"""tcta_engine -- reference implementation of the TCTA formal core.

This is the first code in this repository (`spec/transform_algebra_axioms_v1.md`,
`spec/tcta_file_format_v1.md`, and `docs/*.md` were previously documentation
only). It implements exactly what those documents concretely specify, and
nothing they explicitly decline to specify:

- `core`: SR, Transform, Trajectory, the admissible space Omega(C), the
  search-reduction factor R, and SPREAD (= 1/R) -- all concretely defined
  in transform_algebra_axioms_v1.md and tcta_file_format_v1.md.
- `hdrp`: the Hartman Dual-Register Predictor's Phi, implementing
  docs/HDRP.md's equations exactly (dual-register state, tanh forward
  projection, tracking error, gate adaptation).
- `ogsi`: Gamma (invariant projection) and Psi (OGSI family resolution) as
  pluggable interfaces ONLY. docs/OGSI.md's own scope line: "does not
  claim that a universal invariant operator Gamma ... has already been
  established across all domains." This module does not supply a Gamma or
  Psi for any domain -- it provides the H1 prefix-stability test, which
  *is* concretely defined, against a caller-supplied Gamma.
- `compliance`: the COMPLIANCE REJECT IF checks tcta_file_format_v1.md
  requires, same mechanism mg8_engine.pipeline's validate_* functions use
  for .bonit's VALIDATION blocks.
- `file_format`: parse/serialize for the `.tcta` reference block
  representation (tcta_file_format_v1.md's "Reference representation").

Per tcta_file_format_v1.md's own status boundary: this is a reference
profile, not a claimed-final implementation. ALGORITHM_SELECT's
middle-band REASON value is this module's own documented extension (see
core.select_algorithm's docstring) -- the spec says only "disclose
UNRESOLVED," it does not name a REASON token for that case.
"""

from .core import (
    StateRepresentation,
    Transform,
    admissible_trajectory_space,
    compute_spread,
    search_reduction_factor,
    select_algorithm,
)
from .hdrp import HDRP, HDRPState

__all__ = [
    "StateRepresentation",
    "Transform",
    "admissible_trajectory_space",
    "compute_spread",
    "search_reduction_factor",
    "select_algorithm",
    "HDRP",
    "HDRPState",
]
