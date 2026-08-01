"""
Hawkes AR(1) self-exciting process model.
Implements Hawkes process for signal self-excitation intensity prediction,
AR(1) branching ratio tracking, and signal trigger probability estimation.

Model:
  lambda(t) = mu + sum(alpha * exp(-beta * (t - t_i)))   (Hawkes process)
  lambda(t) = a + b * lambda(t-1)                         (AR(1) simplification)

Parameters:
  mu  — baseline intensity (background arrival rate)
  alpha — self-excitation intensity (jump size per event)
  beta  — decay rate (mean reversion speed)

OLS fitting for branching ratio b (0-1):
  b > 0.5: high self-excitation (signals tend to cluster and cascade)
  b in [0.2, 0.5]: moderate self-excitation
  b < 0.2: low self-excitation (signals are mostly independent)
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "branching_ratio": 0.0,
    "baseline_intensity": 0.0,
    "self_excitation_intensity": 0.0,
    "decay_rate": 0.0,
    "signal_probability": 0.0,
    "regime": "low",
    "confidence": 0.0,
    "n_events": 0,
}


class HawkesAR1Model:
    """Hawkes process with AR(1) approximation for signal self-excitation modeling.

    The AR(1) simplification replaces the full Hawkes integral with a simple
    first-order autoregressive model: lambda(t) = a + b * lambda(t-1).

    The branching ratio 'b' measures how much one signal triggers follow-up signals.
    """

    def __init__(
        self,
        mu: float = 0.1,
        alpha: float = 0.3,
        beta: float = 1.0,
    ) -> None:
        """Initialize Hawkes AR(1) model.

        Args:
            mu: Baseline intensity (background signal rate). Default 0.1.
            alpha: Self-excitation intensity (jump per event). Default 0.3.
            beta: Decay rate (how fast excitation fades). Default 1.0.
        """
        self.mu = mu
        self.alpha = alpha
        self.beta = beta
        self._fitted = False
        self._branching_ratio = 0.0
        self._n_events = 0
        self._residuals: Optional[np.ndarray] = None
        self._y_target: Optional[np.ndarray] = None

    def fit(self, event_times: np.ndarray) -> dict:
        """Fit the AR(1) model to observed event times using OLS.

        The AR(1) model: lambda(t) = a + b * lambda(t-1)
        We estimate inter-arrival intensities and regress them.

        Args:
            event_times: Array of event timestamps (sorted, in any consistent unit).

        Returns:
            dict with fitted parameters: branching_ratio, a, b, residuals_std.
            The branching ratio is NOT clamped to [0,1]: values >1 indicate a
            supercritical (explosive) self-exciting regime, which is meaningful
            in Hawkes processes (branching ratio n = alpha / beta).
        """
        if event_times is None or len(event_times) < 3:
            logger.warning("Need at least 3 events for AR(1) fitting")
            return {
                "branching_ratio": 0.0,
                "a": self.mu,
                "b": 0.0,
                "residuals_std": 0.0,
                "n_events": len(event_times) if event_times is not None else 0,
            }

        event_times = np.asarray(event_times, dtype=float)
        event_times = np.sort(event_times)
        self._n_events = len(event_times)

        # Deduplicate timestamps: identical times (e.g. same-second signals)
        # produce zero inter-arrival times, which explode to 1/epsilon intensities
        # and dominate the OLS fit. Collapse runs of equal timestamps into one.
        unique_times = np.unique(event_times)
        if len(unique_times) < 3:
            # Not enough distinct events after dedup to fit AR(1) meaningfully.
            self._branching_ratio = 0.0
            return {
                "branching_ratio": 0.0,
                "a": float(np.mean(unique_times)) if len(unique_times) else self.mu,
                "b": 0.0,
                "residuals_std": 0.0,
                "n_events": self._n_events,
            }

        # Compute inter-arrival times (all > 0 after dedup)
        inter_arrivals = np.diff(unique_times)

        # Scale-aware epsilon: guard any residual zero/underflow without
        # dominating typical inter-arrival magnitudes. 1e-10 was far too small
        # and turned genuine zero diffs into 1e10 outliers.
        scale = float(np.median(inter_arrivals)) if len(inter_arrivals) else 1.0
        epsilon = max(1e-9, scale * 1e-6)
        raw_intensities = 1.0 / (inter_arrivals + epsilon)

        # Log1p transform of intensities before OLS. The raw 1/inter-arrival
        # scale spans many orders of magnitude (an explosive gap vs. a quiet one),
        # so a direct OLS on raw values is dominated by the extreme tail and
        # produces near-zero / unstable slopes. log1p compresses the range and
        # yields a robust AR(1) persistence estimate (per QA report #3).
        intensities = np.log1p(raw_intensities)

        # AR(1) regression: lambda(t) = a + b * lambda(t-1)
        # Y = intensities[1:], X = intensities[:-1]
        if len(intensities) < 2:
            return {
                "branching_ratio": 0.0,
                "a": float(np.mean(intensities)),
                "b": 0.0,
                "residuals_std": 0.0,
                "n_events": self._n_events,
            }

        Y = intensities[1:]
        X = intensities[:-1]

        # OLS: [a, b] = (X'X)^-1 X'Y
        X_design = np.column_stack([np.ones(len(X)), X])
        try:
            coeffs, residuals, rank, _ = np.linalg.lstsq(X_design, Y, rcond=None)
            a_hat = float(coeffs[0])
            b_hat = float(coeffs[1])
        except np.linalg.LinAlgError:
            logger.warning("OLS fitting failed, using defaults")
            a_hat = float(np.mean(intensities))
            b_hat = 0.0

        # Lower-bound only: negative self-excitation is not meaningful, but we
        # deliberately DO NOT cap the upper end — branching ratio >1 represents
        # a supercritical (explosive) regime the frontend is designed to surface.
        b_hat = max(0.0, b_hat)

        # Ensure stationarity (a > 0 for positive intensity)
        a_hat = max(0.0, a_hat)

        # Compute residuals
        Y_pred = a_hat + b_hat * X
        resid = Y - Y_pred
        resid_std = float(np.std(resid)) if len(resid) > 0 else 0.0

        self._fitted = True
        self._branching_ratio = b_hat
        self._residuals = resid
        self._y_target = Y

        # Do NOT overwrite self.alpha (the configured jump-size parameter) with
        # the AR(1) coefficient. The fitted branching ratio is tracked separately
        # in self._branching_ratio and reported on its own.

        return {
            "branching_ratio": round(b_hat, 4),
            "a": round(a_hat, 6),
            "b": round(b_hat, 4),
            "residuals_std": round(resid_std, 6),
            "n_events": self._n_events,
        }

    def predict_intensity(self, n_steps: int = 10) -> np.ndarray:
        """Predict future intensity trajectory.

        Args:
            n_steps: Number of future time steps to predict.

        Returns:
            Array of predicted intensity values.
        """
        # Use the fitted AR(1) self-excitation coefficient where available,
        # otherwise fall back to the configured jump-size alpha.
        a_coef = self._branching_ratio if self._fitted else self.alpha
        if not self._fitted:
            # Use initial parameters
            intensities = np.zeros(n_steps)
            intensities[0] = self.mu
            for t in range(1, n_steps):
                intensities[t] = self.mu + a_coef * intensities[t - 1]
            return intensities

        # Start from steady state (branching ratio >= 1 => no finite steady
        # state; fall back to baseline)
        steady_state = self.mu / (1.0 - a_coef) if a_coef < 1.0 else self.mu
        intensities = np.zeros(n_steps)
        intensities[0] = steady_state
        for t in range(1, n_steps):
            intensities[t] = self.mu + a_coef * intensities[t - 1]

        return intensities

    def signal_probability(self, current_intensity: Optional[float] = None) -> float:
        """Estimate probability of next signal occurring.

        Uses the fitted intensity to estimate the probability of at least
        one event in the next time unit.

        Args:
            current_intensity: Current intensity level. If None, uses steady state.

        Returns:
            Probability in [0, 1] of a signal occurring.
        """
        a_coef = self._branching_ratio if self._fitted else self.alpha
        if current_intensity is None:
            if self._fitted and a_coef < 1.0:
                current_intensity = self.mu / (1.0 - a_coef)
            else:
                current_intensity = self.mu

        # Poisson probability: P(at least 1 event) = 1 - exp(-lambda)
        prob = 1.0 - np.exp(-current_intensity)
        return float(max(0.0, min(1.0, prob)))

    def get_regime(self) -> str:
        """Classify the self-excitation regime based on branching ratio.

        Returns:
            'high' if b > 0.5, 'moderate' if 0.2 <= b <= 0.5, 'low' if b < 0.2
        """
        b = self._branching_ratio
        if b > 0.5:
            return "high"
        elif b >= 0.2:
            return "moderate"
        return "low"

    def get_summary(self) -> dict:
        """Get a summary of the fitted model.

        Returns:
            dict with model parameters and regime classification.
            - branching_ratio: fitted AR(1) self-excitation coefficient (may be
              >1 in a supercritical / explosive regime)
            - self_excitation_intensity: the fitted branching ratio (same value),
              exposed under this name for the Hawkes-process interpretation
            - decay_rate: configured beta (the AR(1) approximation does not fit a
              separate decay parameter; this is the initial decay constant)
            - confidence: R^2 of the AR(1) fit (fraction of intensity variance
              explained), meaningful in [0,1] for normal residual noise.
        """
        if not self._fitted:
            import copy
            result = copy.deepcopy(_DEFAULT_RESULT)
            result["baseline_intensity"] = self.mu
            result["self_excitation_intensity"] = self.alpha
            result["decay_rate"] = self.beta
            result["n_events"] = self._n_events
            return result

        br = self._branching_ratio
        sig_prob = self.signal_probability()
        regime = self.get_regime()

        # Confidence = R^2 of the AR(1) fit in the transformed space. This is a
        # genuine goodness-of-fit metric in [0,1] (what fraction of target
        # variance the AR(1) model explains), unlike the old
        # 1 - std/mean(|resid|) which collapses to ~0 for any normal residual.
        confidence = 0.0
        if self._residuals is not None and self._y_target is not None and len(self._residuals) > 0:
            ss_res = float(np.sum(self._residuals ** 2))
            y = self._y_target
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            if ss_tot > 0:
                r2 = 1.0 - (ss_res / ss_tot)
                confidence = max(0.0, min(1.0, r2))

        return {
            "branching_ratio": round(br, 4),
            "baseline_intensity": round(self.mu, 6),
            "self_excitation_intensity": round(br, 4),
            "decay_rate": round(self.beta, 4),
            "signal_probability": round(sig_prob, 4),
            "regime": regime,
            "confidence": round(confidence, 4),
            "n_events": self._n_events,
        }


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze signal self-excitation using Hawkes AR(1) model.

    Args:
        data: Dict with key 'event_times' (list of timestamps or numeric values).
              Can also include 'mu', 'alpha', 'beta' for custom parameters.

    Returns:
        dict with branching_ratio, signal_probability, regime, etc.
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        event_times = data.get("event_times")
        mu = data.get("mu", 0.1)
        alpha = data.get("alpha", 0.3)
        beta = data.get("beta", 1.0)

        model = HawkesAR1Model(mu=mu, alpha=alpha, beta=beta)

        if event_times is not None:
            event_array = np.array(event_times, dtype=float)
            model.fit(event_array)

        return model.get_summary()

    except Exception as e:
        logger.error(f"Hawkes analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)
