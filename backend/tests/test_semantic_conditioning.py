"""Test semantic conditioning in neural API."""
import numpy as np
import pytest


class TestSemanticConditioning:
    def test_speaker_conditioning(self):
        from app.make_model.audio.neural_api import NeuralAPI
        api = NeuralAPI()
        text = 'Hello world, this is a test.'
        
        result1 = api.generate(text, duration_s=1.0, speaker='default', emotion='neutral', style='neutral')
        result2 = api.generate(text, duration_s=1.0, speaker='narrator', emotion='neutral', style='neutral')
        
        diff = np.abs(result1.audio - result2.audio).mean()
        print(f'Speaker diff: {diff:.6f}')
        assert diff > 0.001, f'Speaker conditioning not working: {diff}'
        
    def test_emotion_conditioning(self):
        from app.make_model.audio.neural_api import NeuralAPI
        api = NeuralAPI()
        text = 'Hello world, this is a test.'
        
        result1 = api.generate(text, duration_s=1.0, speaker='default', emotion='neutral', style='neutral')
        result2 = api.generate(text, duration_s=1.0, speaker='default', emotion='happy', style='neutral')
        
        diff = np.abs(result1.audio - result2.audio).mean()
        print(f'Emotion diff: {diff:.6f}')
        assert diff > 0.001, f'Emotion conditioning not working: {diff}'
        
    def test_style_conditioning(self):
        from app.make_model.audio.neural_api import NeuralAPI
        api = NeuralAPI()
        text = 'Hello world, this is a test.'
        
        result1 = api.generate(text, duration_s=1.0, speaker='default', emotion='neutral', style='neutral')
        result2 = api.generate(text, duration_s=1.0, speaker='default', emotion='neutral', style='whisper')
        
        diff = np.abs(result1.audio - result2.audio).mean()
        print(f'Style diff: {diff:.6f}')
        assert diff > 0.001, f'Style conditioning not working: {diff}'
        
    def test_pitch_conditioning(self):
        from app.make_model.audio.neural_api import NeuralAPI
        api = NeuralAPI()
        text = 'Hello world, this is a test of pitch control.'
        
        result_low = api.generate(text, duration_s=1.0, speaker='default', emotion='neutral', style='neutral', pitch_hz=80.0)
        result_mid = api.generate(text, duration_s=1.0, speaker='default', emotion='neutral', style='neutral', pitch_hz=120.0)
        result_high = api.generate(text, duration_s=1.0, speaker='default', emotion='neutral', style='neutral', pitch_hz=200.0)
        
        diff_low_mid = np.abs(result_low.audio - result_mid.audio).mean()
        diff_mid_high = np.abs(result_mid.audio - result_high.audio).mean()
        diff_low_high = np.abs(result_low.audio - result_high.audio).mean()
        
        print(f'Pitch 80Hz vs 120Hz diff: {diff_low_mid:.6f}')
        print(f'Pitch 120Hz vs 200Hz diff: {diff_mid_high:.6f}')
        print(f'Pitch 80Hz vs 200Hz diff: {diff_low_high:.6f}')
        
        assert diff_low_mid > 0.001, f'Pitch conditioning not working: {diff_low_mid}'
        assert diff_mid_high > 0.001, f'Pitch conditioning not working: {diff_mid_high}'
        
    def test_energy_conditioning(self):
        from app.make_model.audio.neural_api import NeuralAPI
        api = NeuralAPI()
        text = 'Hello world, this is a test.'
        
        result_quiet = api.generate(text, duration_s=1.0, speaker='default', emotion='neutral', style='neutral', energy_db=-60.0)
        result_loud = api.generate(text, duration_s=1.0, speaker='default', emotion='neutral', style='neutral', energy_db=0.0)
        
        diff_energy = np.abs(result_quiet.audio - result_loud.audio).mean()
        print(f'Energy -60dB vs 0dB diff: {diff_energy:.6f}')
        assert diff_energy > 0.001, f'Energy conditioning not working: {diff_energy}'
        
    def test_duration_control(self):
        from app.make_model.audio.neural_api import NeuralAPI
        api = NeuralAPI()
        text = 'Hello world.'
        
        for dur in [0.5, 1.0, 2.0, 5.0, 10.0]:
            result = api.generate(text, duration_s=dur, speaker='default', emotion='neutral', style='neutral')
            expected_samples = int(dur * 16000)
            print(f'Duration {dur}s: {len(result.audio)} samples (expected {expected_samples})')
            assert len(result.audio) == expected_samples, f'Duration mismatch: {len(result.audio)} != {expected_samples}'
            
    def test_provenance_includes_conditioning(self):
        from app.make_model.audio.neural_api import NeuralAPI
        api = NeuralAPI()
        text = 'Hello world.'
        
        result = api.generate(text, duration_s=1.0, speaker='narrator', emotion='happy', style='whisper', pitch_hz=150.0, energy_db=-10.0)
        
        cond = result.provenance['conditioning']
        assert cond['speaker_id'] == 1
        assert cond['speaker_label'] == 'narrator'
        assert cond['emotion_id'] == 1
        assert cond['emotion_label'] == 'happy'
        assert cond['style_id'] == 1
        assert cond['style_label'] == 'whisper'
        assert cond['pitch_hz'] == 150.0
        assert cond['energy_db'] == -10.0
        
    def test_validate_conditioning(self):
        from app.make_model.audio.neural_api import NeuralAPI
        api = NeuralAPI()
        
        # Valid labels
        val = api.validate_conditioning(speaker='narrator', emotion='happy', style='whisper')
        assert val['speaker_valid'] is True
        assert val['emotion_valid'] is True
        assert val['style_valid'] is True
        
        # Invalid labels
        val = api.validate_conditioning(speaker='invalid', emotion='invalid', style='invalid')
        assert val['speaker_valid'] is False
        assert val['emotion_valid'] is False
        assert val['style_valid'] is False
        
    def test_get_available_conditioning(self):
        from app.make_model.audio.neural_api import NeuralAPI
        api = NeuralAPI()
        
        cond = api.get_available_conditioning()
        assert 'speakers' in cond
        assert 'emotions' in cond
        assert 'styles' in cond
        assert len(cond['speakers']) >= 28
        assert len(cond['emotions']) == 32
        assert len(cond['styles']) == 16
        assert 'narrator' in cond['speakers']
        assert 'happy' in cond['emotions']
        assert 'whisper' in cond['styles']