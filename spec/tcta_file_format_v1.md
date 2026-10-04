# TCTA File Format v1 — `.tcta`

**Author:** Nicholas Hartman / American Milestone Inc.
**Status:** interim specification, same bar as `.ork`/`.bonit` in `mg8`: the role is established, the serialization is a reference profile, not a claimed-final grammar.

## What `.tcta` is, and isn't

`.tcta` is not state (`.gst`), not a gate decision (`.g8son`), not position/loop control (`.ork`), not domain-specific policy (`.bonit`), and not a trace (`.qson`). It carries the one thing none of those do: the **trajectory-constraint algebra itself** — the machinery a reasoning step (today, an LLM) is handed and told to apply when deciding which candidate transforms in an `.mg8` run remain admissible.

It never restates the algebra. `GAMMA_REF`, `PSI_REF`, and `PHI_REF` below point at the canonical equations in `nhartman000/TCTA`'s `spec/transform_algebra_axioms_v1.md` and `docs/HDRP.md` — the same reference-not-restate discipline `.bonit` uses for `nych`'s canonical `EpistemicStatus`. A `.tcta` file that embeds its own copy of Γ, Ψ, or Φ instead of pointing at the one canonical definition is non-conformant.

## The four consumption points

A `.tcta` file is read at exactly these points in a run:

1. **Domain prune** — restricts the active constraint set `C` using the run's domain classification, before any transform is evaluated.
2. **Competency prune** — further restricts `C` using a competency/fluency estimate, so a low-confidence vernacular match licenses a narrower transform set than a high-confidence one.
3. **Inverse transform** — applies a transform's domain-relative inverse where one is defined. TCTA does not assume a global inverse exists for every transform (`transform_algebra_axioms_v1.md` §1), so this step is conditional, never automatic, and a `.tcta` file must say explicitly when no inverse is defined rather than silently skipping it.
4. **Trajectory narrowing** — the core pipeline: `Ω(C) → τ_q → Γ → Ψ → 𝒯_G`, then HDRP's `Φ` for localized continuation inside the resolved family.

## Generative role: proposing `.g8son` gate candidates toward a goal

The four points above describe `.tcta` as a filter. It is also meant to be generative: given a current state representation and a **stated or inferred desired state representation** (`GOAL.DESIRED_SR` below), trajectory narrowing isn't just pruning an existing candidate list — it's computing which trajectories in `Ω(C)` could actually connect current state to that goal, then resolving them to the family `𝒯_G` via `Γ`/`Ψ`.

The transforms that survive in `𝒯_G` are the material an LLM drafts into `.g8son` gate conditions and PASS/FAIL predicates. `.tcta` proposes what's admissible toward the goal; `.g8son` is still where that proposal gets fixed into a bounded, auditable 1–3-gate file. `.tcta` never writes a `.g8son` file itself — it narrows the space a reasoning step reads from when it does.

When `GOAL.DESIRED_SR` is `null` (no stated or inferred goal yet), trajectory narrowing falls back to the pure filter behavior above: `Ω(C) → 𝒯_G` with no target, just the constraint-bounded admissible space.

## Forcing compliance: the engine isn't optional

A `.tcta` file is not a suggestion the reasoning step may substitute its own math for. `COMPLIANCE` below is a `REJECT IF` block, the same mechanism `.bonit` files use (`TOTElibrary.bonit`'s `VALIDATION`), checked against the step's actual output:

- `REJECT IF ALGORITHM_SUBSTITUTED` — the reasoning step used a different narrowing/selection method than the one `ENGINE` names, with or without disclosing it.
- `REJECT IF GOAL_PURSUED_WITHOUT_OMEGA_C` — a trajectory toward `GOAL.DESIRED_SR` was proposed without first computing (or disclosing `UNKNOWN` for) the admissible space `Ω(C)`.
- `REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION` — see below: no algorithm may be selected until `SPREAD` is computed for this step.

This makes `.tcta` closer to `.g8son`'s PASS/FAIL discipline than to a reference doc: a reasoning step's output is checked against these rules the same way a gate's output is checked against its conditions, not merely encouraged to comply.

## Dynamic algorithm selection by spread

`SPREAD` is not a new quantity — it's the inverse of the search-reduction factor `R` already defined in `transform_algebra_axioms_v1.md` §11:

\[
\text{SPREAD} = \frac{1}{R} = \frac{\mathcal{S}(\mathcal{T}_G)}{\mathcal{S}(\Omega(\mathcal{C}))}
\]

Low `SPREAD` means the resolved trajectory family is tight relative to the admissible space — the narrowing did real work, and localized continuation (HDRP's `Φ`) is licensed. High `SPREAD` means narrowing barely reduced anything — the family isn't actually resolved, and picking one trajectory to hand to HDRP would be a guess dressed up as a calculation.

`ALGORITHM_SELECT` routes on `SPREAD` against two thresholds you set per domain in `PARAMETERS`:

- `SPREAD <= SPREAD_LOW` → `HDRP_LOCALIZED` (use `Φ`; the family is tight enough to trust).
- `SPREAD >= SPREAD_HIGH` → `UNRESOLVED` (fail closed, same discipline as `.ork`'s `ON_BOUND_EXCEEDED`; do not let HDRP pick inside a family that isn't actually resolved).
- Between the two thresholds: not yet defined by this spec. Don't invent a third algorithm to fill the gap — disclose `UNRESOLVED` until a real middle-band behavior is designed and added here with its own reasoning, the same way `H1`/`H2` stay hypotheses until tested rather than assumed true to make the gap go away.

`H2`'s collision bound `ε` is a second, independent check on the same question: even a low-`SPREAD` family is not trustworthy if `ε` says it could collide with a sibling family. `ALGORITHM_SELECT` must treat a high `ε` the same as a high `SPREAD` — route to `UNRESOLVED`, not `HDRP_LOCALIZED`, regardless of how tight `𝒯_G` looks in isolation.

## Reference representation (v1)

```
TCTA/1.0
NAME <run-or-unit-id>
APPLIES_TO "<.mg8 unit or .ork path>"

GOAL {
  DESIRED_SR "<stated or inferred target state representation, or null>"
  SOURCE "<stated|inferred|null>"   # stated: the actor declared it; inferred: a reasoning step proposed it and it is MODEL, not OBS/INTENT (see nych's EpistemicStatus) until confirmed
}

ENGINE {
  GAMMA_REF "TCTA/spec/transform_algebra_axioms_v1.md#6-invariant-projection"
  PSI_REF   "TCTA/spec/transform_algebra_axioms_v1.md#9-ogsi--orthogonal-gestalt-symmetry-identification"
  PHI_REF   "TCTA/docs/HDRP.md#forward-projection"
}

PARAMETERS {
  ETA <float|null>        # η, HDRP gate update rate
  LAMBDA_REC <float|null> # λ_rec, HDRP recovery coefficient
  ALPHA <float|null>      # α, HDRP momentum coefficient
  EPSILON <float|null>    # ε, OGSI accepted signature-collision bound
  PREFIX_K <int|null>     # k, resolved critical prefix length, if found this run
  SPREAD_LOW <float|null>   # threshold at/below which ALGORITHM_SELECT picks HDRP_LOCALIZED
  SPREAD_HIGH <float|null>  # threshold at/above which ALGORITHM_SELECT picks UNRESOLVED
}

CONSUMPTION_POINTS {
  DOMAIN_PRUNE        SOURCE "<module or step supplying the domain classification>" STATUS "<implemented|not_yet_wired>"
  COMPETENCY_PRUNE     SOURCE "<module or step supplying the competency estimate>"   STATUS "<implemented|not_yet_wired>"
  INVERSE_TRANSFORM    DEFINED <true|false>                                          STATUS "<implemented|not_yet_wired>"
  TRAJECTORY_NARROWING SOURCE "ENGINE"                                               STATUS "<implemented|not_yet_wired>"
}

SPREAD {
  VALUE <float|null>   # S(T_G) / S(Omega(C)) for this step; null until computed
  EPSILON_CHECK <float|null>   # current H2 collision bound; a high value overrides a low SPREAD
}

ALGORITHM_SELECT {
  RESULT "<HDRP_LOCALIZED|UNRESOLVED|null>"   # null until SPREAD.VALUE is computed -- never pre-set
  REASON "<spread_low|spread_high|epsilon_high|not_yet_computed>"
}

COMPLIANCE {
  REJECT IF ALGORITHM_SUBSTITUTED
  REJECT IF GOAL_PURSUED_WITHOUT_OMEGA_C
  REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION
}
```

Field notes:

- `GOAL.DESIRED_SR` is what makes trajectory narrowing generative rather than a pure filter — see "Generative role" above. `SOURCE` follows the same stated/inferred discipline as `nych`'s `EpistemicStatus`: an inferred goal is `MODEL`, never `INTENT`, until something explicitly licenses it as the actual target.
- `PARAMETERS` are the only place actual numbers live, and they're explicitly **operating parameters for this run/unit**, not the algebra — the algebra itself (`Γ`, `Ψ`, `Φ`'s functional form) is never written here, only referenced via `ENGINE`. `null` means not yet empirically resolved for this run, same convention `.ork` uses for `WRITTEN_AT`.
- `CONSUMPTION_POINTS.*.STATUS` must be disclosed honestly, same bar as the rest of this file family. As of this writing, **none of the four are wired into working code** — `nych`'s `domain.py` (domain expansion/classification) and `competency.py` (vernacular-based competency scoring) are real, running modules that could feed `DOMAIN_PRUNE`/`COMPETENCY_PRUNE`, but nothing currently connects their output to a `.tcta` file's `PARAMETERS` or to `Ω(C)`. This file format exists to make that wiring possible and auditable when it happens, not to claim it already has.
- `INVERSE_TRANSFORM.DEFINED` must be `false` rather than omitted when a transform has no domain-relative inverse — per the axioms, absence of an inverse is a normal, expected case, not an error.

## Relationship to the rest of the file family

```text
.mg8pk
  ↓
system.ork
  ↓
.mg8 unit
  ↓
flow.ork
  ├── .gst   state/context
  ├── .tcta  trajectory-constraint algebra (prunes/narrows before or alongside gate evaluation)
  ├── .g8son bounded gates
  └── .qson  trace destination
```

`.tcta` sits beside `.g8son`, not above or inside it: a gate still evaluates PASS/FAIL/INTERMEDIATE against `.gst` state exactly as `g8son`'s own spec defines. What `.tcta` changes is the *candidate set* a gate chain is even allowed to consider — narrowed from the full potential future space down to `Ω(C)`, then (when `H1`/`H2` hold for the active trajectory family) down further to `𝒯_G`.

## Status boundary

This is a new file type, not yet implemented in `mg8-engine` or anywhere else. Treat the `ENGINE`/`PARAMETERS`/`CONSUMPTION_POINTS` shape above as a reference profile, open to revision once real wiring is attempted — the same posture `.ork` took before anyone had tried to run a real `.ork` instance end to end.

## Change log

- v1 — initial reference profile. Establishes `.tcta` as the carrier for TCTA's Γ/Ψ and HDRP's Φ, referenced from `nhartman000/TCTA` rather than restated, consumed at exactly four points (domain prune, competency prune, inverse transform, trajectory narrowing), with explicit `not_yet_wired` disclosure since no code currently connects them.
- v1.1 — added `GOAL.DESIRED_SR`: trajectory narrowing is generative, not just a filter. Given a stated or inferred desired state representation, `.tcta` computes which admissible trajectories could reach it; the surviving `𝒯_G` transforms are the candidate material an LLM drafts into `.g8son` gates. `GOAL.SOURCE` follows the same stated/inferred discipline as `nych`'s `EpistemicStatus` (an inferred goal is `MODEL`, never `INTENT`, until confirmed).
- v1.2 — `.tcta` now forces compliance instead of describing math the reasoning step could substitute: added `COMPLIANCE` (`REJECT IF` rules, same mechanism as `.bonit`'s `VALIDATION`) and `ALGORITHM_SELECT`, which dynamically routes to `HDRP_LOCALIZED` or fail-closed `UNRESOLVED` based on `SPREAD` — the inverse of the search-reduction factor `R` already defined in `transform_algebra_axioms_v1.md` §11, not a new metric. A high `ε` (H2 collision bound) overrides a low `SPREAD` and also routes to `UNRESOLVED`. The band between the two thresholds is explicitly undefined rather than papered over with an invented third algorithm.
