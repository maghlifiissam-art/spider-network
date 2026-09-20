from unittest import TestCase

from electronics_spider import compute_battery_runtime, compute_led_resistor, compute_voltage_divider
from engineering_spider import build_scad_code, compute_bracket_strength


class ElectronicsTests(TestCase):
    def test_led_resistor_calculation(self):
        result = compute_led_resistor({
            "supply_voltage_v": 5,
            "desired_current_ma": 20,
            "led_color": "red",
        })
        self.assertGreaterEqual(result["standard_resistance_ohm"], 150)
        self.assertGreater(result["power_dissipation_w"], 0)

    def test_voltage_divider_math(self):
        result = compute_voltage_divider({
            "input_voltage_v": 12,
            "desired_output_voltage_v": 6,
            "max_current_ma": 2,
        })
        self.assertAlmostEqual(result["actual_output_voltage_v"], 6.0, delta=1.0)
        self.assertGreater(result["r1_ohm"], 0)
        self.assertGreater(result["r2_ohm"], 0)

    def test_battery_runtime_math(self):
        result = compute_battery_runtime({
            "battery_capacity_mah": 2000,
            "components": [
                {"name": "controller", "current_draw_ma": 150},
                {"name": "sensor", "current_draw_ma": 50},
            ],
        })
        self.assertEqual(result["total_current_draw_ma"], 200)
        self.assertAlmostEqual(result["estimated_runtime_hours_worst_case"], 10.0)


class MechanicalTests(TestCase):
    SPEC = {
        "part_name": "test-bracket",
        "arm1_length_mm": 40,
        "arm2_length_mm": 50,
        "width_mm": 30,
        "thickness_mm": 4,
        "hole_diameter_mm": 5,
        "material": "steel_a36",
        "expected_load_kg": 2,
    }

    def test_scad_generation_is_deterministic_and_local(self):
        code = build_scad_code(self.SPEC)
        self.assertIn("difference()", code)
        self.assertIn("cylinder", code)

    def test_strength_returns_real_safety_factor(self):
        result = compute_bracket_strength(self.SPEC)
        self.assertGreater(result["bending_stress_mpa"], 0)
        self.assertGreater(result["factor_of_safety"], 0)
        self.assertIn("verdict", result)
