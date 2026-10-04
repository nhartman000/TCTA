"""Tests for tcta_engine.compliance: the three REJECT IF checks.

Uses stdlib unittest (no pytest / no package-install network access)."""

import unittest

from tcta_engine.compliance import (
    AlgorithmSubstituted,
    GoalPursuedWithoutOmegaC,
    SpreadNotComputedBeforeSelection,
    check_algorithm_not_substituted,
    check_compliance,
    check_goal_requires_omega_c,
    check_spread_before_selection,
)


class TestCheckAlgorithmNotSubstituted(unittest.TestCase):
    def test_passes_when_used_matches_declared(self):
        check_algorithm_not_substituted("HDRP#phi", "HDRP#phi")  # no raise

    def test_raises_on_mismatch(self):
        with self.assertRaises(AlgorithmSubstituted):
            check_algorithm_not_substituted("HDRP#phi", "some_other_method")

    def test_raises_when_used_is_none(self):
        with self.assertRaises(AlgorithmSubstituted):
            check_algorithm_not_substituted("HDRP#phi", None)


class TestCheckGoalRequiresOmegaC(unittest.TestCase):
    def test_no_goal_means_check_does_not_apply(self):
        check_goal_requires_omega_c(desired_sr=None, omega_c_computed=False)  # no raise

    def test_goal_with_omega_c_computed_passes(self):
        check_goal_requires_omega_c(desired_sr="target", omega_c_computed=True)  # no raise

    def test_goal_without_omega_c_and_without_disclosure_raises(self):
        with self.assertRaises(GoalPursuedWithoutOmegaC):
            check_goal_requires_omega_c(desired_sr="target", omega_c_computed=False)

    def test_goal_without_omega_c_but_disclosed_unknown_passes(self):
        check_goal_requires_omega_c(
            desired_sr="target", omega_c_computed=False, omega_c_disclosed_unknown=True
        )  # no raise


class TestCheckSpreadBeforeSelection(unittest.TestCase):
    def test_no_selection_result_means_check_does_not_apply(self):
        check_spread_before_selection(spread_value=None, algorithm_select_result=None)  # no raise

    def test_selection_with_spread_computed_passes(self):
        check_spread_before_selection(spread_value=0.3, algorithm_select_result="HDRP_LOCALIZED")

    def test_selection_without_spread_raises(self):
        with self.assertRaises(SpreadNotComputedBeforeSelection):
            check_spread_before_selection(spread_value=None, algorithm_select_result="UNRESOLVED")


class TestCheckCompliance(unittest.TestCase):
    def _base_kwargs(self, **overrides):
        kwargs = dict(
            declared_method_ref="HDRP#phi",
            used_method_ref="HDRP#phi",
            desired_sr="target",
            omega_c_computed=True,
            spread_value=0.3,
            algorithm_select_result="HDRP_LOCALIZED",
        )
        kwargs.update(overrides)
        return kwargs

    def test_all_checks_pass_raises_nothing(self):
        check_compliance(**self._base_kwargs())

    def test_algorithm_substitution_is_checked_first(self):
        with self.assertRaises(AlgorithmSubstituted):
            check_compliance(
                **self._base_kwargs(
                    used_method_ref="other",
                    omega_c_computed=False,  # would also fail goal check
                    spread_value=None,  # would also fail spread check
                )
            )

    def test_goal_without_omega_c_raises_when_algorithm_matches(self):
        with self.assertRaises(GoalPursuedWithoutOmegaC):
            check_compliance(**self._base_kwargs(omega_c_computed=False))

    def test_spread_not_computed_raises_when_earlier_checks_pass(self):
        with self.assertRaises(SpreadNotComputedBeforeSelection):
            check_compliance(**self._base_kwargs(spread_value=None))


if __name__ == "__main__":
    unittest.main()
