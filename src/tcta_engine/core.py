"""core.py -- SR, Transform, Trajectory, Omega(C), R, and SPREAD.

Concretely defined by transform_algebra_axioms_v1.md SS2-4 and SS11, and by
tcta_file_format_v1.md's "Dynamic algorithm selection by spread" section.
Nothing here invents domain semantics: what a transform actually computes
(`f_T`), what makes a resulting state valid (`constraint_check`), and what
the search/effort measure S(X) is are all caller-supplied, because the
axioms document says explicitly that admissibility is domain-relative and
that the relationship between search-space measure and real computational
cost "must be stated for each implementation" (SS11).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# SS2-4: State representation, transform, trajectory, admissible space
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateRepresentation:
    """SR = (s, D, C), transform_algebra_axioms_v1.md SS2.

    `s` is the current state vector/configuration, `domain` is the active
    domain/projection context (D), `constraints` is the active
    constraint/container geometry (C). All three are left as `Any`: this
    module does not define what a state, a domain, or a constraint set look
    like for any particular use of TCTA.
    """

    s: Any
    domain: Any
    constraints: Any


@dataclass(frozen=True)
class Transform:
    """T: SR_i -> SR_j, transform_algebra_axioms_v1.md SS3.

    `apply` is the state action f_T(s_i) = s_j. TCTA does not assume every
    transform has a global inverse or that composition is commutative
    (SS1) -- this type makes no such assumption either.
    """

    transform_id: str
    apply: Callable[[Any], Any]

    def result_state(self, sr_i: StateRepresentation) -> Any:
        """f_T(s_i)."""
        return self.apply(sr_i.s)

    def is_admissible(
        self,
        sr_i: StateRepresentation,
        constraint_check: Callable[[Any, Any], bool],
    ) -> bool:
        """A transform is admissible only when its resulting state remains
        valid under the active domain and constraints (SS3). `constraint_check
        (s_j, C) -> bool` is caller-supplied -- validity is domain-specific."""
        return constraint_check(self.result_state(sr_i), sr_i.constraints)


# An ordered transform sequence (SS4). Order is part of the object: two
# trajectories with the same transforms in different orders need not be
# equivalent, so this is a plain ordered list, never a set.
Trajectory = List[Transform]


def is_admissible_trajectory(
    trajectory: Trajectory,
    sr_0: StateRepresentation,
    constraint_check: Callable[[Any, Any], bool],
) -> bool:
    """SS4's explicit form of Omega(C) membership for one trajectory: every
    transform's result must satisfy constraint_check at each step, starting
    from sr_0 and threading the resulting state through the sequence."""
    sr = sr_0
    for t in trajectory:
        if not t.is_admissible(sr, constraint_check):
            return False
        sr = StateRepresentation(t.result_state(sr), sr.domain, sr.constraints)
    return True


def admissible_trajectory_space(
    candidates: Iterable[Trajectory],
    sr_0: StateRepresentation,
    constraint_check: Callable[[Any, Any], bool],
) -> List[Trajectory]:
    """Omega(C): filters `candidates` down to the admissible trajectories
    (SS4). This does NOT enumerate the full potential future space --
    `candidates` is caller-supplied. Generating every possible trajectory is
    a domain-specific, generally intractable problem this module does not
    claim to solve; it only implements the admissibility filter once a
    candidate set exists.
    """
    return [t for t in candidates
            if is_admissible_trajectory(t, sr_0, constraint_check)]


# ---------------------------------------------------------------------------
# SS11 + tcta_file_format_v1.md: search reduction factor R, SPREAD
# ---------------------------------------------------------------------------


def search_reduction_factor(s_omega_c: float, s_tg: float) -> float:
    """R = S(Omega(C)) / S(T_G), SS11. `s_omega_c`/`s_tg` are the caller's
    chosen search/effort measure S(X) applied to each space -- SS11 is
    explicit that the relationship between this measure and actual
    computational cost must be stated per implementation; this function
    does not supply or assume one.

    Raises ValueError if s_tg <= 0 (R undefined) or s_tg > s_omega_c (T_G
    not a subset of Omega(C), which SS10 requires it to be).
    """
    if s_tg <= 0:
        raise ValueError("S(T_G) must be positive to compute R")
    if s_tg > s_omega_c:
        raise ValueError(
            "S(T_G) exceeds S(Omega(C)); T_G must be a subset of the "
            "admissible space (SS10)"
        )
    return s_omega_c / s_tg


def compute_spread(s_tg: float, s_omega_c: float) -> float:
    """SPREAD = 1/R = S(T_G) / S(Omega(C)), tcta_file_format_v1.md's
    "Dynamic algorithm selection by spread" section. Not a new quantity --
    the inverse of `search_reduction_factor`, computed directly here rather
    than via division-of-a-division to avoid a spurious float round-trip.
    """
    if s_omega_c <= 0:
        raise ValueError("S(Omega(C)) must be positive to compute SPREAD")
    if s_tg > s_omega_c:
        raise ValueError(
            "S(T_G) exceeds S(Omega(C)); T_G must be a subset of the "
            "admissible space (SS10)"
        )
    return s_tg / s_omega_c


# ---------------------------------------------------------------------------
# ALGORITHM_SELECT
# ---------------------------------------------------------------------------

#: Values tcta_file_format_v1.md's ALGORITHM_SELECT.RESULT may take.
ALGORITHM_RESULTS = ("HDRP_LOCALIZED", "UNRESOLVED")

#: REASON tokens tcta_file_format_v1.md names explicitly: "spread_low",
#: "spread_high", "epsilon_high", "not_yet_computed". "middle_band_undefined"
#: is this module's own addition -- the spec requires disclosing UNRESOLVED
#: for a SPREAD strictly between the two thresholds ("Between the two
#: thresholds: not yet defined by this spec... disclose UNRESOLVED") but
#: does not name a REASON token for that specific case, and reusing
#: "spread_high" would misreport which threshold actually fired. Flagging
#: this here rather than silently picking one of the spec's four tokens.
REASON_MIDDLE_BAND_UNDEFINED = "middle_band_undefined"


class SpreadNotComputedBeforeSelection(ValueError):
    """COMPLIANCE: REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION. No
    algorithm may be selected until SPREAD is computed for this step."""


def select_algorithm(
    spread: Optional[float],
    spread_low: float,
    spread_high: float,
    *,
    epsilon: Optional[float] = None,
    epsilon_max: Optional[float] = None,
) -> Tuple[str, str]:
    """ALGORITHM_SELECT, tcta_file_format_v1.md's routing rule:

        SPREAD <= SPREAD_LOW  -> HDRP_LOCALIZED ("spread_low")
        SPREAD >= SPREAD_HIGH -> UNRESOLVED      ("spread_high")
        between the two        -> UNRESOLVED      (REASON_MIDDLE_BAND_UNDEFINED;
                                                     see that constant's docstring)

    A high H2 collision bound epsilon overrides a low SPREAD and also
    routes to UNRESOLVED ("epsilon_high"), regardless of how tight the
    family looks in isolation -- checked before the SPREAD thresholds.

    Raises SpreadNotComputedBeforeSelection if `spread` is None (COMPLIANCE:
    REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION) -- enforced by
    construction: there is no code path in this function that returns a
    result without a computed spread value.
    """
    if spread is None:
        raise SpreadNotComputedBeforeSelection(
            "ALGORITHM_SELECT requires SPREAD.VALUE to be computed first "
            "(mg8.bonit/tcta_file_format_v1.md COMPLIANCE: REJECT IF "
            "SPREAD_NOT_COMPUTED_BEFORE_SELECTION)"
        )

    if epsilon is not None and epsilon_max is not None and epsilon >= epsilon_max:
        return "UNRESOLVED", "epsilon_high"

    if spread <= spread_low:
        return "HDRP_LOCALIZED", "spread_low"

    if spread >= spread_high:
        return "UNRESOLVED", "spread_high"

    return "UNRESOLVED", REASON_MIDDLE_BAND_UNDEFINED
