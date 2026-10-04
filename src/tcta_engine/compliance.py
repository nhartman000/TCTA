"""compliance.py -- the COMPLIANCE REJECT IF checks tcta_file_format_v1.md
requires, against a reasoning step's actual output. Same mechanism and the
same stance mg8_engine.pipeline's validate_mapping_plan/
validate_congruence_response take toward .bonit's VALIDATION blocks: the
reasoning step is not trusted to have followed the rules, its output is
checked.

tcta_file_format_v1.md, "Forcing compliance: the engine isn't optional":

    REJECT IF ALGORITHM_SUBSTITUTED
    REJECT IF GOAL_PURSUED_WITHOUT_OMEGA_C
    REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION

`core.select_algorithm` already enforces the third rule by construction
(it cannot return a result without a computed SPREAD). The functions here
are for validating an already-produced claim of having run the engine --
e.g. an LLM's response asserting it computed SPREAD and selected an
algorithm -- the same role validate_congruence_response plays for an
LLM's congruence-assessment response.
"""

from __future__ import annotations

from typing import Any, Optional


class ComplianceError(ValueError):
    """Raised when a reasoning step's output violates .tcta's COMPLIANCE
    block. Never repaired silently."""


class AlgorithmSubstituted(ComplianceError):
    """REJECT IF ALGORITHM_SUBSTITUTED: the reasoning step used a
    different narrowing/selection method than the one ENGINE names, with
    or without disclosing it."""


class GoalPursuedWithoutOmegaC(ComplianceError):
    """REJECT IF GOAL_PURSUED_WITHOUT_OMEGA_C: a trajectory toward
    GOAL.DESIRED_SR was proposed without first computing (or disclosing
    UNKNOWN for) the admissible space Omega(C)."""


class SpreadNotComputedBeforeSelection(ComplianceError):
    """REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION: no algorithm may be
    selected until SPREAD is computed for this step. Re-exported here
    (same exception core.select_algorithm raises) so callers validating a
    response can catch one compliance exception family from this module."""


def check_algorithm_not_substituted(
    declared_method_ref: str,
    used_method_ref: Optional[str],
) -> None:
    """`declared_method_ref` is the ENGINE.GAMMA_REF/PSI_REF/PHI_REF (or a
    caller-chosen identifier for "the engine this unit declared") the
    reasoning step was handed; `used_method_ref` is what the step's output
    claims it actually used. `None` or a mismatch is a substitution,
    disclosed or not -- the rule does not distinguish the two.
    """
    if used_method_ref != declared_method_ref:
        raise AlgorithmSubstituted(
            f"reasoning step used {used_method_ref!r}, not the declared "
            f"engine {declared_method_ref!r} (REJECT IF ALGORITHM_SUBSTITUTED)"
        )


def check_goal_requires_omega_c(
    desired_sr: Any,
    omega_c_computed: bool,
    omega_c_disclosed_unknown: bool = False,
) -> None:
    """`desired_sr` is GOAL.DESIRED_SR (None means no stated/inferred goal
    -- trajectory narrowing is a pure filter, this check does not apply).
    `omega_c_computed` is whether Omega(C) was actually computed for this
    step; `omega_c_disclosed_unknown` is whether the step instead
    explicitly disclosed UNKNOWN for it (the rule's own stated escape
    hatch: "or disclosing UNKNOWN for").
    """
    if desired_sr is None:
        return
    if not omega_c_computed and not omega_c_disclosed_unknown:
        raise GoalPursuedWithoutOmegaC(
            "a trajectory toward GOAL.DESIRED_SR was proposed without "
            "computing Omega(C) or disclosing UNKNOWN for it "
            "(REJECT IF GOAL_PURSUED_WITHOUT_OMEGA_C)"
        )


def check_spread_before_selection(
    spread_value: Optional[float],
    algorithm_select_result: Optional[str],
) -> None:
    """Validates an already-produced .tcta-shaped response: if
    ALGORITHM_SELECT.RESULT is set, SPREAD.VALUE must have been set first.
    `core.select_algorithm` enforces this by construction when the engine
    itself is called directly; this function is for checking a response
    that claims to have done so (e.g. from an LLM, or a reloaded .tcta
    file) without having gone through `core.select_algorithm`.
    """
    if algorithm_select_result is not None and spread_value is None:
        raise SpreadNotComputedBeforeSelection(
            "ALGORITHM_SELECT.RESULT is set but SPREAD.VALUE is null "
            "(REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION)"
        )


def check_compliance(
    *,
    declared_method_ref: str,
    used_method_ref: Optional[str],
    desired_sr: Any,
    omega_c_computed: bool,
    spread_value: Optional[float],
    algorithm_select_result: Optional[str],
    omega_c_disclosed_unknown: bool = False,
) -> None:
    """Runs all three COMPLIANCE checks in the order tcta_file_format_v1.md
    lists them. Raises the first violation encountered; never repairs
    silently and never continues past a violation to report "all" errors
    at once (consistent with mg8_engine.pipeline's validate_* functions)."""
    check_algorithm_not_substituted(declared_method_ref, used_method_ref)
    check_goal_requires_omega_c(desired_sr, omega_c_computed, omega_c_disclosed_unknown)
    check_spread_before_selection(spread_value, algorithm_select_result)
