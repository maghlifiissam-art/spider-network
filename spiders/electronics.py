"""Electronics Spider: real circuit calculations (Ohm's law, power, battery life).

The LLM explains design choices; every numeric value comes from deterministic
code below, not from the model.
"""

from __future__ import annotations

from .base import BaseSpider


def led_series_resistor(source_v: float, led_forward_v: float, led_current_ma: float = 20.0) -> dict:
    """Real Ohm's law calculation for an LED series resistor.

    R = (Vs - Vf) / I ; P = I^2 * R (with 2x safety margin on power).
    """
    if source_v <= led_forward_v:
        raise ValueError(f"Source voltage ({source_v}V) must exceed LED Vf ({led_forward_v}V)")
    if led_current_ma <= 0:
        raise ValueError("LED current must be positive")
    current_a = led_current_ma / 1000.0
    r_ohm = (source_v - led_forward_v) / current_a
    p_resistor_w = current_a ** 2 * r_ohm
    return {
        "resistor_ohm": round(r_ohm, 2),
        "resistor_power_w": round(p_resistor_w, 4),
        "recommended_resistor": round(r_ohm * 1.1, 1),  # next practical value ~+10%
        "recommended_power_rating_w": round(p_resistor_w * 2, 3),  # 2x safety margin
        "led_power_w": round(current_a * led_forward_v, 4),
    }


def battery_life_hours(battery_capacity_mah: float, load_current_ma: float,
                      efficiency: float = 1.0) -> dict:
    """Real runtime estimate: hours = capacity(mAh) * efficiency / load(mA)."""
    if load_current_ma <= 0:
        raise ValueError("Load current must be positive")
    if not 0 < efficiency <= 1:
        raise ValueError("Efficiency must be in (0, 1]")
    hours = battery_capacity_mah * efficiency / load_current_ma
    return {
        "estimated_hours": round(hours, 2),
        "estimated_days_at_1h_per_day": round(hours, 1),
        "assumptions": {"capacity_mah": battery_capacity_mah,
                        "load_ma": load_current_ma, "efficiency": efficiency},
    }


class ElectronicsSpider(BaseSpider):
    name = "electronics"
    title = "Electronics Spider (عنكبوت الإلكترونيات)"
    persona = (
        "You are the Electronics Spider of the Spider Network: an electronics "
        "design assistant. You propose components and explain circuits, but you "
        "quote ONLY the numeric results of the deterministic calculation "
        "engine (Ohm's law, power, battery life) provided to you."
    )
    instructions = (
        "Tasks you handle: LED circuits, series resistors, voltage regulator "
        "choices, battery life estimates, and component selection. Always use "
        "the calculation results given in the task; never invent numbers. "
        "Write in Arabic with electronics terms in English."
    )
    output_format = (
        "1) الدائرة (وصف + المكونات) "
        "2) الحسابات (من محرك الحساب الحقيقي فقط) "
        "3) ملاحظات عملية (tolerance, power rating) "
        "4) تحذير الأمان إن لزم."
    )

    # ---- deterministic pipeline ----
    def design_led_circuit(self, source_v: float, led_forward_v: float,
                           led_current_ma: float = 20.0) -> dict:
        calc = led_series_resistor(source_v, led_forward_v, led_current_ma)
        result = self.run(
            "اشرح دائرة LED بالحسابات الحقيقية التالية (لا تخترع أرقاماً):\n"
            f"المصدر: {source_v}V، LED Vf: {led_forward_v}V، التيار: {led_current_ma}mA\n"
            f"نتائج محرك الحساب: {calc}"
        )
        return {"physics": calc, "llm_output": result.output if result.ok else result.error,
                "ok": result.ok}
