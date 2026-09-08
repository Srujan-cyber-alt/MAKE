"""Tests for Experiment Engine."""

import pytest
from app.intelligence.agent.experiment_engine import (
    ExperimentEngine, Experiment, ExperimentResult, ExperimentVariant
)


class TestExperimentEngine:
    def test_create_experiment_engine(self):
        engine = ExperimentEngine()
        assert engine is not None

    def test_create_experiment(self):
        engine = ExperimentEngine()
        experiment = engine.create_experiment(
            name="Test Experiment",
            hypothesis="Strategy A is better than B",
            variants=[
                ExperimentVariant(name="A", strategy="strategy_a"),
                ExperimentVariant(name="B", strategy="strategy_b"),
            ],
        )
        assert experiment is not None
        assert experiment.name == "Test Experiment"
        assert len(experiment.variants) == 2

    def test_run_experiment(self):
        engine = ExperimentEngine()
        experiment = engine.create_experiment(
            name="Run Test",
            hypothesis="A wins",
            variants=[
                ExperimentVariant(name="A", strategy="a"),
                ExperimentVariant(name="B", strategy="b"),
            ],
        )
        result = engine.run_experiment(experiment)
        assert result is not None
        assert isinstance(result, ExperimentResult)

    def test_select_winner(self):
        engine = ExperimentEngine()
        experiment = engine.create_experiment(
            name="Winner Test",
            hypothesis="A wins",
            variants=[
                ExperimentVariant(name="A", strategy="a"),
                ExperimentVariant(name="B", strategy="b"),
            ],
        )
        result = engine.run_experiment(experiment)
        assert result.winner is not None

    def test_experiment_records_metrics(self):
        engine = ExperimentEngine()
        experiment = engine.create_experiment(
            name="Metrics Test",
            hypothesis="A is faster",
            variants=[ExperimentVariant(name="A", strategy="a")],
        )
        result = engine.run_experiment(experiment)
        assert result.metrics is not None
        assert isinstance(result.metrics, dict)
