"""Tests for MAKE Image Engine training, inference, dataset, evaluation."""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from app.make_model.image.arch import ImageConfig, ImageFoundationModel
from app.make_model.image.training import ImageTrainingConfig, ImageTrainer, SyntheticDataEngine
from app.make_model.image.inference import ImageInferenceEngine, ImageInferenceRequest
from app.make_model.image.dataset import ImageDatasetConfig, ImageDatasetEngine
from app.make_model.image.evaluation import ImageBenchmark, BenchmarkSuite, HumanEvaluationWorkflow, HumanEvaluationRecord


def test_synthetic_data_engine():
    engine = SyntheticDataEngine()
    base = np.random.rand(64, 64, 3).astype(np.float32)
    out = engine.generate_lighting_variation(base, {"intensity": 1.2})
    assert out.shape == base.shape


def test_image_trainer():
    cfg = ImageConfig.from_preset("TINY")
    model = ImageFoundationModel(cfg)
    train_cfg = ImageTrainingConfig()
    trainer = ImageTrainer(train_cfg, model)
    result = trainer.train_step({"latents": np.random.rand(1, 4, 32, 32).astype(np.float32)})
    assert "loss" in result


def test_checkpoint_save_load():
    cfg = ImageConfig.from_preset("TINY")
    model = ImageFoundationModel(cfg)
    train_cfg = ImageTrainingConfig(output_dir=tempfile.mkdtemp())
    trainer = ImageTrainer(train_cfg, model)
    path = os.path.join(train_cfg.output_dir, "test.ckpt.npz")
    trainer.save_checkpoint(path)
    assert os.path.exists(path)
    trainer.load_checkpoint(path)


def test_inference_engine():
    engine = ImageInferenceEngine()
    req = ImageInferenceRequest(prompt="test", short_side=64, num_inference_steps=2)
    result = engine.run(req)
    assert result.ok is True
    assert result.output_path is not None


def test_dataset_engine():
    cfg = ImageDatasetConfig()
    engine = ImageDatasetEngine(cfg)
    record = engine.add_sample("pixabay", "Pixabay License", (512, 512), 0.9, "test caption", b"fakebytes")
    assert record.source == "pixabay"
    manifest = engine.build_manifest()
    assert manifest["total_samples"] == 1


def test_benchmark_suite():
    benchmark = ImageBenchmark()
    assert len(benchmark.suite.cases) > 0
    categories = set(c.category for c in benchmark.suite.cases)
    assert "text_to_image" in categories
    assert "photorealism" in categories


def test_human_evaluation_workflow():
    workflow = HumanEvaluationWorkflow()
    record = HumanEvaluationRecord(evaluator_id="eval1", case_id="case1", scores={"realism": 0.9}, preferred="A")
    workflow.submit(record)
    summary = workflow.summary()
    assert summary["total_evaluations"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
