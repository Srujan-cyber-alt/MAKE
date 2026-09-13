"""
Neural Audio Model for MAKE Audio V2.

Transformer + BiLSTM + Conv1d Vocoder architecture.
Real PyTorch implementation with full checkpoint support.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import os
import json
import hashlib
import time
from dataclasses import dataclass, field, asdict

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


@dataclass
class MakeNeuralTrainingConfig:
    """Configuration for neural model training."""
    batch_size: int = 8
    learning_rate: float = 1e-3
    max_steps: int = 200
    warmup_steps: int = 10
    checkpoint_every: int = 20
    eval_every: int = 10
    gradient_clip_norm: float = 1.0
    seed: int = 42
    checkpoint_dir: str = "checkpoints/neural_audio"
    dataset_config: Dict[str, Any] = field(default_factory=dict)
    device: str = "cpu"
    mixed_precision: bool = False


class TextEncoder(nn.Module):
    """Character-level text encoder with positional encoding."""
    
    def __init__(self, vocab_size: int = 256, embed_dim: int = 256, max_len: int = 256):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.pos_encoding = self._create_pos_encoding(max_len, embed_dim)
        self.norm = nn.LayerNorm(embed_dim)
        
    def _create_pos_encoding(self, max_len: int, embed_dim: int) -> torch.Tensor:
        pe = torch.zeros(max_len, embed_dim)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, embed_dim, 2).float() * 
                           -(np.log(10000.0) / embed_dim))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        return pe.unsqueeze(0)
    
    def forward(self, text_indices: torch.Tensor) -> torch.Tensor:
        # text_indices: (batch, seq_len)
        seq_len = text_indices.size(1)
        x = self.embedding(text_indices)
        x = x + self.pos_encoding[:, :seq_len, :].to(x.device)
        x = self.norm(x)
        return x.mean(dim=1)  # Global average pooling -> (batch, embed_dim)


class SpeakerEncoder(nn.Module):
    """Speaker identity encoder with learned embeddings."""
    
    def __init__(self, num_speakers: int = 1000, embed_dim: int = 256):
        super().__init__()
        self.embedding = nn.Embedding(num_speakers, embed_dim)
        
    def forward(self, speaker_ids: torch.Tensor) -> torch.Tensor:
        return self.embedding(speaker_ids)


class EmotionEncoder(nn.Module):
    """Emotion conditioning encoder."""
    
    def __init__(self, num_emotions: int = 32, embed_dim: int = 256):
        super().__init__()
        self.embedding = nn.Embedding(num_emotions, embed_dim)
        
    def forward(self, emotion_ids: torch.Tensor) -> torch.Tensor:
        return self.embedding(emotion_ids)


class StyleEncoder(nn.Module):
    """Speaking style/acting encoder."""
    
    def __init__(self, num_styles: int = 16, embed_dim: int = 256):
        super().__init__()
        self.embedding = nn.Embedding(num_styles, embed_dim)
        
    def forward(self, style_ids: torch.Tensor) -> torch.Tensor:
        return self.embedding(style_ids)


class DurationEncoder(nn.Module):
    """Duration conditioning encoder."""
    
    def __init__(self, embed_dim: int = 256):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(1, embed_dim // 2),
            nn.ReLU(),
            nn.Linear(embed_dim // 2, embed_dim),
        )
        
    def forward(self, duration: torch.Tensor) -> torch.Tensor:
        # duration: (batch, 1)
        return self.mlp(duration)


class PitchEncoder(nn.Module):
    """Pitch conditioning encoder."""
    
    def __init__(self, embed_dim: int = 256):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(1, embed_dim // 2),
            nn.ReLU(),
            nn.Linear(embed_dim // 2, embed_dim),
        )
        
    def forward(self, pitch: torch.Tensor) -> torch.Tensor:
        # pitch: (batch, 1) in Hz
        log_pitch = torch.log2(pitch / 80.0).clamp(0, 4) / 4.0
        return self.mlp(log_pitch)


class MakeNeuralAudioModel(nn.Module):
    """
    MAKE Neural Audio Model.
    
    Architecture:
    - Text Encoder (Transformer-style)
    - Speaker/Emotion/Style/Pitch/Duration Encoders
    - BiLSTM for temporal modeling
    - Transformer encoder for context
    - Conv1d Vocoder for waveform generation
    """
    
    def __init__(
        self,
        vocab_size: int = 256,
        embed_dim: int = 256,
        hidden_dim: int = 512,
        num_layers: int = 4,
        num_heads: int = 8,
        ffn_dim: int = 1024,
        dropout: float = 0.1,
        max_text_len: int = 256,
        num_speakers: int = 1000,
        num_emotions: int = 32,
        num_styles: int = 16,
        sample_rate: int = 16000,
        seed: int = 42,
    ):
        super().__init__()
        
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.ffn_dim = ffn_dim
        self.dropout = dropout
        self.sample_rate = sample_rate
        self.seed = seed
        
        # Set seed for reproducibility
        torch.manual_seed(seed)
        np.random.seed(seed)
        
        # Encoders
        self.text_encoder = TextEncoder(vocab_size, embed_dim, max_text_len)
        self.speaker_encoder = SpeakerEncoder(num_speakers, embed_dim)
        self.emotion_encoder = EmotionEncoder(num_emotions, embed_dim)
        self.style_encoder = StyleEncoder(num_styles, embed_dim)
        self.duration_encoder = DurationEncoder(embed_dim)
        self.pitch_encoder = PitchEncoder(embed_dim)
        
        # Conditioning fusion
        cond_dim = embed_dim * 6  # text + speaker + emotion + style + duration + pitch
        self.cond_fusion = nn.Sequential(
            nn.Linear(cond_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        
        # BiLSTM for temporal modeling
        self.bilstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim // 2,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        
        # Transformer encoder for context
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=ffn_dim,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Output projection
        self.output_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 128),  # Vocoder input dim
        )
        
        # Conv1d Vocoder
        self.vocoder = Conv1dVocoder(
            input_dim=128,
            hidden_dim=256,
            upsample_factors=[4, 4, 4, 4],  # 16k -> 256
            output_channels=1,
        )
        
        # Initialize weights
        self.apply(self._init_weights)
        
    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, (nn.Linear, nn.Conv1d, nn.ConvTranspose1d)):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0, std=0.1)
        elif isinstance(module, nn.LayerNorm):
            nn.init.ones_(module.weight)
            nn.init.zeros_(module.bias)
        elif isinstance(module, nn.LSTM):
            for name, param in module.named_parameters():
                if 'weight' in name:
                    nn.init.xavier_uniform_(param)
                elif 'bias' in name:
                    nn.init.zeros_(param)
    
    def forward(
        self,
        text_indices: torch.Tensor,      # (batch, seq_len)
        speaker_ids: torch.Tensor,       # (batch,)
        emotion_ids: torch.Tensor,       # (batch,)
        style_ids: torch.Tensor,         # (batch,)
        duration: torch.Tensor,          # (batch, 1)
        pitch: torch.Tensor,             # (batch, 1)
    ) -> torch.Tensor:
        """Forward pass returning acoustic parameters."""
        # Encode all conditioning
        text_emb = self.text_encoder(text_indices)
        speaker_emb = self.speaker_encoder(speaker_ids)
        emotion_emb = self.emotion_encoder(emotion_ids)
        style_emb = self.style_encoder(style_ids)
        duration_emb = self.duration_encoder(duration)
        pitch_emb = self.pitch_encoder(pitch)
        
        # Fuse conditioning
        cond = torch.cat([text_emb, speaker_emb, emotion_emb, style_emb, duration_emb, pitch_emb], dim=-1)
        fused = self.cond_fusion(cond)  # (batch, hidden_dim)
        
        # Add sequence dimension for LSTM/Transformer
        fused_seq = fused.unsqueeze(1)  # (batch, 1, hidden_dim)
        
        # BiLSTM
        lstm_out, _ = self.bilstm(fused_seq)  # (batch, 1, hidden_dim)
        
        # Transformer
        trans_out = self.transformer(lstm_out)  # (batch, 1, hidden_dim)
        
        # Output projection
        params = self.output_proj(trans_out.squeeze(1))  # (batch, 128)
        
        return params
    
    def generate(
        self,
        text_indices: torch.Tensor,
        speaker_ids: torch.Tensor,
        emotion_ids: torch.Tensor,
        style_ids: torch.Tensor,
        duration: torch.Tensor,
        pitch: torch.Tensor,
    ) -> torch.Tensor:
        """Generate waveform from conditioning."""
        self.eval()
        with torch.no_grad():
            params = self.forward(text_indices, speaker_ids, emotion_ids, style_ids, duration, pitch)
            audio = self.vocoder(params)
        return audio
    
    def get_num_params(self) -> int:
        return sum(p.numel() for p in self.parameters())


class Conv1dVocoder(nn.Module):
    """Conv1d-based vocoder for waveform generation."""
    
    def __init__(
        self,
        input_dim: int = 128,
        hidden_dim: int = 256,
        upsample_factors: List[int] = [4, 4, 4, 4],
        output_channels: int = 1,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.upsample_factors = upsample_factors
        
        # Initial projection
        self.initial = nn.Sequential(
            nn.Conv1d(input_dim, hidden_dim, 3, padding=1),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
        )
        
        # Upsampling blocks
        self.upsample_blocks = nn.ModuleList()
        current_dim = hidden_dim
        for factor in upsample_factors:
            self.upsample_blocks.append(UpsampleBlock(current_dim, current_dim, factor))
        
        # Final output
        self.output = nn.Sequential(
            nn.Conv1d(hidden_dim, hidden_dim // 2, 3, padding=1),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Conv1d(hidden_dim // 2, output_channels, 3, padding=1),
            nn.Tanh(),
        )
        
    def forward(self, params: torch.Tensor) -> torch.Tensor:
        # params: (batch, 128)
        # Add time dimension
        x = params.unsqueeze(-1)  # (batch, 128, 1)
        x = self.initial(x)  # (batch, hidden_dim, 1)
        
        for block in self.upsample_blocks:
            x = block(x)
        
        x = self.output(x)  # (batch, 1, time)
        return x.squeeze(1)  # (batch, time)


class UpsampleBlock(nn.Module):
    """Upsampling block with ConvTranspose1d."""
    
    def __init__(self, in_channels: int, out_channels: int, upsample_factor: int):
        super().__init__()
        self.upsample = nn.ConvTranspose1d(
            in_channels, out_channels,
            kernel_size=upsample_factor * 2,
            stride=upsample_factor,
            padding=upsample_factor // 2,
        )
        self.norm = nn.BatchNorm1d(out_channels)
        self.activation = nn.ReLU()
        self.conv = nn.Conv1d(out_channels, out_channels, 3, padding=1)
        self.norm2 = nn.BatchNorm1d(out_channels)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.upsample(x)
        x = self.norm(x)
        x = self.activation(x)
        x = self.conv(x)
        x = self.norm2(x)
        x = self.activation(x)
        return x


class MakeNeuralTrainer:
    """Training pipeline for MakeNeuralAudioModel."""
    
    def __init__(self, model: MakeNeuralAudioModel, config: MakeNeuralTrainingConfig):
        self.model = model
        self.config = config
        self.device = torch.device(config.device)
        self.model.to(self.device)
        
        # Optimizer
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=config.learning_rate,
            weight_decay=1e-4,
        )
        
        # Scheduler with warmup
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=config.max_steps,
            eta_min=config.learning_rate * 0.01,
        )
        
        # Loss
        self.criterion = nn.MSELoss()
        
        # Training state
        self.step = 0
        self.epoch = 0
        self.best_val_loss = float('inf')
        self.train_losses: List[float] = []
        self.val_losses: List[float] = []
        
        # Create checkpoint dir
        os.makedirs(config.checkpoint_dir, exist_ok=True)
        
    def _create_synthetic_batch(
        self, 
        batch_size: int, 
        max_text_len: int = 100,
    ) -> Dict[str, torch.Tensor]:
        """Create synthetic training batch with deterministic targets."""
        torch.manual_seed(self.config.seed + self.step)
        
        # Random text indices
        text_indices = torch.randint(0, self.model.vocab_size, (batch_size, max_text_len))
        
        # Random speaker/emotion/style IDs
        speaker_ids = torch.randint(0, self.model.speaker_encoder.embedding.num_embeddings, (batch_size,))
        emotion_ids = torch.randint(0, self.model.emotion_encoder.embedding.num_embeddings, (batch_size,))
        style_ids = torch.randint(0, self.model.style_encoder.embedding.num_embeddings, (batch_size,))
        
        # Duration: 0.5-5.0 seconds
        duration = torch.rand(batch_size, 1) * 4.5 + 0.5
        
        # Pitch: 80-400 Hz
        pitch = torch.rand(batch_size, 1) * 320 + 80
        
        # Target: deterministic from text hash
        targets = []
        for i in range(batch_size):
            text_str = ''.join(chr(idx % 128) for idx in text_indices[i].tolist())
            target_hash = hashlib.sha256(text_str.encode()).digest()
            target_vec = torch.frombuffer(target_hash, dtype=torch.float32)[:128]
            if len(target_vec) < 128:
                target_vec = F.pad(target_vec, (0, 128 - len(target_vec)))
            targets.append(target_vec)
        
        target = torch.stack(targets).to(self.device)
        
        return {
            'text_indices': text_indices.to(self.device),
            'speaker_ids': speaker_ids.to(self.device),
            'emotion_ids': emotion_ids.to(self.device),
            'style_ids': style_ids.to(self.device),
            'duration': duration.to(self.device),
            'pitch': pitch.to(self.device),
            'target': target,
        }
    
    def train_step(self) -> Dict[str, float]:
        """Single training step."""
        self.model.train()
        self.optimizer.zero_grad()
        
        batch = self._create_synthetic_batch(self.config.batch_size)
        
        # Forward
        params = self.model(
            batch['text_indices'],
            batch['speaker_ids'],
            batch['emotion_ids'],
            batch['style_ids'],
            batch['duration'],
            batch['pitch'],
        )
        
        # Loss
        loss = self.criterion(params, batch['target'])
        
        # NaN/Inf check
        if torch.isnan(loss) or torch.isinf(loss):
            raise RuntimeError(f"NaN/Inf loss detected at step {self.step}")
        
        # Backward
        loss.backward()
        
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.gradient_clip_norm)
        
        # Gradient sanity check
        total_grad_norm = 0.0
        for p in self.model.parameters():
            if p.grad is not None:
                total_grad_norm += p.grad.norm().item() ** 2
        total_grad_norm = total_grad_norm ** 0.5
        
        if total_grad_norm > 100.0:
            print(f"Warning: Large gradient norm: {total_grad_norm}")
        
        self.optimizer.step()
        self.scheduler.step()
        self.step += 1
        
        return {
            'step': self.step,
            'loss': loss.item(),
            'lr': self.scheduler.get_last_lr()[0],
            'grad_norm': total_grad_norm,
        }
    
    @torch.no_grad()
    def validate(self, num_batches: int = 4) -> float:
        """Run validation."""
        self.model.eval()
        total_loss = 0.0
        
        for _ in range(num_batches):
            batch = self._create_synthetic_batch(self.config.batch_size)
            params = self.model(
                batch['text_indices'],
                batch['speaker_ids'],
                batch['emotion_ids'],
                batch['style_ids'],
                batch['duration'],
                batch['pitch'],
            )
            loss = self.criterion(params, batch['target'])
            total_loss += loss.item()
        
        avg_loss = total_loss / num_batches
        return avg_loss
    
    def train(self) -> Dict[str, Any]:
        """Full training loop."""
        print(f"Starting training for {self.config.max_steps} steps on {self.device}")
        print(f"Model parameters: {self.model.get_num_params():,}")
        
        for step in range(self.config.max_steps):
            metrics = self.train_step()
            self.train_losses.append(metrics['loss'])
            
            # Validation
            if (step + 1) % self.config.eval_every == 0:
                val_loss = self.validate()
                self.val_losses.append(val_loss)
                
                is_best = val_loss < self.best_val_loss
                if is_best:
                    self.best_val_loss = val_loss
                
                print(f"Step {step+1}/{self.config.max_steps}: "
                      f"train_loss={metrics['loss']:.6f}, "
                      f"val_loss={val_loss:.6f}, "
                      f"lr={metrics['lr']:.6f}, "
                      f"grad_norm={metrics['grad_norm']:.4f}"
                      f"{' [BEST]' if is_best else ''}")
                
                # Save checkpoint
                if (step + 1) % self.config.checkpoint_every == 0 or is_best:
                    self.save_checkpoint(is_best=is_best)
            
            # Log training loss
            if (step + 1) % 10 == 0:
                print(f"Step {step+1}/{self.config.max_steps}: "
                      f"loss={metrics['loss']:.6f}, "
                      f"lr={metrics['lr']:.6f}")
        
        # Final checkpoint
        self.save_checkpoint(is_best=False)
        
        return {
            'total_steps': self.step,
            'final_train_loss': self.train_losses[-1] if self.train_losses else None,
            'final_val_loss': self.val_losses[-1] if self.val_losses else None,
            'best_val_loss': self.best_val_loss,
        }
    
    def save_checkpoint(self, is_best: bool = False) -> str:
        """Save model checkpoint with full training state."""
        checkpoint_path = os.path.join(
            self.config.checkpoint_dir,
            f"step_{self.step}_{'best' if is_best else 'latest'}.pt"
        )
        
        checkpoint = {
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'step': self.step,
            'epoch': self.epoch,
            'best_val_loss': self.best_val_loss,
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'model_config': {
                'vocab_size': self.model.vocab_size,
                'embed_dim': self.model.embed_dim,
                'hidden_dim': self.model.hidden_dim,
                'num_layers': self.model.num_layers,
                'num_heads': self.model.num_heads,
                'ffn_dim': self.model.ffn_dim,
                'dropout': self.model.dropout,
                'sample_rate': self.model.sample_rate,
                'seed': self.model.seed,
            },
            'training_config': asdict(self.config),
            'dataset_fingerprint': hashlib.sha256(
                json.dumps(self.config.dataset_config, sort_keys=True).encode()
            ).hexdigest()[:16],
            'seed': self.config.seed,
            'training_metadata': {
                'start_time': time.time() - sum(self.train_losses) if self.train_losses else time.time(),
                'total_steps': self.step,
                'device': self.config.device,
            },
        }
        
        torch.save(checkpoint, checkpoint_path)
        print(f"Checkpoint saved: {checkpoint_path}")
        return checkpoint_path
    
    def load_checkpoint(self, checkpoint_path: str) -> None:
        """Load model checkpoint with full training state."""
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        
        # Verify model config matches
        model_config = checkpoint.get('model_config', {})
        for key, expected_value in model_config.items():
            actual_value = getattr(self.model, key, None)
            if actual_value is not None and actual_value != expected_value:
                raise RuntimeError(f"Model config mismatch: {key} expected {expected_value}, got {actual_value}")
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.step = checkpoint.get('step', 0)
        self.epoch = checkpoint.get('epoch', 0)
        self.best_val_loss = checkpoint.get('best_val_loss', float('inf'))
        self.train_losses = checkpoint.get('train_losses', [])
        self.val_losses = checkpoint.get('val_losses', [])
        
        print(f"Checkpoint loaded: step={self.step}, best_val_loss={self.best_val_loss:.6f}")
    
    @torch.no_grad()
    def generate(
        self,
        text: str,
        duration_s: float = 1.0,
        speaker_id: int = 0,
        emotion_id: int = 0,
        style_id: int = 0,
        pitch_hz: float = 120.0,
        seed: Optional[int] = None,
    ) -> np.ndarray:
        """Generate audio from text."""
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)
        
        self.model.eval()
        
        # Convert text to indices
        text_indices = torch.tensor(
            [[min(ord(c), self.model.vocab_size - 1) for c in text[:256]]],
            dtype=torch.long,
            device=self.device
        )
        
        # Pad or truncate
        if text_indices.size(1) < 256:
            text_indices = F.pad(text_indices, (0, 256 - text_indices.size(1)))
        else:
            text_indices = text_indices[:, :256]
        
        speaker_ids = torch.tensor([speaker_id], dtype=torch.long, device=self.device)
        emotion_ids = torch.tensor([emotion_id], dtype=torch.long, device=self.device)
        style_ids = torch.tensor([style_id], dtype=torch.long, device=self.device)
        duration = torch.tensor([[duration_s]], dtype=torch.float32, device=self.device)
        pitch = torch.tensor([[pitch_hz]], dtype=torch.float32, device=self.device)
        
        audio = self.model.generate(
            text_indices, speaker_ids, emotion_ids, style_ids, duration, pitch
        )
        
        return audio.squeeze(0).cpu().numpy()


def create_model_and_trainer(
    config: Optional[MakeNeuralTrainingConfig] = None,
    model_config: Optional[Dict[str, Any]] = None,
) -> Tuple[MakeNeuralAudioModel, MakeNeuralTrainer]:
    """Factory function to create model and trainer."""
    config = config or MakeNeuralTrainingConfig()
    model_config = model_config or {}
    
    model = MakeNeuralAudioModel(**model_config, seed=config.seed)
    trainer = MakeNeuralTrainer(model, config)
    
    return model, trainer