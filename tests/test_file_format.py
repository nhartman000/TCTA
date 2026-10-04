"""Tests for tcta_engine.file_format: parse_tcta/serialize_tcta.

Note on the spec's literal example: tcta_file_format_v1.md's "Reference
representation (v1)" code block uses placeholder tokens like `<float|null>`
and `<implemented|not_yet_wired>` as grammar documentation, not parseable
values -- they are not valid `.tcta` content as written (e.g. `<float|null>`
is not a number, a quoted string, `null`, `true`, or `false`). These tests
therefore parse a concrete, filled-in instance of that same grammar rather
than the placeholder-laden doc text itself.

Uses stdlib unittest (no pytest / no package-install network access)."""

import unittest

from tcta_engine.file_format import (
    TctaParseError,
    parse_tcta,
    serialize_tcta,
)

CONCRETE_TCTA = """\
TCTA/1.0
NAME unit-42
APPLIES_TO "mg8-engine/units/unit-42.mg8"

GOAL {
  DESIRED_SR "target-state-7"
  SOURCE "stated"
}

ENGINE {
  GAMMA_REF "TCTA/spec/transform_algebra_axioms_v1.md#6-invariant-projection"
  PSI_REF   "TCTA/spec/transform_algebra_axioms_v1.md#9-ogsi--orthogonal-gestalt-symmetry-identification"
  PHI_REF   "TCTA/docs/HDRP.md#forward-projection"
}

PARAMETERS {
  ETA 0.1
  LAMBDA_REC 0.9
  ALPHA 1.0
  EPSILON 0.05
  PREFIX_K 3
  SPREAD_LOW 0.2
  SPREAD_HIGH 0.8
}

CONSUMPTION_POINTS {
  DOMAIN_PRUNE SOURCE "nych.domain" STATUS "not_yet_wired"
  COMPETENCY_PRUNE SOURCE "nych.competency" STATUS "not_yet_wired"
  INVERSE_TRANSFORM DEFINED false STATUS "not_yet_wired"
  TRAJECTORY_NARROWING SOURCE "ENGINE" STATUS "not_yet_wired"
}

SPREAD {
  VALUE 0.15
  EPSILON_CHECK 0.02
}

ALGORITHM_SELECT {
  RESULT "HDRP_LOCALIZED"
  REASON "spread_low"
}

COMPLIANCE {
  REJECT IF ALGORITHM_SUBSTITUTED
  REJECT IF GOAL_PURSUED_WITHOUT_OMEGA_C
  REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION
}
"""


class TestParseTcta(unittest.TestCase):
    def test_parses_header(self):
        tcta = parse_tcta(CONCRETE_TCTA)
        self.assertEqual(tcta.name, "unit-42")
        self.assertEqual(tcta.applies_to, "mg8-engine/units/unit-42.mg8")

    def test_parses_goal(self):
        tcta = parse_tcta(CONCRETE_TCTA)
        self.assertEqual(tcta.goal.desired_sr, "target-state-7")
        self.assertEqual(tcta.goal.source, "stated")

    def test_parses_engine(self):
        tcta = parse_tcta(CONCRETE_TCTA)
        self.assertTrue(tcta.engine.gamma_ref.endswith("#6-invariant-projection"))
        self.assertTrue(tcta.engine.phi_ref.endswith("#forward-projection"))

    def test_parses_parameters_as_numbers(self):
        tcta = parse_tcta(CONCRETE_TCTA)
        self.assertAlmostEqual(tcta.parameters.eta, 0.1)
        self.assertAlmostEqual(tcta.parameters.lambda_rec, 0.9)
        self.assertEqual(tcta.parameters.prefix_k, 3)
        self.assertIsInstance(tcta.parameters.prefix_k, int)

    def test_parses_consumption_points(self):
        tcta = parse_tcta(CONCRETE_TCTA)
        cp = tcta.consumption_points
        self.assertEqual(cp.domain_prune.source, "nych.domain")
        self.assertEqual(cp.domain_prune.status, "not_yet_wired")
        self.assertIs(cp.inverse_transform.defined, False)

    def test_parses_spread_and_algorithm_select(self):
        tcta = parse_tcta(CONCRETE_TCTA)
        self.assertAlmostEqual(tcta.spread.value, 0.15)
        self.assertEqual(tcta.algorithm_select.result, "HDRP_LOCALIZED")
        self.assertEqual(tcta.algorithm_select.reason, "spread_low")

    def test_parses_compliance_rules_in_order(self):
        tcta = parse_tcta(CONCRETE_TCTA)
        self.assertEqual(
            tcta.compliance,
            [
                "ALGORITHM_SUBSTITUTED",
                "GOAL_PURSUED_WITHOUT_OMEGA_C",
                "SPREAD_NOT_COMPUTED_BEFORE_SELECTION",
            ],
        )

    def test_null_values_parse_as_none(self):
        text = CONCRETE_TCTA.replace('DESIRED_SR "target-state-7"', "DESIRED_SR null")
        tcta = parse_tcta(text)
        self.assertIsNone(tcta.goal.desired_sr)

    def test_comments_are_stripped(self):
        text = CONCRETE_TCTA.replace(
            "ETA 0.1", "ETA 0.1  # eta, HDRP gate update rate"
        )
        tcta = parse_tcta(text)
        self.assertAlmostEqual(tcta.parameters.eta, 0.1)

    def test_hash_inside_quotes_is_not_treated_as_comment(self):
        text = CONCRETE_TCTA.replace(
            'DESIRED_SR "target-state-7"', 'DESIRED_SR "target#7-state"'
        )
        tcta = parse_tcta(text)
        self.assertEqual(tcta.goal.desired_sr, "target#7-state")

    def test_missing_version_header_raises(self):
        text = CONCRETE_TCTA.replace("TCTA/1.0\n", "")
        with self.assertRaises(TctaParseError):
            parse_tcta(text)

    def test_missing_name_raises(self):
        text = CONCRETE_TCTA.replace("NAME unit-42\n", "")
        with self.assertRaises(TctaParseError):
            parse_tcta(text)

    def test_missing_applies_to_raises(self):
        text = CONCRETE_TCTA.replace(
            'APPLIES_TO "mg8-engine/units/unit-42.mg8"\n', ""
        )
        with self.assertRaises(TctaParseError):
            parse_tcta(text)

    def test_unknown_consumption_point_raises(self):
        text = CONCRETE_TCTA.replace(
            'DOMAIN_PRUNE SOURCE "nych.domain" STATUS "not_yet_wired"',
            'NOT_A_REAL_POINT SOURCE "x" STATUS "not_yet_wired"',
        )
        with self.assertRaises(TctaParseError):
            parse_tcta(text)

    def test_missing_optional_blocks_use_defaults(self):
        text = "\n".join(
            ["TCTA/1.0", "NAME minimal-unit", 'APPLIES_TO "x.mg8"', ""]
        )
        tcta = parse_tcta(text)
        self.assertIsNone(tcta.goal.desired_sr)
        self.assertIsNone(tcta.parameters.eta)
        self.assertEqual(tcta.compliance, [])


class TestSerializeTcta(unittest.TestCase):
    def test_round_trips_concrete_example(self):
        original = parse_tcta(CONCRETE_TCTA)
        round_tripped = parse_tcta(serialize_tcta(original))
        self.assertEqual(round_tripped, original)

    def test_round_trips_minimal_file(self):
        text = "\n".join(
            ["TCTA/1.0", "NAME minimal-unit", 'APPLIES_TO "x.mg8"', ""]
        )
        original = parse_tcta(text)
        round_tripped = parse_tcta(serialize_tcta(original))
        self.assertEqual(round_tripped, original)

    def test_round_trips_revise_if_compliance_rule(self):
        text = CONCRETE_TCTA.replace(
            "REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION",
            "REJECT IF SPREAD_NOT_COMPUTED_BEFORE_SELECTION\n  REVISE IF SOME_SOFT_RULE",
        )
        original = parse_tcta(text)
        self.assertEqual(original.compliance[-1], "REVISE:SOME_SOFT_RULE")
        round_tripped = parse_tcta(serialize_tcta(original))
        self.assertEqual(round_tripped, original)


if __name__ == "__main__":
    unittest.main()
