"""Tests for MAKE Audio subsystem."""

import pytest
import numpy as np


class TestAudioConfig:
    def test_load_tiny_config(self):
        from app.make_model.audio.config_loader import load_audio_config
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        assert config.model_id == "audio-tiny-v1"
        assert config.sample_rate == 16000
        assert config.channels == 1

    def test_load_research_config(self):
        from app.make_model.audio.config_loader import load_audio_config
        config = load_audio_config("app/make_model/audio/configs/audio_research.json")
        assert config.sample_rate == 22050
        assert config.hidden_dim == 512

    def test_load_production_config(self):
        from app.make_model.audio.config_loader import load_audio_config
        config = load_audio_config("app/make_model/audio/configs/audio_production.json")
        assert config.sample_rate == 44100
        assert config.channels == 2


class TestVoiceGenome:
    def test_create_voice_genome(self):
        from app.make_model.audio.types import VoiceGenome
        genome = VoiceGenome(voice_id="test_voice", pitch_mean=220.0)
        assert genome.voice_id == "test_voice"
        assert genome.pitch_mean == 220.0

    def test_voice_genome_to_dict(self):
        from app.make_model.audio.types import VoiceGenome
        genome = VoiceGenome(voice_id="test")
        data = genome.to_dict()
        assert "voice_id" in data
        assert data["voice_id"] == "test"

    def test_voice_genome_engine(self):
        from app.make_model.audio.voice import VoiceGenomeEngine
        from app.make_model.audio.config_loader import load_audio_config
        engine = VoiceGenomeEngine()
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        import asyncio
        asyncio.run(engine.initialize(config))
        assert engine.config is not None
        assert engine.config.model_id == "audio-tiny-v1"


class TestEmotionVector:
    def test_emotion_blend(self):
        from app.make_model.audio.types import EmotionVector
        happy = EmotionVector(happiness=0.9, excitement=0.6)
        sad = EmotionVector(sadness=0.9, calm=0.4)
        blended = happy.blend(sad, weight=0.5)
        assert blended.happiness > 0.0
        assert blended.sadness > 0.0

    def test_emotion_engine(self):
        from app.make_model.audio.emotion import EmotionEngine
        from app.make_model.audio.config_loader import load_audio_config
        engine = EmotionEngine()
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        import asyncio
        asyncio.run(engine.initialize(config))
        assert engine.config is not None


class TestAudioQuality:
    def test_quality_evaluator_init(self):
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        assert evaluator is not None

    def test_calculate_snr(self):
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000))
        snr = evaluator._calculate_snr(audio)
        assert isinstance(snr, float)

    def test_calculate_clipping(self):
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        audio = np.clip(np.random.randn(16000), -0.99, 0.99)
        clipping = evaluator._calculate_clipping(audio)
        assert isinstance(clipping, float)

    def test_calculate_silence_ratio(self):
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        audio = np.zeros(16000)
        silence = evaluator._calculate_silence_ratio(audio, 16000)
        assert silence > 0.9


class TestAudioGenerationPipeline:
    def test_pipeline_init(self):
        from app.make_model.audio.generation import AudioGenerationPipeline
        pipeline = AudioGenerationPipeline()
        assert pipeline is not None

    def test_pipeline_list_models(self):
        from app.make_model.audio.generation import AudioGenerationPipeline
        pipeline = AudioGenerationPipeline()
        models = pipeline.list_models()
        assert "voice" in models
        assert "emotion" in models
        assert "music" in models
        assert "mixing" in models

    def test_pipeline_get_model(self):
        from app.make_model.audio.generation import AudioGenerationPipeline
        pipeline = AudioGenerationPipeline()
        model = pipeline.get_model("voice")
        assert model is not None
        assert model.model_type == "voice"


class TestProvenance:
    def test_provenance_tracker(self):
        from app.make_model.audio.provenance import AudioProvenanceTracker
        tracker = AudioProvenanceTracker("/tmp/test_audio_prov.json")
        record = tracker.record(
            artifact_id="test_1",
            model_id="test_model",
            model_version="1.0",
            generation_parameters={"prompt": "test"},
            source_inputs=["input.wav"],
            transformations=[],
            content_hash="abc123",
        )
        assert record.artifact_id == "test_1"
        retrieved = tracker.get_record("test_1")
        assert retrieved is not None
        assert retrieved.content_hash == "abc123"


class TestVoiceIdentityMemory:
    def test_register_and_get(self):
        from app.make_model.audio.voice_identity import VoiceIdentityMemory
        from app.make_model.audio.types import VoiceGenome
        memory = VoiceIdentityMemory("/tmp/test_voice_id.json")
        genome = VoiceGenome(voice_id="voice_1")
        memory.register(genome)
        retrieved = memory.get("voice_1")
        assert retrieved is not None
        assert retrieved.voice_id == "voice_1"

    def test_list_voices(self):
        from app.make_model.audio.voice_identity import VoiceIdentityMemory
        from app.make_model.audio.types import VoiceGenome
        memory = VoiceIdentityMemory("/tmp/test_voice_id2.json")
        memory.register(VoiceGenome(voice_id="v1"))
        memory.register(VoiceGenome(voice_id="v2"))
        voices = memory.list_voices()
        assert "v1" in voices
        assert "v2" in voices


class TestDialogueEngine:
    def test_dialogue_generation(self):
        from app.make_model.audio.dialogue import DialogueEngine
        from app.make_model.audio.config_loader import load_audio_config
        import asyncio
        engine = DialogueEngine()
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        asyncio.run(engine.initialize(config))
        script = [{"speaker": "Alice", "text": "Hello"}]
        voices = {"Alice": "voice_alice"}
        result = asyncio.run(engine.generate_dialogue(script, voices))
        assert result.audio_path != ""


class TestSpeakerMemory:
    def test_speaker_registration(self):
        from app.make_model.audio.speaker_memory import SpeakerMemory
        from app.make_model.audio.types import VoiceGenome
        memory = SpeakerMemory()
        genome = VoiceGenome(voice_id="speaker_1")
        memory.register_speaker("speaker_1", genome)
        speaker = memory.get_speaker("speaker_1")
        assert speaker is not None
        assert speaker["genome"]["voice_id"] == "speaker_1"


class TestContinuityMemory:
    def test_scene_continuity(self):
        from app.make_model.audio.continuity import AudioContinuityMemory
        memory = AudioContinuityMemory("/tmp/test_continuity.json")
        memory.record_scene("scene_1", {"ambience": "forest", "room": "outdoor"})
        scene = memory.get_scene("scene_1")
        assert scene is not None
        assert scene["audio_state"]["ambience"] == "forest"
