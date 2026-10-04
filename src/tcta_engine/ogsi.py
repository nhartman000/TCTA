"""ogsi.py -- Gamma (invariant projection) and Psi (OGSI family resolution)
as PLUGGABLE INTERFACES ONLY.

docs/OGSI.md's own scope line is explicit: this module "does not claim
that a universal invariant operator Gamma or universally separable
trajectory-family partition has already been established across all
domains." Building a concrete Gamma/Psi means deciding what "invariant
structure" and "trajectory family" mean for one specific domain (e.g.
NYCH's word-mapping pipeline) -- that is a modeling decision with its own
H1/H2 evidence obligations, not a wiring task, and this module does not
make that decision on any domain's behalf.

What this module DOES supply is the one piece transform_algebra_axioms_v1.md
SS7 and docs/OGSI.md concretely define: the test for Hypothesis H1
(prefix stability) given a caller-supplied Gamma. H1 itself remains a
hypothesis to be tested per domain -- a single passing call to
`prefix_stability_holds` is one data point, never a proof.
"""

from __future__ import annotations

from typing import Any, List, Protocol

from .core import Trajectory


class GammaOperator(Protocol):
    """Gamma: invariant-signature projection over a trajectory or prefix
    (transform_algebra_axioms_v1.md SS6). "The exact implementation of
    Gamma is domain-dependent. The formal framework requires only that its
    output be suitable for evaluating prefix stability and family
    separability" -- this module supplies no implementation, only the
    call shape a caller's Gamma must satisfy.
    """

    def __call__(self, trajectory_or_prefix: Trajectory) -> Any: ...


class PsiOperator(Protocol):
    """Psi: OGSI's family-resolution operator, G -> T_G
    (transform_algebra_axioms_v1.md SS9). Same non-universality caveat as
    GammaOperator -- domain-specific, caller-supplied.
    """

    def __call__(self, signature: Any, candidate_families: Any) -> Any: ...


def prefix_stability_holds(
    gamma: GammaOperator,
    trajectory: Trajectory,
    k: int,
) -> bool:
    """Tests Hypothesis H1 (transform_algebra_axioms_v1.md SS7,
    docs/OGSI.md "Prefix-stability dependency") for one (trajectory,
    prefix-length) pair under a caller-supplied Gamma:

        Gamma(trajectory[1:k]) == Gamma(trajectory)

    A `True` result is ONE data point supporting H1 for this trajectory at
    this k, under this Gamma -- not a proof that H1 holds for the family,
    domain, or Gamma in general. SS15's Formal Status discipline
    classifies H1 as a hypothesis regardless of how many individual tests
    pass; aggregating evidence across trajectories/domains is the caller's
    responsibility, not this function's.

    Raises ValueError if `k` is not a proper prefix length (0 < k < len(trajectory)).
    """
    n = len(trajectory)
    if not 0 < k < n:
        raise ValueError(
            f"k={k} is not a proper prefix length for a trajectory of "
            f"length {n} (SS5 requires 0 < k < n)"
        )
    return gamma(trajectory[:k]) == gamma(trajectory)


def collision_rate(
    gamma: GammaOperator,
    family_a: List[Trajectory],
    family_b: List[Trajectory],
) -> float:
    """An empirical estimate of Assumption H2's collision probability
    (transform_algebra_axioms_v1.md SS8, docs/OGSI.md "Family separability
    dependency") between two SAMPLE sets of trajectories believed to
    belong to distinct families: the fraction of cross-family pairs whose
    Gamma signatures collide.

    This is an empirical estimate over the supplied samples, not the true
    probability Pr[Gamma(T_i) = Gamma(T_j)] -- SS8 is explicit that H2 is
    "an explicit error term" requiring domain-specific empirical testing,
    which this function performs one measurement toward, not the test
    itself. Returns 0.0 for two empty/singleton-incompatible inputs rather
    than raising, since an empty sample is a valid (if uninformative)
    measurement.
    """
    if not family_a or not family_b:
        return 0.0
    collisions = 0
    total = 0
    for ta in family_a:
        sig_a = gamma(ta)
        for tb in family_b:
            total += 1
            if sig_a == gamma(tb):
                collisions += 1
    return collisions / total if total else 0.0
