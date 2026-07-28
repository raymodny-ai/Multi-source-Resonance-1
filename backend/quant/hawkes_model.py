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
        self._residuals: Optional[np.ndarray] = None

    def fit(self, event_times: np.ndarray) -> dict:
        """Fit the AR(1) model to observed event times using OLS.

        The AR(1) model: lambda(t) = a + b * lambda(t-1)
        We estimate inter-arrival intensities and regress them.

        Args:
            event_times: Array of event timestamps (sorted, in any consistent unit).

        Returns:
            dict with fitted parameters: branching_ratio, a, b, residuals_std
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

        # Compute inter-arrival times
        inter_arrivals = np.diff(event_times)

        # Convert to intensity proxies (inverse of inter-arrival time)
        # Avoid division by zero
        epsilon = 1e-10
        intensities = 1.0 / (inter_arrivals + epsilon)

        # AR(1) regression: lambda(t) = a + b * lambda(t-1)
        # Y = intensities[1:], X = intensities[:-1]
        if len(intensities) < 2:
            return {
                "branching_ratio": 0.0,
                "a": float(np.mean(intensities)),
                "b": 0.0,
                "residuals_std": 0.0,
                "n_events": len(event_times),
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

        # Clamp branching ratio to [0, 1]
        b_hat = max(0.0, min(1.0, b_hat))

        # Ensure stationarity (a > 0 for positive intensity)
        a_hat = max(0.0, a_hat)

        # Compute residuals
        Y_pred = a_hat + b_hat * X
        resid = Y - Y_pred
        resid_std = float(np.std(resid)) if len(resid) > 0 else 0.0

        self._fitted = True
        self._branching_ratio = b_hat
        self._residuals = resid

        # Update model parameters
        self.mu = a_hat
        self.alpha = b_hat  # In AR(1), branching ratio = self-excitation coefficient

        return {
            "branching_ratio": round(b_hat, 4),
            "a": round(a_hat, 6),
            "b": round(b_hat, 4),
            "residuals_std": round(resid_std, 6),
            "n_events": len(event_times),
        }

    def predict_intensity(self, n_steps: int = 10) -> np.ndarray:
        """Predict future intensity trajectory.

        Args:
            n_steps: Number of future time steps to predict.

        Returns:
            Array of predicted intensity values.
        """
        if not self._fitted:
            # Use initial parameters
            intensities = np.zeros(n_steps)
            intensities[0] = self.mu
            for t in range(1, n_steps):
                intensities[t] = self.mu + self.alpha * intensities[t - 1]
            return intensities

        # Start from steady state
        steady_state = self.mu / (1.0 - self.alpha) if self.alpha < 1.0 else self.mu
        intensities = np.zeros(n_steps)
        intensities[0] = steady_state
        for t in range(1, n_steps):
            intensities[t] = self.mu + self.alpha * intensities[t - 1]

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
        if current_intensity is None:
            if self._fitted and self.alpha < 1.0:
                current_intensity = self.mu / (1.0 - self.alpha)
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
        """
        if not self._fitted:
            import copy
            result = copy.deepcopy(_DEFAULT_RESULT)
            result["baseline_intensity"] = self.mu
            result["self_excitation_intensity"] = self.alpha
            result["decay_rate"] = self.beta
            return result

        br = self._branching_ratio
        sig_prob = self.signal_probability()
        regime = self.get_regime()

        return {
            "branching_ratio": round(br, 4),
            "baseline_intensity": round(self.mu, 6),
            "self_excitation_intensity": round(self.alpha, 4),
            "decay_rate": round(self.beta, 4),
            "signal_probability": round(sig_prob, 4),
            "regime": regime,
            "confidence": round(max(0.0, min(1.0, 1.0 - (np.std(self._residuals) / (np.mean(np.abs(self._residuals)) + 1e-10)))) if self._residuals is not None and len(self._residuals) > 0 else 0.0, 4),
            "n_events": len(self._residuals) + 1 if self._residuals is not None else 0,
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
