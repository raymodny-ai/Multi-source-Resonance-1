"""
LLM analyzer module.
Calls LLM API for comprehensive market analysis with multi-model fallback:
OpenAI → Anthropic → Template-based fallback.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "llm_provider": "none",
        "analysis_text": "",
        "confidence": 0.0,
        "model_used": None,
        "timestamp": None,
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze market data using LLM and return score, level, signals, and details.

    Args:
        data: Market data dict containing analysis context. Expected keys:
            - gex_analysis: dict — GEX analyzer output
            - vix_analysis: dict — VIX analyzer output
            - crypto_analysis: dict — Crypto analyzer output
            - darkpool_analysis: dict — Darkpool analyzer output
            - scoring: dict — Resonance scoring output
            - api_keys: dict — {openai, anthropic} API keys

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return await _compute_llm_analysis(data)
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


async def _compute_llm_analysis(data: dict) -> dict:
    """Core LLM analysis with multi-model fallback."""
    gex = data.get("gex_analysis", {})
    vix = data.get("vix_analysis", {})
    crypto = data.get("crypto_analysis", {})
    darkpool = data.get("darkpool_analysis", {})
    scoring = data.get("scoring", {})
    api_keys = data.get("api_keys", {})

    signals = []
    provider_used = "template"
    model_used = None
    analysis_text = ""
    confidence = 0.0

    # Build context for LLM
    context = _build_context(gex, vix, crypto, darkpool, scoring)

    # Try OpenAI first
    openai_key = api_keys.get("openai")
    if openai_key:
        try:
            result = await _call_openai(openai_key, context)
            if result:
                analysis_text = result.get("text", "")
                confidence = result.get("confidence", 0.7)
                provider_used = "openai"
                model_used = result.get("model", "gpt-4o")
                signals.append("llm_openai_success")
        except Exception as e:
            logger.warning(f"OpenAI call failed: {e}")

    # Fallback to Anthropic
    if not analysis_text:
        anthropic_key = api_keys.get("anthropic")
        if anthropic_key:
            try:
                result = await _call_anthropic(anthropic_key, context)
                if result:
                    analysis_text = result.get("text", "")
                    confidence = result.get("confidence", 0.6)
                    provider_used = "anthropic"
                    model_used = result.get("model", "claude-3-sonnet")
                    signals.append("llm_anthropic_success")
            except Exception as e:
                logger.warning(f"Anthropic call failed: {e}")

    # Final fallback to template
    if not analysis_text:
        analysis_text = _template_analysis(gex, vix, crypto, darkpool, scoring)
        confidence = 0.3
        provider_used = "template"
        signals.append("llm_template_fallback")

    # Score based on analysis confidence
    raw_score = confidence * 100

    final_score = max(0.0, min(100.0, raw_score))
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "llm_provider": provider_used,
            "analysis_text": analysis_text,
            "confidence": round(confidence, 2),
            "model_used": model_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def _build_context(gex: dict, vix: dict, crypto: dict, darkpool: dict, scoring: dict) -> str:
    """Build analysis context string for LLM."""
    return json.dumps({
        "gex": {
            "net_gex": gex.get("details", {}).get("net_gex"),
            "regime": gex.get("details", {}).get("gex_regime"),
            "signals": gex.get("signals", []),
        },
        "vix": {
            "term_state": vix.get("details", {}).get("term_structure_state"),
            "panic_premium": vix.get("details", {}).get("panic_premium"),
            "signals": vix.get("signals", []),
        },
        "crypto": {
            "leverage_cleanup": crypto.get("details", {}).get("leverage_cleanup"),
            "funding_rate": crypto.get("details", {}).get("btc_funding_rate"),
            "signals": crypto.get("signals", []),
        },
        "darkpool": {
            "dix_value": darkpool.get("details", {}).get("dix_value"),
            "flow_direction": darkpool.get("details", {}).get("flow_direction"),
            "signals": darkpool.get("signals", []),
        },
        "scoring": {
            "total_score": scoring.get("normalized_score"),
            "level": scoring.get("level"),
        },
    }, indent=2)


async def _call_openai(api_key: str, context: str) -> Optional[dict]:
    """Call OpenAI API for analysis."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a quantitative analyst for a multi-source resonance "
                                "monitoring system. Analyze the market data and provide a "
                                "concise assessment of bottom-fishing signal quality. "
                                "Respond in JSON with keys: text, confidence (0-1)."
                            ),
                        },
                        {"role": "user", "content": f"Market data:\n{context}"},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # Try to parse as JSON
            try:
                parsed = json.loads(content)
                return {"text": parsed.get("text", content), "confidence": parsed.get("confidence", 0.7), "model": "gpt-4o"}
            except json.JSONDecodeError:
                return {"text": content, "confidence": 0.7, "model": "gpt-4o"}
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return None


async def _call_anthropic(api_key: str, context: str) -> Optional[dict]:
    """Call Anthropic API for analysis."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-3-sonnet-20240229",
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "You are a quantitative analyst. Analyze this market data "
                                "for bottom-fishing signal quality. Respond in JSON with "
                                "keys: text, confidence (0-1).\n\n"
                                f"Market data:\n{context}"
                            ),
                        },
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            try:
                parsed = json.loads(content)
                return {"text": parsed.get("text", content), "confidence": parsed.get("confidence", 0.6), "model": "claude-3-sonnet"}
            except json.JSONDecodeError:
                return {"text": content, "confidence": 0.6, "model": "claude-3-sonnet"}
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        return None


def _template_analysis(gex: dict, vix: dict, crypto: dict, darkpool: dict, scoring: dict) -> str:
    """Template-based fallback analysis when LLM APIs are unavailable."""
    level = scoring.get("level", "LEVEL_0")
    gex_signals = gex.get("signals", [])
    vix_signals = vix.get("signals", [])
    crypto_signals = crypto.get("signals", [])
    dp_signals = darkpool.get("signals", [])

    parts = [f"[Template Analysis] Signal Level: {level}"]

    if gex_signals:
        parts.append(f"GEX signals: {', '.join(gex_signals)}")
    if vix_signals:
        parts.append(f"VIX signals: {', '.join(vix_signals)}")
    if crypto_signals:
        parts.append(f"Crypto signals: {', '.join(crypto_signals)}")
    if dp_signals:
        parts.append(f"Darkpool signals: {', '.join(dp_signals)}")

    if level == "LEVEL_3":
        parts.append("STRONG SIGNAL: Multiple dimensions aligned for potential bottom.")
    elif level == "LEVEL_2":
        parts.append("MODERATE SIGNAL: Monitor for confirmation across remaining dimensions.")
    elif level == "LEVEL_1":
        parts.append("WEAK SIGNAL: Early stage, insufficient confirmation.")
    else:
        parts.append("NO SIGNAL: Market conditions do not meet threshold criteria.")

    return "\n".join(parts)


def _score_to_level(score: float) -> str:
    """Convert numeric score to signal level."""
    if score >= 75.0:
        return "LEVEL_3"
    elif score >= 50.0:
        return "LEVEL_2"
    elif score >= 25.0:
        return "LEVEL_1"
    return "LEVEL_0"
