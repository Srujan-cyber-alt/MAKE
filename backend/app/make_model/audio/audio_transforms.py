"""
MAKE Audio-to-Audio Transformations.

Voice identity preservation while changing acoustic characteristics.
All transformations are deterministic DSP operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal
import time
import hashlib
from pathlib import Path

from app.make_model.audio.architecture import GenerationRequest, GenerationResult, AudioConfig


class VoiceTransformer:
    """Voice identity-preserving transformations."""

    @staticmethod
    def age_voice(
        audio_path: str, target_age_group: str = "older",
        output_path: Optional[str] = None,
    ) -> str:
        sr, data = VoiceTransformer._load_audio(audio_path)
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        else:
            audio = data.astype(np.float32)
        if target_age_group == "older":
            audio = VoiceTransformer._reduce_pitch(audio, sr, 0.85)
            audio = VoiceTransformer._add_breathiness(audio, sr, 0.15)
            audio = VoiceTransformer._add_rasp(audio, sr, 0.1)
        elif target_age_group == "younger":
            audio = VoiceTransformer._increase_pitch(audio, sr, 1.15)
            audio = VoiceTransformer._add_clarity(audio, sr)
        elif target_age_group == "child":
            audio = VoiceTransformer._increase_pitch(audio, sr, 1.5)
            audio = VoiceTransformer._brighten(audio, sr)
        if output_path is None:
            output_path = audio_path.replace(".wav", f"_age_{target_age_group}.wav")
        VoiceTransformer._save_audio(output_path, audio, sr)
        return output_path

    @staticmethod
    def change_gender(
        audio_path: str, shift_ratio: float = 1.2,
        output_path: Optional[str] = None,
    ) -> str:
        sr, data = VoiceTransformer._load_audio(audio_path)
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        else:
            audio = data.astype(np.float32)
        audio = VoiceTransformer._reduce_pitch(audio, sr, shift_ratio)
        if output_path is None:
            output_path = audio_path.replace(".wav", f"_gender_{shift_ratio}.wav")
        VoiceTransformer._save_audio(output_path, audio, sr)
        return output_path

    @staticmethod
    def _reduce_pitch(audio: np.ndarray, sr: int, ratio: float) -> np.ndarray:
        n_fft = min(1024, len(audio))
        hop = n_fft // 4
        S = signal.stft(audio, sr, nperseg=n_fft, noverlap=n_fft - hop)
        f, t_stft, Z = S
        n_freq = Z.shape[0]
        shift_bins = int((1.0 - ratio) * n_freq / 2)
        if shift_bins != 0:
            shifted = np.zeros_like(Z)
            for i in range(n_freq):
                src = i + shift_bins
                if 0 <= src < n_freq:
                    shifted[i, :] = Z[src, :]
            Z = shifted
        _, audio_out = signal.istft(Z, sr, nperseg=n_fft, noverlap=n_fft - hop)
        return audio_out[:len(audio)]

    @staticmethod
    def _increase_pitch(audio: np.ndarray, sr: int, ratio: float) -> np.ndarray:
        return VoiceTransformer._reduce_pitch(audio, sr, 1.0 / ratio)

    @staticmethod
    def _add_breathiness(audio: np.ndarray, sr: int, amount: float) -> np.ndarray:
        noise = np.random.RandomState(42).randn(len(audio))
        noise_filt = signal.lfilter([0.01], [1, -0.99], noise)
        return audio + amount * 0.1 * noise_filt

    @staticmethod
    def _add_rasp(audio: np.ndarray, sr: int, amount: float) -> np.ndarray:
        noise = np.random.RandomState(43).randn(len(audio))
        noise_filt = signal.lfilter([0.1], [1, -0.9], noise)
        return audio + amount * 0.05 * noise_filt

    @staticmethod
    def _add_clarity(audio: np.ndarray, sr: int) -> np.ndarray:
        sos = signal.butter(4, 2000, btype="high", fs=sr, output="sos")
        return signal.sosfilt(sos, audio)

    @staticmethod
    def _brighten(audio: np.ndarray, sr: int) -> np.ndarray:
        sos = signal.butter(4, 3000, btype="high", fs=sr, output="sos")
        return signal.sosfilt(sos, audio) * 1.2

    @staticmethod
    def _load_audio(path: str) -> Tuple[int, np.ndarray]:
        sr, data = wavfile.read(path)
        if data.ndim > 1:
            data = data[:, 0]
        return sr, data

    @staticmethod
    def _save_audio(path: str, audio: np.ndarray, sr: int) -> None:
        audio_int = (np.clip(audio, -0.99, 0.99) * 32767).astype(np.int16)
        try:
            wavfile.write(path, sr, audio_int)
        except ValueError:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            wavfile.write(path, sr, audio_int)


class AudioEffect:
    """Audio effect transformations."""

    @staticmethod
    def telephone(audio_path: str, output_path: Optional[str] = None) -> str:
        sr, data = VoiceTransformer._load_audio(audio_path)
        audio = data.astype(np.float32) / 32768.0
        sos = signal.butter(4, [300, 3000], btype="band", fs=sr, output="sos")
        audio = signal.sosfilt(sos, audio)
        audio = signal.resample(audio, int(len(audio) * 0.8))
        if output_path is None:
            output_path = audio_path.replace(".wav", "_telephone.wav")
        VoiceTransformer._save_audio(output_path, audio, sr)
        return output_path

    @staticmethod
    def radio(audio_path: str, output_path: Optional[str] = None) -> str:
        sr, data = VoiceTransformer._load_audio(audio_path)
        audio = data.astype(np.float32) / 32768.0
        sos = signal.butter(4, [200, 5000], btype="band", fs=sr, output="sos")
        audio = signal.sosfilt(sos, audio)
        noise = np.random.RandomState(44).randn(len(audio))
        audio += 0.02 * noise
        if output_path is None:
            output_path = audio_path.replace(".wav", "_radio.wav")
        VoiceTransformer._save_audio(output_path, audio, sr)
        return output_path

    @staticmethod
    def robot(audio_path: str, output_path: Optional[str] = None) -> str:
        sr, data = VoiceTransformer._load_audio(audio_path)
        audio = data.astype(np.float32) / 32768.0
        t = np.arange(len(audio)) / sr
        mod = np.sin(2 * np.pi * 10 * t)
        audio = audio * (1 + 0.1 * mod)
        if output_path is None:
            output_path = audio_path.replace(".wav", "_robot.wav")
        VoiceTransformer._save_audio(output_path, audio, sr)
        return output_path

    @staticmethod
    def underwater(audio_path: str, output_path: Optional[str] = None) -> str:
        sr, data = VoiceTransformer._load_audio(audio_path)
        audio = data.astype(np.float32) / 32768.0
        sos = signal.butter(4, 200, btype="low", fs=sr, output="sos")
        audio = signal.sosfilt(sos, audio)
        noise = np.random.RandomState(45).randn(len(audio))
        audio += 0.03 * signal.lfilter([0.01], [1, -0.99], noise)
        if output_path is None:
            output_path = audio_path.replace(".wav", "_underwater.wav")
        VoiceTransformer._save_audio(output_path, audio, sr)
        return output_path

    @staticmethod
    def alien(audio_path: str, shift_ratio: float = 0.7, output_path: Optional[str] = None) -> str:
        sr, data = VoiceTransformer._load_audio(audio_path)
        audio = data.astype(np.float32) / 32768.0
        n_fft = min(2048, len(audio))
        hop = n_fft // 4
        f, t_stft, Z = signal.stft(audio, sr, nperseg=n_fft, noverlap=n_fft - hop)
        n_freq = Z.shape[0]
        shift_bins = int((1.0 - shift_ratio) * n_freq / 2)
        shifted = np.zeros_like(Z)
        for i in range(n_freq):
            src = i + shift_bins
            if 0 <= src < n_freq:
                shifted[i, :] = Z[src, :]
        _, audio = signal.istft(shifted, sr, nperseg=n_fft, noverlap=n_fft - hop)
        if output_path is None:
            output_path = audio_path.replace(".wav", "_alien.wav")
        VoiceTransformer._save_audio(output_path, audio, sr)
        return output_path

    @staticmethod
    def apply_effect(audio_path: str, effect_name: str, output_path: Optional[str] = None, **params) -> str:
        effects = {
            "telephone": AudioEffect.telephone,
            "radio": AudioEffect.radio,
            "robot": AudioEffect.robot,
            "underwater": AudioEffect.underwater,
            "alien": AudioEffect.alien,
        }
        if effect_name not in effects:
            raise ValueError(f"Unknown effect: {effect_name}")
        return effects[effect_name](audio_path, output_path=output_path, **params)
