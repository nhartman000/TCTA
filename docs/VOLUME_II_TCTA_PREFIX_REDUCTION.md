# TCTA — Formal Volume II: Prefix Resolution and Conditional Reduction

**Author:** Nicholas Hartman / American Milestone Inc.  
**Status:** H1 is a hypothesis; H2 is an assumption or empirical requirement; the reduction statements are conditional. This volume imports Volume I definitions only.

## 5. Prefix Trace

For a complete trajectory \(\tau\), an incomplete prefix is:

\[
\tau_q=\tau_{1:k},\qquad k<n
\]

TCTA asks whether a proper prefix can carry enough invariant structure to resolve the family of the complete trajectory before execution terminates.

## 6. Invariant Projection

Let:

\[
\Gamma(\tau)
\]

be an invariant-signature projection over a trajectory or trajectory prefix.

The exact implementation of \(\Gamma\) is domain-dependent. The formal framework requires only that its output be suitable for evaluating prefix stability and family separability.

## 7. Hypothesis H1 — Prefix Stability of Invariants

For a trajectory family \(\mathcal{T}_G\), TCTA tests whether there exists a proper prefix length \(k<n\) such that:

\[
\Gamma(\tau_{1:k})=\Gamma(\tau)
\]

for trajectories in the evaluated family under the specified operating conditions.

This is a **hypothesis**, not a universal theorem. Its validity must be tested per domain, family definition, invariant operator, noise regime, and significance criterion.

## 8. Assumption H2 — Family Separability / Discriminability

For distinct trajectory families \(\mathcal{T}_i\) and \(\mathcal{T}_j\), the framework assumes or empirically tests a bounded signature-collision probability:

\[
\Pr\left[\Gamma(\mathcal{T}_i)=\Gamma(\mathcal{T}_j)\right]<\epsilon
\]

where \(\epsilon\in[0,1)\) is the accepted structural collision / cross-contamination bound under the evaluated conditions.

This is an explicit error term. When \(\epsilon>0\), family resolution and pruning are bounded-risk operations rather than absolute guarantees.

## 9. OGSI — Orthogonal Gestalt Symmetry Identification

OGSI is the TCTA family-resolution operator:

\[
\Psi
\]

With invariant extraction made explicit:

\[
\tau_q\xrightarrow{\Gamma}G\xrightarrow{\Psi}\mathcal{T}_G
\]

where:

- \(G\) is the resolved invariant/signature representation,
- \(\Psi\) is Orthogonal Gestalt Symmetry Identification,
- \(\mathcal{T}_G\) is the resolved trajectory family.

The resolved family defines the transform subset admissible for family-consistent continuation.

## 10. Transform-Space Truncation

Before family resolution, continuation is evaluated within the admissible space \(\Omega(\mathcal{C})\).

After family resolution, the active continuation domain can be restricted to \(\mathcal{T}_G\) or to the transform set associated with that family.

Conceptually:

```text
potential future space
        ↓
constraints C
        ↓
Ω(C)
        ↓
prefix τq
        ↓
Γ invariant signature
        ↓
Ψ OGSI
        ↓
trajectory family T_G
        ↓
remove incompatible transforms
        ↓
remaining admissible continuation space
```

This operation is subtractive: incompatible transforms are removed from consideration rather than requiring exhaustive generation of every impossible future.

## 11. Search Reduction Factor

Let \(\mathcal{S}(X)\) denote the selected search/effort measure over an active trajectory domain \(X\).

Define:

\[
R=
\frac{\mathcal{S}(\Omega(\mathcal{C}))}
{\mathcal{S}(\mathcal{T}_G)}
\]

A material computational benefit requires:

\[
\mathcal{S}(\mathcal{T}_G)<\mathcal{S}(\Omega(\mathcal{C}))
\]

and a strong reduction corresponds to \(R\gg1\).

The relationship between search-space measure and actual computational cost must be stated for each implementation; reduced probability or geometric measure alone does not automatically imply reduced runtime.

## 14. HDRP Relationship

The Hartman Dual-Register Predictor (HDRP) is downstream of trajectory-family resolution. TCTA/OGSI constrains the allowable continuation space; HDRP performs localized short-horizon predictive continuation within that reduced space.

The architecture is:

\[
\tau_q\xrightarrow{\Gamma}G\xrightarrow{\Psi}\mathcal{T}_G\xrightarrow{\Phi}\text{localized continuation}
\]

where \(\Phi\) denotes the HDRP predictive layer.

## 15. Formal Status

The current core intentionally distinguishes:

- **definitions**: SR, transform, trajectory, prefix trace, CIIU, search-reduction factor;
- **hypothesis**: H1 prefix stability;
- **assumption / empirical requirement**: H2 family separability;
- **conditional results**: early family classification and search reduction when H1/H2 and the relevant cost assumptions hold;
- **empirical quantities**: critical prefix length \(k\), collision bound \(\epsilon\), OGSI accuracy, reduction factor \(R\), false-negative pruning rate, and ground-truth retention.

No universal proof of H1, H2, zero-error pruning, or universal computational reduction is asserted by this specification.

## Existing conditional arguments and evaluation

The source volume's Chapter 4 contains three conditional arguments and Chapter 5 gives the evaluation quantities. They are retained below with their original wording and dependencies; these are not unconditional proofs of prefix stability, family separability or runtime improvement.

## Chapter 4 — Hardened Formal Specifications and Proof Core

### 4.1 Hypothesis H1 — Prefix Stability of Invariants

Let \(\tau=[T_1,\dots,T_n]\) be a complete execution trace and \(\tau_{1:k}\) its prefix. H1 states that, under the relevant family/domain conditions, there exists a proper prefix \(k<n\) such that:

\[
\exists k<n\;\text{s.t.}\;\Gamma(\tau_{1:k})=\Gamma(\tau)
\]

This remains a **hypothesis** to be established empirically or formally for the relevant trajectory classes.

### 4.2 Assumption H2 — Family Separability / Discriminability

For distinct non-overlapping trajectory families:

\[
\mathcal{T}_i\cap\mathcal{T}_j=\emptyset
\]

and their projected invariant signatures satisfy:

\[
\Pr[\Gamma(\mathcal{T}_i)=\Gamma(\mathcal{T}_j)]<\epsilon
\]

where \(\epsilon\in[0,1)\) is the maximum allowed cross-family collision/cross-contamination bound.

### 4.3 Theorem 1 — Measure-Theoretic Space Reduction

**Conditional assertion.** If a constraint geometry \(\mathcal{C}\) excludes a positive-measure region of the global trajectory space, and the chosen search-effort functional \(\mathcal{S}\) is monotone with respect to the relevant active-space measure, then restriction to \(\Omega(\mathcal{C})\) reduces expected search effort.

Let:

\[
\Omega(\mathcal{C})\subset\Omega_{\text{global}}
\]

and:

\[
\Omega_{\text{excluded}}=\Omega_{\text{global}}\setminus\Omega(\mathcal{C})
\]

If:

\[
P(\Omega_{\text{excluded}})>0
\]

then:

\[
P(\Omega(\mathcal{C}))<P(\Omega_{\text{global}})
\]

Under the explicit monotonicity condition on \(\mathcal{S}\):

\[
\mathcal{S}(\Omega(\mathcal{C}))<\mathcal{S}(\Omega_{\text{global}})
\]

The search-cost monotonicity condition is part of the theorem's dependency; it does not follow from probability axioms alone.

### 4.4 Theorem 2 — Partial Trace Family Classification

Given H1 and H2, if:

\[
\Gamma(\tau_q)=\Gamma(\tau)
\]

and:

\[
\operatorname{Class}(\cdot)=f(\Gamma(\cdot))
\]

then:

\[
\operatorname{Class}(\tau_q)=\operatorname{Class}(\tau)=\mathcal{T}_G
\]

with family-collision/error probability bounded by \(\epsilon\) under H2.

The resulting pruning operation is therefore **bounded-risk**, not zero-risk when \(\epsilon>0\). Correctness retention must be measured empirically against known admissible continuations.

### 4.5 Theorem 3 — Search Complexity Reduction Bound

Let:

\[
\mathcal{T}_G\subset\Omega(\mathcal{C})
\]

and assume the structural concentration condition:

\[
\mathcal{S}(\mathcal{T}_G)\ll\mathcal{S}(\Omega(\mathcal{C}))
\]

After prefix classification:

\[
\tau_q\xrightarrow{\Gamma}G\xrightarrow{\Psi}\mathcal{T}_G
\]

continuation search can operate over \(\mathcal{T}_G\) rather than the entire constrained space.

Define the **Search Reduction Factor**:

\[
R=\frac{\mathcal{S}(\Omega(\mathcal{C}))}{\mathcal{S}(\mathcal{T}_G)}
\]

Under the stated concentration condition, \(R\gg1\). This conclusion is conditional on the family having materially lower search effort than the parent constrained space.

## Chapter 5 — Quantitative Evaluation and Benchmarking Framework

The evaluation harness is:

\[
\left(k,\epsilon,\Psi_{\text{acc}},R,\text{false-negative pruning rate}\right)
\]

### Critical Prefix Length \(k\)

Minimum trace prefix required to achieve stable family resolution under the selected significance criterion. The target criterion supplied for rigorous evaluation is:

\[
p<0.001
\]

This must not be reported as achieved unless supported by actual experiment data.

### Separability Bound \(\epsilon\)

The verified collision/cross-contamination bound between distinct trajectory-family invariant signatures.

### OGSI Classification Accuracy \(\Psi_{\text{acc}}\)

Empirical accuracy of the OGSI operator in mapping invariant signatures to the correct trajectory family across defined test conditions.

### Search Reduction Factor \(R\)

\[
R=\frac{\mathcal{S}(\Omega(\mathcal{C}))}{\mathcal{S}(\mathcal{T}_G)}
\]

### False-Negative Pruning Rate

The fraction/count of valid ground-truth admissible trajectories incorrectly discarded during space truncation.

### Ground-Truth Retention

The evaluation must explicitly report whether the known valid continuation remains in the reduced admissible family after pruning.


## Open specification work

For a blinded test, the exact Γ projection, Ψ decision rule, signature metric, training-only thresholds, nuisance transformations and acceptance rule must be frozen separately. An abstract operator name is not an executable classification algorithm.

**Source:** historical `docs/VOLUME_1_TECHNICAL_AND_MANAGEMENT.md`, preserved in Git history and in the theory repository's `sources/` directory.
