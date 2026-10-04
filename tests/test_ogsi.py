"""Tests for tcta_engine.ogsi: prefix_stability_holds (H1 test) and
collision_rate (H2 empirical estimate).

Uses stdlib unittest (no pytest / no package-install network access)."""

import unittest

from tcta_engine.ogsi import collision_rate, prefix_stability_holds


def _gamma_last_element(trajectory):
    """A trivial Gamma: the signature is just the final transform in the
    trajectory (a list of strings standing in for Transform objects)."""
    return trajectory[-1]


def _gamma_constant(trajectory):
    return "same-signature-always"


class TestPrefixStabilityHolds(unittest.TestCase):
    def test_true_when_prefix_and_full_trajectory_share_gamma_signature(self):
        trajectory = ["a", "b", "c"]
        self.assertTrue(prefix_stability_holds(_gamma_constant, trajectory, k=1))

    def test_false_when_prefix_gamma_differs_from_full_trajectory_gamma(self):
        trajectory = ["a", "b", "c"]
        self.assertFalse(prefix_stability_holds(_gamma_last_element, trajectory, k=1))

    def test_raises_when_k_is_zero(self):
        with self.assertRaises(ValueError):
            prefix_stability_holds(_gamma_constant, ["a", "b", "c"], k=0)

    def test_raises_when_k_equals_full_length(self):
        with self.assertRaises(ValueError):
            prefix_stability_holds(_gamma_constant, ["a", "b", "c"], k=3)

    def test_raises_when_k_exceeds_length(self):
        with self.assertRaises(ValueError):
            prefix_stability_holds(_gamma_constant, ["a", "b", "c"], k=5)


class TestCollisionRate(unittest.TestCase):
    def test_empty_family_a_returns_zero(self):
        self.assertEqual(collision_rate(_gamma_constant, [], [["a"]]), 0.0)

    def test_empty_family_b_returns_zero(self):
        self.assertEqual(collision_rate(_gamma_constant, [["a"]], []), 0.0)

    def test_all_collide_when_gamma_is_constant(self):
        family_a = [["a"], ["b"]]
        family_b = [["c"], ["d"]]
        self.assertAlmostEqual(collision_rate(_gamma_constant, family_a, family_b), 1.0)

    def test_no_collisions_when_signatures_never_match(self):
        family_a = [["x", "a"]]
        family_b = [["y", "b"]]
        self.assertAlmostEqual(
            collision_rate(_gamma_last_element, family_a, family_b), 0.0
        )

    def test_partial_collision_rate(self):
        # family_a signatures: "a", "b"; family_b signatures: "a", "c"
        family_a = [["z", "a"], ["z", "b"]]
        family_b = [["z", "a"], ["z", "c"]]
        # pairs: (a,a) collide, (a,c) no, (b,a) no, (b,c) no -> 1/4
        self.assertAlmostEqual(
            collision_rate(_gamma_last_element, family_a, family_b), 0.25
        )


if __name__ == "__main__":
    unittest.main()
