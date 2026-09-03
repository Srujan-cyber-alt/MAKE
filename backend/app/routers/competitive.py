"""
Phase 22 Competitive Benchmark API Router.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User
from app.services.competitive_gap_engine import competitive_gap_engine
from app.services.competitive_capability_matrix import competitive_capability_matrix
from app.services.competitor_benchmark import competitor_benchmark, BenchmarkCase

router = APIRouter()


@router.get("/competitive/gaps")
async def get_competitive_gaps(current_user: User = Depends(get_current_user)):
    make_caps = competitive_capability_matrix.get_make_capabilities()
    competitor_caps = competitive_capability_matrix.get_competitor_capabilities()
    
    gaps = []
    for competitor, caps in competitor_caps.items():
        for comp_cap in caps:
            for make_cap in make_caps:
                if make_cap["name"] == comp_cap["name"]:
                    gaps.append(competitive_gap_engine.analyze_gap(make_cap, comp_cap))
    
    summary = {
        "total": len(gaps),
        "matched": sum(1 for g in gaps if g["gap"] == "matched"),
        "exceeded": sum(1 for g in gaps if g["gap"] == "exceeded"),
        "partially_matched": sum(1 for g in gaps if g["gap"] == "partially_matched"),
        "missing": sum(1 for g in gaps if g["gap"] == "missing"),
    }
    return {"gaps": gaps, "summary": summary}


@router.get("/competitive/matrix")
async def get_capability_matrix(current_user: User = Depends(get_current_user)):
    return competitive_capability_matrix.build_matrix()


@router.get("/benchmark/cases")
async def get_benchmark_cases(count: int = 100, current_user: User = Depends(get_current_user)):
    cases = competitor_benchmark.get_benchmark_cases(count)
    return {"cases": cases, "total": len(cases)}


@router.get("/benchmark/summary")
async def get_benchmark_summary(current_user: User = Depends(get_current_user)):
    cases = competitor_benchmark.get_benchmark_cases(100)
    summary = competitor_benchmark.summarize_results(cases)
    return summary


@router.get("/runtime/neural")
async def get_neural_runtime_report(current_user: User = Depends(get_current_user)):
    from app.providers.neural_interface import get_neural_runtime_report
    report = get_neural_runtime_report()
    return report.to_dict()


@router.get("/runtime/providers")
async def get_provider_classifications(current_user: User = Depends(get_current_user)):
    from app.providers.registry import get_provider_registry
    from app.providers.neural_interface import get_generation_mode
    registry = get_provider_registry()
    result = {
        "generation_mode": get_generation_mode().value,
        "providers": {},
    }
    for name, provider in registry.get_all().items():
        classification = "unknown"
        if hasattr(provider, "get_classification"):
            try:
                classification = provider.get_classification()
            except Exception:
                classification = "unknown"
        result["providers"][name] = {
            "classification": classification,
        }
    return result
