"""Tests for tcta_engine.hdrp against docs/HDRP.md's equations exactly:
O_t = tanh(R_0 + g_t*alpha*T_t), E_t = ||O_t - I_{t+1}||_2,
delta_g_t = -eta*delta_E_t*sign(T_t . O_t), g_{t+1} = Pi_[0,1](g_t*lambda_rec + delta_g_t).

Uses stdlib unittest (no pytest / no package-install network access)."""

import math
import unittest

from tcta_engine.hdrp import HDRP, HDRPState, _clip_unit, _dot, _l2, _sub


def _assert_list_almost_equal(test, actual, expected, places=6):
    test.assertEqual(len(actual), len(expected))
    for a, e in zip(actual, expected):
        test.assertAlmostEqual(a, e, places=places)


class TestHelpers(unittest.TestCase):
    def test_sub_elementwise(self):
        self.assertEqual(_sub([3.0, 5.0], [1.0, 2.0]), [2.0, 3.0])

    def test_dot_product(self):
        self.assertAlmostEqual(_dot([1.0, 2.0], [3.0, 4.0]), 11.0)

    def test_l2_distance(self):
        self.assertAlmostEqual(_l2([0.0, 0.0], [3.0, 4.0]), 5.0)

    def test_clip_unit_clamps_both_sides(self):
        self.assertEqual(_clip_unit(-0.5), 0.0)
        self.assertEqual(_clip_unit(1.5), 1.0)
        self.assertAlmostEqual(_clip_unit(0.3), 0.3)


class TestHDRPStateTrajectoryDelta(unittest.TestCase):
    def test_trajectory_delta_is_r0_minus_r_prev(self):
        state = HDRPState(r0=[1.0, 2.0], r_prev=[0.5, 0.5])
        _assert_list_almost_equal(self, state.trajectory_delta(), [0.5, 1.5])


class TestForwardProjection(unittest.TestCase):
    def test_matches_tanh_equation_by_hand(self):
        state = HDRPState(r0=[0.0, 0.0], r_prev=[-1.0, 1.0], gate=0.5)
        hdrp = HDRP(state=state, alpha=1.0, eta=0.1, lambda_rec=0.9)
        # T = R0 - R_prev = [1.0, -1.0]; O = tanh(R0 + g*alpha*T) = tanh(0.5*[1,-1])
        expected = [math.tanh(0.5), math.tanh(-0.5)]
        _assert_list_almost_equal(self, hdrp.forward_projection(), expected)

    def test_zero_gate_means_projection_equals_tanh_of_r0(self):
        state = HDRPState(r0=[0.2, -0.3], r_prev=[1.0, 1.0], gate=0.0)
        hdrp = HDRP(state=state, alpha=1.0, eta=0.1, lambda_rec=0.9)
        expected = [math.tanh(0.2), math.tanh(-0.3)]
        _assert_list_almost_equal(self, hdrp.forward_projection(), expected)


class TestStep(unittest.TestCase):
    def test_step_returns_full_disclosed_record(self):
        state = HDRPState(r0=[0.0, 0.0], r_prev=[-1.0, 1.0], gate=0.5)
        hdrp = HDRP(state=state, alpha=1.0, eta=0.1, lambda_rec=0.9)
        record = hdrp.step(observed_next=[0.1, -0.1])
        for key in (
            "trajectory_delta",
            "forward_projection",
            "tracking_error",
            "error_delta",
            "gate_delta",
            "gate_before",
            "gate_after",
            "sign_T_dot_O",
        ):
            self.assertIn(key, record)

    def test_step_does_not_roll_registers(self):
        state = HDRPState(r0=[0.0, 0.0], r_prev=[-1.0, 1.0], gate=0.5)
        hdrp = HDRP(state=state, alpha=1.0, eta=0.1, lambda_rec=0.9)
        hdrp.step(observed_next=[0.1, -0.1])
        self.assertEqual(hdrp.state.r0, [0.0, 0.0])
        self.assertEqual(hdrp.state.r_prev, [-1.0, 1.0])

    def test_step_updates_gate_and_last_error_in_place(self):
        state = HDRPState(r0=[0.0, 0.0], r_prev=[-1.0, 1.0], gate=0.5)
        hdrp = HDRP(state=state, alpha=1.0, eta=0.1, lambda_rec=0.9)
        gate_before = hdrp.state.gate
        record = hdrp.step(observed_next=[0.1, -0.1])
        self.assertAlmostEqual(hdrp.state.gate, record["gate_after"])
        self.assertAlmostEqual(record["gate_before"], gate_before)
        self.assertAlmostEqual(hdrp._last_error, record["tracking_error"])

    def test_step_by_hand_matches_documented_equations(self):
        # R0=[1.0], R_prev=[0.0], g=1.0, alpha=1.0, eta=0.5, lambda_rec=1.0
        state = HDRPState(r0=[1.0], r_prev=[0.0], gate=1.0)
        hdrp = HDRP(state=state, alpha=1.0, eta=0.5, lambda_rec=1.0)
        # T = [1.0]; O = tanh(1.0 + 1.0*1.0*1.0) = tanh(2.0)
        O_expected = math.tanh(2.0)
        I_next = [0.0]
        E_expected = abs(O_expected - 0.0)
        delta_E_expected = E_expected  # last_error starts at 0.0
        sign_expected = 1.0  # sign(1.0 * O_expected), O_expected > 0
        delta_g_expected = -0.5 * delta_E_expected * sign_expected
        g_next_expected = _clip_unit(1.0 * 1.0 + delta_g_expected)

        record = hdrp.step(observed_next=I_next)
        _assert_list_almost_equal(self, record["forward_projection"], [O_expected])
        self.assertAlmostEqual(record["tracking_error"], E_expected)
        self.assertAlmostEqual(record["error_delta"], delta_E_expected)
        self.assertAlmostEqual(record["sign_T_dot_O"], sign_expected)
        self.assertAlmostEqual(record["gate_delta"], delta_g_expected)
        self.assertAlmostEqual(record["gate_after"], g_next_expected)

    def test_sign_is_zero_when_trajectory_dot_projection_is_zero(self):
        # T=[0.0] forces T.O == 0 regardless of O.
        state = HDRPState(r0=[0.3], r_prev=[0.3], gate=0.5)
        hdrp = HDRP(state=state, alpha=1.0, eta=0.1, lambda_rec=0.9)
        record = hdrp.step(observed_next=[0.3])
        self.assertEqual(record["sign_T_dot_O"], 0.0)

    def test_gate_never_leaves_unit_interval_across_many_steps(self):
        state = HDRPState(r0=[2.0], r_prev=[-2.0], gate=0.5)
        hdrp = HDRP(state=state, alpha=5.0, eta=10.0, lambda_rec=1.0)
        for i in range(20):
            record = hdrp.step(observed_next=[(-1.0) ** i * 5.0])
            self.assertGreaterEqual(record["gate_after"], 0.0)
            self.assertLessEqual(record["gate_after"], 1.0)


class TestAdvance(unittest.TestCase):
    def test_advance_rolls_registers(self):
        state = HDRPState(r0=[1.0, 2.0], r_prev=[0.0, 0.0], gate=0.5)
        hdrp = HDRP(state=state, alpha=1.0, eta=0.1, lambda_rec=0.9)
        hdrp.advance(new_r0=[3.0, 4.0])
        self.assertEqual(hdrp.state.r_prev, [1.0, 2.0])
        self.assertEqual(hdrp.state.r0, [3.0, 4.0])

    def test_advance_does_not_touch_gate(self):
        state = HDRPState(r0=[1.0], r_prev=[0.0], gate=0.7)
        hdrp = HDRP(state=state, alpha=1.0, eta=0.1, lambda_rec=0.9)
        hdrp.advance(new_r0=[2.0])
        self.assertAlmostEqual(hdrp.state.gate, 0.7)


if __name__ == "__main__":
    unittest.main()
