"""Tests for Source Separation V2."""
import numpy as np
import pytest
from app.make_model.audio.source_separation_v2 import (
    DSPSeparator, SeparationBand, SeparationQuality,
    SEPARATION_BAND_DEFS,
)


class TestSourceSeparationV2:
    @pytest.fixture
    def separator(self):
        return DSPSeparator(sample_rate=16000)

    @pytest.fixture
    def test_audio(self):
        t = np.arange(8000) / 16000
        return (0.3 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)

    def test_separator_creation(self, separator):
        assert separator.sample_rate == 16000

    def test_all_bands_defined(self):
        assert len(SEPARATION_BAND_DEFS) == 8
        expected_bands = {"vocal", "speech", "music", "percussion", "bass", "high_frequency", "ambience", "noise"}
        actual_bands = {b.value for b in SEPARATION_BAND_DEFS}
        assert expected_bands == actual_bands

    def test_separate_basic(self, separator, test_audio):
        result = separator.separate(test_audio)
        assert len(result.bands) == 8
        assert result.method == "dsp_fft_filterbank_v2"
        assert len(result.input_sha256) > 0
        assert result.reconstruction_error >= 0

    def test_separation_produces_audio(self, separator, test_audio):
        result = separator.separate(test_audio)
        for band_name, band_audio in result.bands.items():
            assert band_audio.shape[0] > 0
            assert isinstance(band_audio, np.ndarray)

    def test_quality_metrics(self, separator, test_audio):
        result = separator.separate(test_audio)
        quality = separator.get_quality_metrics(result)
        assert isinstance(quality, SeparationQuality)
        assert quality.sdr > -100
        assert quality.sir > -100
        assert quality.sar > 0

    def test_get_separated_audio_single_band(self, separator, test_audio):
        result = separator.separate(test_audio)
        vocal = separator.get_separated_audio(result, ["vocal"])
        assert len(vocal) > 0
        assert np.max(np.abs(vocal)) <= 0.99

    def test_get_separated_audio_multiple_bands(self, separator, test_audio):
        result = separator.separate(test_audio)
        combined = separator.get_separated_audio(result, ["vocal", "speech", "music"])
        assert len(combined) > 0

    def test_leakage_measurement(self, separator, test_audio):
        result = separator.separate(test_audio)
        assert len(result.leakage_metrics) > 0

    def test_dsp_labeling(self, separator, test_audio):
        result = separator.separate(test_audio)
        assert "dsp" in result.method.lower()

    def test_determinism(self, separator, test_audio):
        r1 = separator.separate(test_audio)
        r2 = separator.separate(test_audio)
        assert r1.input_sha256 == r2.input_sha256
        for band in r1.bands:
            assert np.allclose(r1.bands[band], r2.bands[band])
