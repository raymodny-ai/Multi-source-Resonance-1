"""
Pipeline <-> quant adapter.

Wires the quant analyzer layer (backend/quant/*_analyzer.py) and scoring engine
(backend/quant/scoring.py) into the Pipeline's Phase 2/3 slots.

`register_pipeline_analyzers_and_scorer(pipeline)` is called once during app
startup (backend/main.py lifespan) after the Pipeline is constructed but before
the background loop starts. Without it the Pipeline runs Phase 2 with
"[Phase 2] No analyzers registered" and falls back to `basic_fallback` scoring,
which yields total_score=0 and never writes signal_alerts rows → the frontend
heatmap / signals / alerts stay empty.

Source-name keys below MUST match the Fetcher.source_name values (they are the
keys of `collected_data` passed into Phase 2). Fetcher -> analyzer mapping:
    GEXMetrix          -> gex_analyze
    VIX                -> vix_analyze
    crypto_derivatives -> crypto_analyze
    dark_pool_metrics  -> darkpool_analyze
"""

from __future__ import annotations

import logging

from backend.quant import (
    gex_analyze,
    vix_analyze,
    crypto_analyze,
    darkpool_analyze,
    calculate_score,
)

logger = logging.getLogger(__name__)

# Fetcher.source_name -> quant analyzer
ANALYZER_MAP: dict[str, object] = {
    "GEXMetrix": gex_analyze,
    "VIX": vix_analyze,
    "crypto_derivatives": crypto_analyze,
    "dark_pool_metrics": darkpool_analyze,
}

# Scorer returns keys the Pipeline/_persist + frontend expect:
#   total_score, gex_score, vix_score, crypto_score, darkpool_score, alert_level
async def resonance_scorer(analysis_results: dict[str, dict]) -> dict:
    """Async scorer for Pipeline.Phase 3.

    Reads the four analyzer outputs (keyed by source_name) from analysis_results,
    runs the quant resonance scorer, and flattens the result into the
    pipeline/db/frontend schema.
    """
    def _score_of(src: str) -> float:
        res = analysis_results.get(src) or {}
        # analyzer outputs carry score under "score"; be defensive on shape.
        if isinstance(res, dict) and "score" in res:
            return float(res.get("score") or 0.0)
        return 0.0

    gex_s = _score_of("GEXMetrix")
    vix_s = _score_of("VIX")
    crypto_s = _score_of("crypto_derivatives")
    dark_s = _score_of("dark_pool_metrics")

    scoring = calculate_score(
        gex_score=gex_s,
        vix_score=vix_s,
        crypto_score=crypto_s,
        darkpool_score=dark_s,
    )

    dims = scoring.get("dimension_scores", {})
    out = {
        "total_score": float(scoring.get("normalized_score", 0.0)),
        "raw_score": float(scoring.get("raw_score", 0.0)),
        "gex_score": float(dims.get("gex", gex_s)),
        "vix_score": float(dims.get("vix", vix_s)),
        "crypto_score": float(dims.get("crypto", crypto_s)),
        "darkpool_score": float(dims.get("darkpool", dark_s)),
        "signals": scoring.get("signals", []),
        "scorer": "quant_resonance",
        "details": scoring,
    }
    return out


def register_pipeline_analyzers_and_scorer(pipeline) -> None:
    """Register the quant analyzer + scorer onto the pipeline (Phase 2/3)."""
    for source_name, analyzer in ANALYZER_MAP.items():
        pipeline.register_analyzer(source_name, analyzer)
    pipeline.register_scorer(resonance_scorer)
    logger.info(
        "Registered %d quant analyzers + quant_resonance scorer onto pipeline",
        len(ANALYZER_MAP),
    )
