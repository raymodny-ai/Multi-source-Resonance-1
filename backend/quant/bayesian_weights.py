"""
Bayesian weight adaptation module for four-dimensional resonance scoring.

Uses Bayesian update rules to dynamically adjust dimension weights
based on historical signal outcomes (actual market performance after
signal triggers).

Integration:
    from backend.quant.bayesian_weights import BayesianWeightAdapter
    adapter = BayesianWeightAdapter()
    new_weights = adapter.update_weights(signal_outcomes)
"""

import logging
import math
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from scipy import stats as scipy_stats

from backend.quant.scoring import WEIGHTS, RAW_MAX

logger = logging.getLogger(__name__)

# Default prior parameters for each dimension
# Beta distribution parameters (alpha, beta) representing prior belief
# Higher alpha = stronger belief that dimension is predictive
# Higher beta = stronger belief that dimension is NOT predictive
_DEFAULT_PRIORS = {
    "gex": {"alpha": 5.0, "beta": 3.0},
    "vix": {"alpha": 4.0, "beta": 3.0},
    "crypto": {"alpha": 4.0, "beta": 4.0},
    "darkpool": {"alpha": 4.0, "beta": 4.0},
}

# Minimum and maximum weight bounds (fraction of RAW_MAX)
_MIN_WEIGHT_FRACTION = 0.05  # At least 5% of total
_MAX_WEIGHT_FRACTION = 0.60  # At most 60% of total

# Decay factor for older observations (0-1, higher = slower decay)
_DECAY_FACTOR = 0.95

# Minimum outcomes required before updating weights
_MIN_OUTCOMES = 10


class SignalOutcome:
    """Represents the outcome of a historical signal trigger."""

    def __init__(
        self,
        timestamp: str,
        gex_score: float,
        vix_score: float,
        crypto_score: float,
        darkpool_score: float,
        forward_return: float,
        alert_level: str = "LEVEL_0",
    ):
        self.timestamp = timestamp
        self.gex_score = gex_score
        self.vix_score = vix_score
        self.crypto_score = crypto_score
        self.darkpool_score = darkpool_score
        self.forward_return = forward_return  # Actual return after signal (in %)
        self.alert_level = alert_level

    @classmethod
    def from_dict(cls, data: dict) -> "SignalOutcome":
        """Create from a dictionary (e.g., from database query)."""
        return cls(
            timestamp=data.get("timestamp", data.get("trigger_time", "")),
            gex_score=float(data.get("gex_score", 0)),
            vix_score=float(data.get("vix_score", 0)),
            crypto_score=float(data.get("crypto_score", 0)),
            darkpool_score=float(data.get("darkpool_score", 0)),
            forward_return=float(data.get("forward_return", 0)),
            alert_level=data.get("alert_level", "LEVEL_0"),
        )


class BayesianWeightAdapter:
    """Bayesian adaptive weight adjustment for resonance scoring.

    Uses Beta-Binomial conjugate update to adjust dimension weights
    based on whether each dimension's signals were predictive of
    actual market moves.

    The core idea:
    - Each dimension has a Beta(α, β) prior on its "predictiveness"
    - After observing outcomes, we update: α += successes, β += failures
    - Weights are proportional to the posterior mean of predictiveness
    - Weights are normalized to sum to RAW_MAX (8.0)
    """

    def __init__(
        self,
        priors: Optional[dict] = None,
        decay_factor: float = _DECAY_FACTOR,
        min_outcomes: int = _MIN_OUTCOMES,
    ):
        self._priors = priors or dict(_DEFAULT_PRIORS)
        self._decay = decay_factor
        self._min_outcomes = min_outcomes
        # Current posterior parameters (initialized from priors)
        self._posteriors: dict[str, dict[str, float]] = {}
        for dim, params in self._priors.items():
            self._posteriors[dim] = {
                "alpha": params["alpha"],
                "beta": params["beta"],
            }
        # Track update history
        self._update_count = 0
        self._last_update: Optional[str] = None

    def update_weights(self, signal_outcomes: list) -> dict[str, float]:
        """Update dimension weights based on signal outcomes.

        Args:
            signal_outcomes: List of SignalOutcome objects or dicts with keys:
                - gex_score, vix_score, crypto_score, darkpool_score
                - forward_return (actual market return after signal)

        Returns:
            dict of updated weights {dimension: weight_value} summing to RAW_MAX.
        """
        if not signal_outcomes:
            logger.warning("No signal outcomes provided, returning current weights")
            return self.get_current_weights()

        # Convert dicts to SignalOutcome if needed
        outcomes = []
        for item in signal_outcomes:
            if isinstance(item, dict):
                outcomes.append(SignalOutcome.from_dict(item))
            elif isinstance(item, SignalOutcome):
                outcomes.append(item)
            else:
                logger.warning(f"Invalid outcome type: {type(item)}")

        if len(outcomes) < self._min_outcomes:
            logger.info(
                f"Only {len(outcomes)} outcomes (min={self._min_outcomes}), "
                "returning current weights"
            )
            return self.get_current_weights()

        # Apply decay to existing posteriors (forget older observations)
        self._apply_decay()

        # Calculate dimension "success" scores
        # A dimension is "successful" if its score was high AND the market moved favorably
        dimension_stats = self._calculate_dimension_stats(outcomes)

        # Bayesian update for each dimension
        for dim in ["gex", "vix", "crypto", "darkpool"]:
            dim_data = dimension_stats.get(dim, {"successes": 0, "failures": 0})
            successes = dim_data["successes"]
            failures = dim_data["failures"]

            if successes + failures == 0:
                continue

            # Beta-Binomial conjugate update
            self._posteriors[dim]["alpha"] += successes
            self._posteriors[dim]["beta"] += failures

            # Ensure parameters stay positive
            self._posteriors[dim]["alpha"] = max(0.1, self._posteriors[dim]["alpha"])
            self._posteriors[dim]["beta"] = max(0.1, self._posteriors[dim]["beta"])

        # Convert posteriors to weights
        weights = self._posteriors_to_weights()

        self._update_count += 1
        self._last_update = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Bayesian weight update #{self._update_count}: {weights} "
            f"(from {len(outcomes)} outcomes)"
        )

        return weights

    def get_current_weights(self) -> dict[str, float]:
        """Get current weight allocation."""
        return self._posteriors_to_weights()

    def get_posterior_summary(self) -> dict:
        """Get posterior distribution summary for each dimension.

        Returns:
            dict with mean, std, credible interval for each dimension.
        """
        summary = {}
        for dim, params in self._posteriors.items():
            alpha = params["alpha"]
            beta = params["beta"]

            # Beta distribution properties
            mean = alpha / (alpha + beta)
            variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
            std = math.sqrt(variance)

            # 95% credible interval
            ci_low = float(scipy_stats.beta.ppf(0.025, alpha, beta))
            ci_high = float(scipy_stats.beta.ppf(0.975, alpha, beta))

            # Current weight
            current_weight = self._posteriors_to_weights().get(dim, 0)

            summary[dim] = {
                "posterior_mean": round(mean, 4),
                "posterior_std": round(std, 4),
                "credible_interval_95": [round(ci_low, 4), round(ci_high, 4)],
                "current_weight": round(current_weight, 4),
                "prior_alpha": self._priors[dim]["alpha"],
                "prior_beta": self._priors[dim]["beta"],
                "posterior_alpha": round(alpha, 2),
                "posterior_beta": round(beta, 2),
            }

        return summary

    def get_update_stats(self) -> dict:
        """Get statistics about weight update history."""
        return {
            "update_count": self._update_count,
            "last_update": self._last_update,
            "current_weights": self.get_current_weights(),
            "decay_factor": self._decay,
            "min_outcomes": self._min_outcomes,
        }

    def reset(self) -> None:
        """Reset posteriors back to priors."""
        for dim, params in self._priors.items():
            self._posteriors[dim] = {
                "alpha": params["alpha"],
                "beta": params["beta"],
            }
        self._update_count = 0
        self._last_update = None
        logger.info("Bayesian weights reset to priors")

    def _apply_decay(self) -> None:
        """Apply exponential decay to posterior parameters.

        This gradually forgets older observations, giving more weight
        to recent market behavior.
        """
        for dim in self._posteriors:
            # Decay the "evidence" (excess over prior)
            prior_alpha = self._priors[dim]["alpha"]
            prior_beta = self._priors[dim]["beta"]

            excess_alpha = self._posteriors[dim]["alpha"] - prior_alpha
            excess_beta = self._posteriors[dim]["beta"] - prior_beta

            self._posteriors[dim]["alpha"] = prior_alpha + excess_alpha * self._decay
            self._posteriors[dim]["beta"] = prior_beta + excess_beta * self._decay

    def _calculate_dimension_stats(
        self, outcomes: list[SignalOutcome]
    ) -> dict[str, dict[str, float]]:
        """Calculate success/failure counts for each dimension.

        A dimension scores a "success" when:
        - Its score is above median AND forward return is positive, OR
        - Its score is below median AND forward return is negative

        This measures whether the dimension's signal direction was correct.
        """
        stats: dict[str, dict[str, float]] = {}

        for dim in ["gex", "vix", "crypto", "darkpool"]:
            scores = np.array([getattr(o, f"{dim}_score") for o in outcomes])
            returns = np.array([o.forward_return for o in outcomes])

            median_score = float(np.median(scores))

            successes = 0.0
            failures = 0.0

            for score, ret in zip(scores, returns):
                # Weight by signal strength (LEVEL_3 counts more)
                weight = 1.0
                if score >= 75:
                    weight = 2.0
                elif score >= 50:
                    weight = 1.5

                # Direction agreement = success
                if (score > median_score and ret > 0) or (
                    score <= median_score and ret <= 0
                ):
                    successes += weight
                else:
                    failures += weight

            stats[dim] = {"successes": successes, "failures": failures}

        return stats

    def _posteriors_to_weights(self) -> dict[str, float]:
        """Convert posterior parameters to normalized weights.

        Weights are proportional to posterior means, normalized to sum to RAW_MAX.
        Bounds are applied to prevent any dimension from being too small or too large.
        """
        # Calculate posterior means
        means = {}
        for dim, params in self._posteriors.items():
            alpha = params["alpha"]
            beta = params["beta"]
            means[dim] = alpha / (alpha + beta)

        # Apply bounds
        min_weight = RAW_MAX * _MIN_WEIGHT_FRACTION
        max_weight = RAW_MAX * _MAX_WEIGHT_FRACTION

        raw_weights = {}
        for dim, mean in means.items():
            # Scale mean to weight space
            w = mean * RAW_MAX
            w = max(min_weight, min(max_weight, w))
            raw_weights[dim] = w

        # Normalize to sum to RAW_MAX
        total = sum(raw_weights.values())
        if total > 0:
            normalized = {dim: round(w * RAW_MAX / total, 4) for dim, w in raw_weights.items()}
        else:
            # Fallback to equal weights
            n = len(raw_weights)
            normalized = {dim: round(RAW_MAX / n, 4) for dim in raw_weights}

        return normalized


# ── Integration with scoring.py ─────────────────────────────────────────────


def get_adapted_weights(signal_outcomes: list) -> dict[str, float]:
    """Convenience function: update and return adapted weights.

    Args:
        signal_outcomes: List of outcome dicts or SignalOutcome objects.

    Returns:
        dict of weights {dimension: value} summing to RAW_MAX.
    """
    adapter = BayesianWeightAdapter()
    return adapter.update_weights(signal_outcomes)


def calculate_score_with_bayesian_weights(
    gex_score: float,
    vix_score: float,
    crypto_score: float,
    darkpool_score: float,
    signal_outcomes: list,
) -> dict:
    """Calculate resonance score using Bayesian-adapted weights.

    This integrates with scoring.py by using adapted weights
    instead of the default fixed weights.

    Args:
        gex_score: GEX dimension score (0-100)
        vix_score: VIX dimension score (0-100)
        crypto_score: Crypto dimension score (0-100)
        darkpool_score: Darkpool dimension score (0-100)
        signal_outcomes: Historical outcomes for weight adaptation

    Returns:
        Scoring result dict with adapted weights applied.
    """
    adapter = BayesianWeightAdapter()
    weights = adapter.update_weights(signal_outcomes)

    # Calculate score with adapted weights
    gex_contrib = (gex_score / 100.0) * weights.get("gex", 2.0)
    vix_contrib = (vix_score / 100.0) * weights.get("vix", 2.0)
    crypto_contrib = (crypto_score / 100.0) * weights.get("crypto", 2.0)
    darkpool_contrib = (darkpool_score / 100.0) * weights.get("darkpool", 2.0)

    raw_score = gex_contrib + vix_contrib + crypto_contrib + darkpool_contrib
    normalized = (raw_score / RAW_MAX) * 100.0

    from backend.quant.scoring import determine_level

    level = determine_level(normalized)

    return {
        "normalized_score": round(normalized, 2),
        "raw_score": round(raw_score, 4),
        "raw_max": RAW_MAX,
        "level": level,
        "dimension_scores": {
            "gex": round(gex_score, 2),
            "vix": round(vix_score, 2),
            "crypto": round(crypto_score, 2),
            "darkpool": round(darkpool_score, 2),
        },
        "dimension_weights": weights,
        "bayesian_adapted": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
