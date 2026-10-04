"""hdrp.py -- the Hartman Dual-Register Predictor's Phi, implementing
docs/HDRP.md's equations exactly. Per that document's own "Implementation
status discipline": if this code differs from the spec, the discrepancy
must be reported explicitly rather than silently changing either one.

HDRP predicts only inside a trajectory family already resolved by OGSI
(Psi) -- it is not a global planner and this module does not claim it is
one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List


def _sub(a: List[float], b: List[float]) -> List[float]:
    return [x - y for x, y in zip(a, b)]


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _l2(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _clip_unit(x: float) -> float:
    """Pi_[0,1]: projection into the stable gate interval, docs/HDRP.md's
    "Gate adaptation" section."""
    return max(0.0, min(1.0, x))


@dataclass
class HDRPState:
    """The dual registers docs/HDRP.md's "Dual-register state" section
    names explicitly: present state R_0, previous state R_{-1}, plus the
    adaptive gate g_t this module threads through `HDRP.step`."""

    r0: List[float]
    r_prev: List[float]
    gate: float = 0.5  # g_t; no canonical initial value is specified, 0.5
                        # is this module's own neutral starting point.

    def trajectory_delta(self) -> List[float]:
        """T_t = R_0 - R_{-1}."""
        return _sub(self.r0, self.r_prev)


@dataclass
class HDRP:
    """Stateful HDRP predictor. One instance tracks one localized
    continuation inside a trajectory family already resolved by OGSI.

    `alpha`, `eta`, `lambda_rec` are the operating parameters
    tcta_file_format_v1.md's PARAMETERS block carries per run/unit (ALPHA,
    ETA, LAMBDA_REC) -- never hard-coded defaults pretending to be the
    algebra itself.
    """

    state: HDRPState
    alpha: float
    eta: float
    lambda_rec: float
    _last_error: float = field(default=0.0, repr=False)

    def forward_projection(self) -> List[float]:
        """O_t = tanh(R_0 + g_t * alpha * T_t), docs/HDRP.md's "Forward
        projection" section -- the predicted successor state."""
        T = self.state.trajectory_delta()
        g = self.state.gate
        return [
            math.tanh(r0_i + g * self.alpha * t_i)
            for r0_i, t_i in zip(self.state.r0, T)
        ]

    def step(self, observed_next: List[float]) -> dict:
        """One HDRP cycle against an observed successor state I_{t+1}:

        1. compute O_t = forward_projection() using the CURRENT gate g_t;
        2. E_t = ||O_t - I_{t+1}||_2 (tracking error);
        3. delta_E_t = E_t - E_{t-1};
        4. delta_g_t = -eta * delta_E_t * sign(T_t . O_t);
        5. g_{t+1} = Pi_[0,1](g_t * lambda_rec + delta_g_t).

        This computes and stores g_{t+1} on `self.state.gate` but does NOT
        roll the registers (R_{-1} <- R_0, R_0 <- observed_next) -- that is
        a separate, explicit decision the caller makes via `advance`,
        since docs/HDRP.md does not specify that every step necessarily
        commits to the observed state as the new present register (e.g. a
        rejected/UNRESOLVED gate result per core.select_algorithm should
        not silently advance the registers).

        Returns a disclosed record of every intermediate quantity, not
        just the final gate -- same auditability bar as the rest of the
        file family's QSON entries.
        """
        T = self.state.trajectory_delta()
        O_t = self.forward_projection()
        E_t = _l2(O_t, observed_next)
        delta_E = E_t - self._last_error
        dot = _dot(T, O_t)
        sign = 1.0 if dot > 0 else (-1.0 if dot < 0 else 0.0)
        delta_g = -self.eta * delta_E * sign
        g_next = _clip_unit(self.state.gate * self.lambda_rec + delta_g)

        record = {
            "trajectory_delta": T,
            "forward_projection": O_t,
            "tracking_error": E_t,
            "error_delta": delta_E,
            "gate_delta": delta_g,
            "gate_before": self.state.gate,
            "gate_after": g_next,
            "sign_T_dot_O": sign,
        }

        self.state.gate = g_next
        self._last_error = E_t
        return record

    def advance(self, new_r0: List[float]) -> None:
        """Rolls the dual registers forward: R_{-1} <- R_0, R_0 <- new_r0.
        Separate from `step` by design -- see `step`'s docstring."""
        self.state.r_prev = self.state.r0
        self.state.r0 = new_r0
