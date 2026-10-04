"""Tests for tcta_engine.core: StateRepresentation/Transform/Trajectory,
Omega(C), search_reduction_factor/compute_spread, select_algorithm.

Uses stdlib unittest (no pytest / no package-install network access)."""

import unittest

from tcta_engine.core import (
    StateRepresentation,
    Transform,
    admissible_trajectory_space,
    compute_spread,
    is_admissible_trajectory,
    search_reduction_factor,
    select_algorithm,
    ALGORITHM_RESULTS,
    REASON_MIDDLE_BAND_UNDEFINED,
    SpreadNotComputedBeforeSelection,
)


def _always_valid(result_state, constraints) -> bool:
    return True


def _nonneg(result_state, constraints) -> bool:
    return result_state >= 0


class TestTransformAndTrajectory(unittest.TestCase):
    def test_result_state_applies_function(self):
        sr = StateRepresentation(s=5, domain=None, constraints=None)
        t = Transform("add1", apply=lambda s: s + 1)
        self.assertEqual(t.result_state(sr), 6)

    def test_is_admissible_true_when_constraint_check_passes(self):
        sr = StateRepresentation(s=5, domain=None, constraints=None)
        t = Transform("add1", apply=lambda s: s + 1)
        self.assertTrue(t.is_admissible(sr, _always_valid))

    def test_is_admissible_false_when_constraint_check_fails(self):
        sr = StateRepresentation(s=5, domain=None, constraints=None)
        t = Transform("neg", apply=lambda s: -s)
        self.assertFalse(t.is_admissible(sr, _nonneg))

    def test_trajectory_threads_state_through_each_transform(self):
        sr0 = StateRepresentation(s=0, domain=None, constraints=None)
        traj = [Transform("add1", lambda s: s + 1), Transform("add1", lambda s: s + 1)]
        self.assertTrue(is_admissible_trajectory(traj, sr0, _nonneg))

    def test_trajectory_fails_as_soon_as_one_step_is_inadmissible(self):
        sr0 = StateRepresentation(s=0, domain=None, constraints=None)
        traj = [Transform("sub5", lambda s: s - 5), Transform("add1", lambda s: s + 1)]
        self.assertFalse(is_admissible_trajectory(traj, sr0, _nonneg))


class TestAdmissibleTrajectorySpace(unittest.TestCase):
    def test_filters_to_only_admissible_trajectories(self):
        sr0 = StateRepresentation(s=0, domain=None, constraints=None)
        good = [Transform("add1", lambda s: s + 1)]
        bad = [Transform("sub1", lambda s: s - 1)]
        space = admissible_trajectory_space([good, bad], sr0, _nonneg)
        self.assertEqual(space, [good])

    def test_empty_candidates_yields_empty_space(self):
        sr0 = StateRepresentation(s=0, domain=None, constraints=None)
        self.assertEqual(admissible_trajectory_space([], sr0, _nonneg), [])


class TestSearchReductionAndSpread(unittest.TestCase):
    def test_search_reduction_factor_is_ratio(self):
        self.assertEqual(search_reduction_factor(s_omega_c=100.0, s_tg=25.0), 4.0)

    def test_search_reduction_factor_rejects_nonpositive_s_tg(self):
        with self.assertRaises(ValueError):
            search_reduction_factor(s_omega_c=100.0, s_tg=0.0)

    def test_search_reduction_factor_rejects_s_tg_exceeding_s_omega_c(self):
        with self.assertRaises(ValueError):
            search_reduction_factor(s_omega_c=10.0, s_tg=20.0)

    def test_compute_spread_is_inverse_of_search_reduction_factor(self):
        s_omega_c, s_tg = 100.0, 25.0
        r = search_reduction_factor(s_omega_c, s_tg)
        spread = compute_spread(s_tg, s_omega_c)
        self.assertAlmostEqual(spread, 1.0 / r)
        self.assertAlmostEqual(spread, 0.25)

    def test_compute_spread_rejects_nonpositive_s_omega_c(self):
        with self.assertRaises(ValueError):
            compute_spread(s_tg=1.0, s_omega_c=0.0)

    def test_compute_spread_rejects_s_tg_exceeding_s_omega_c(self):
        with self.assertRaises(ValueError):
            compute_spread(s_tg=20.0, s_omega_c=10.0)


class TestSelectAlgorithm(unittest.TestCase):
    def test_raises_when_spread_not_computed(self):
        with self.assertRaises(SpreadNotComputedBeforeSelection):
            select_algorithm(None, spread_low=0.2, spread_high=0.8)

    def test_low_spread_selects_hdrp_localized(self):
        result, reason = select_algorithm(0.1, spread_low=0.2, spread_high=0.8)
        self.assertEqual(result, "HDRP_LOCALIZED")
        self.assertEqual(reason, "spread_low")
        self.assertIn(result, ALGORITHM_RESULTS)

    def test_spread_exactly_at_low_threshold_selects_hdrp_localized(self):
        result, reason = select_algorithm(0.2, spread_low=0.2, spread_high=0.8)
        self.assertEqual(result, "HDRP_LOCALIZED")
        self.assertEqual(reason, "spread_low")

    def test_high_spread_selects_unresolved_spread_high(self):
        result, reason = select_algorithm(0.9, spread_low=0.2, spread_high=0.8)
        self.assertEqual(result, "UNRESOLVED")
        self.assertEqual(reason, "spread_high")

    def test_spread_exactly_at_high_threshold_selects_unresolved_spread_high(self):
        result, reason = select_algorithm(0.8, spread_low=0.2, spread_high=0.8)
        self.assertEqual(result, "UNRESOLVED")
        self.assertEqual(reason, "spread_high")

    def test_middle_band_selects_unresolved_with_documented_reason(self):
        result, reason = select_algorithm(0.5, spread_low=0.2, spread_high=0.8)
        self.assertEqual(result, "UNRESOLVED")
        self.assertEqual(reason, REASON_MIDDLE_BAND_UNDEFINED)

    def test_high_epsilon_overrides_low_spread(self):
        result, reason = select_algorithm(
            0.1, spread_low=0.2, spread_high=0.8, epsilon=0.5, epsilon_max=0.3
        )
        self.assertEqual(result, "UNRESOLVED")
        self.assertEqual(reason, "epsilon_high")

    def test_epsilon_below_max_does_not_override(self):
        result, reason = select_algorithm(
            0.1, spread_low=0.2, spread_high=0.8, epsilon=0.1, epsilon_max=0.3
        )
        self.assertEqual(result, "HDRP_LOCALIZED")
        self.assertEqual(reason, "spread_low")


if __name__ == "__main__":
    unittest.main()
