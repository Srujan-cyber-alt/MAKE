"""Tests for quantizer module."""

import numpy as np
import pytest

from app.make_model.audio.quantizer import Quantizer, QuantizeDtype


class TestQuantizer:
    def test_fp32_identity(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        result = quantizer.quantize(data, QuantizeDtype.FP32)
        assert np.allclose(result.data, data)
        assert result.compression_ratio == 1.0

    def test_fp16_smaller(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        result = quantizer.quantize(data, QuantizeDtype.FP16)
        assert result.quantized_size_bytes == data.nbytes // 2
        assert result.compression_ratio >= 2.0

    def test_int8_smaller(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        result = quantizer.quantize(data, QuantizeDtype.INT8)
        assert result.quantized_size_bytes == data.nbytes // 4
        assert result.compression_ratio >= 4.0

    def test_uint8_range(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        result = quantizer.quantize(data, QuantizeDtype.UINT8)
        assert result.data.min() >= 0
        assert result.data.max() <= 255

    def test_int8_range(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        result = quantizer.quantize(data, QuantizeDtype.INT8)
        assert result.data.min() >= -128
        assert result.data.max() <= 127

    def test_int4(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        result = quantizer.quantize(data, QuantizeDtype.INT4)
        assert result.data.min() >= -8
        assert result.data.max() <= 7

    def test_error_measurement(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        result = quantizer.quantize(data, QuantizeDtype.INT8)
        assert result.error >= 0.0
        assert result.max_abs_error >= 0.0

    def test_snr(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        result = quantizer.quantize(data, QuantizeDtype.FP16)
        assert np.isfinite(result.snr_db)

    def test_compare(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        results = quantizer.compare(data)
        assert len(results) == 4

    def test_best_dtype(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        dtype = quantizer.best_dtype(data, max_error=0.01)
        assert dtype in [QuantizeDtype.INT8, QuantizeDtype.UINT8, QuantizeDtype.FP16, QuantizeDtype.FP32]

    def test_to_dict(self):
        quantizer = Quantizer()
        data = np.random.randn(100).astype(np.float32)
        result = quantizer.quantize(data, QuantizeDtype.INT8)
        d = result.to_dict()
        assert "target_dtype" in d
        assert "compression_ratio" in d

    def test_constant_array(self):
        quantizer = Quantizer()
        data = np.ones(100, dtype=np.float32)
        result = quantizer.quantize(data, QuantizeDtype.INT8)
        assert np.all(result.data == result.data[0])
        assert result.data.min() >= -128
        assert result.data.max() <= 127