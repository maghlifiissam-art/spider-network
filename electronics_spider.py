"""
electronics_spider.py — أول خطوة فوكيل الإلكترونيات: دارة LED بسيطة
------------------------------------------------------------------
نفس مبدأ engineering_spider.py: الـ LLM كيقترح المعطيات، الحساب كيدير
بقانون أوم الحقيقي (V = I × R)، ماشي تخمين.

⚠️ هذا حساب نظري مبسط لدارة LED بمقاومة واحدة على التوالي. الدارات
الحقيقية (بالخصوص عالية القدرة/التيار) خاصها مراجعة مهندس إلكترونيك
قبل التصنيع، بالخصوص للسلامة الكهربائية.
"""

import json
from groq import Groq

MODEL = "llama-3.1-8b-instant"

# قيم مقاومات معيارية حقيقية (سلسلة E12) — باش نقترحو قيمة موجودة فالسوق
STANDARD_RESISTORS_OHM = [
    10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82,
    100, 120, 150, 180, 220, 270, 330, 390, 470, 560, 680, 820,
    1000, 1200, 1500, 1800, 2200, 2700, 3300, 3900, 4700, 5600, 6800, 8200,
    10000, 12000, 15000, 18000, 22000, 27000, 33000,
]

# جهد التشغيل الأمامي النموذجي لأنواع LED شائعة (فولت)
LED_FORWARD_VOLTAGE = {
    "red": 2.0, "green": 2.1, "yellow": 2.1, "blue": 3.2, "white": 3.2, "infrared": 1.5,
}


def generate_led_circuit_spec(client: Groq, description: str) -> dict:
    system_prompt = f"""You are an electronics assistant. Read the user's description of a \
simple LED circuit request (LED color, power supply, desired brightness/current) and extract \
the parameters.

Known typical LED forward voltages (V): {json.dumps(LED_FORWARD_VOLTAGE)}

Respond ONLY with valid JSON, no markdown fences:
{{
  "circuit_name": "...",
  "supply_voltage_v": <float, e.g. 5, 9, 12>,
  "led_color": one of [{", ".join(LED_FORWARD_VOLTAGE.keys())}],
  "desired_current_ma": <float, typical 10-20mA for a standard LED>,
  "battery_capacity_mah": <float or null if not mentioned>,
  "notes": "one short sentence"
}}"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": description}],
            temperature=0.2,
            max_tokens=400,
        )
        return json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError:
        return {"error": "فشل النموذج فإرجاع مواصفات صالحة (JSON)."}
    except Exception as e:
        return {"error": str(e)}


def _nearest_standard_resistor(value_ohm: float) -> float:
    return min(STANDARD_RESISTORS_OHM, key=lambda r: abs(r - value_ohm))


def compute_led_resistor(spec: dict) -> dict:
    """
    قانون أوم: R = (V_supply − V_forward) / I
    كنختارو أقرب مقاومة معيارية موجودة فالسوق (E12)، ومن بعد كنحسبو
    التيار والقدرة الفعليين بهاد المقاومة (ماشي المطلوب بالضبط، لأن
    المقاومة المعيارية نادراً كتكون بالضبط الرقم المحسوب).
    """
    vf = LED_FORWARD_VOLTAGE.get(spec.get("led_color", "red"), 2.0)
    vs = spec["supply_voltage_v"]
    i_desired_a = spec["desired_current_ma"] / 1000

    if vs <= vf:
        return {"error": f"جهد التغذية ({vs}V) أصغر أو يساوي جهد الـ LED ({vf}V) — الدارة ماغاديش تخدم."}

    r_ideal = (vs - vf) / i_desired_a
    r_standard = _nearest_standard_resistor(r_ideal)

    i_actual_a = (vs - vf) / r_standard
    i_actual_ma = i_actual_a * 1000
    power_w = i_actual_a ** 2 * r_standard

    # القدرة المقترحة للمقاومة (نضاعفو ×2 كهامش أمان حراري، ممارسة قياسية)
    recommended_wattage = 0.125 if power_w < 0.0625 else (0.25 if power_w < 0.125 else 0.5)

    result = {
        "led_forward_voltage_v": vf,
        "ideal_resistance_ohm": round(r_ideal, 1),
        "standard_resistance_ohm": r_standard,
        "actual_current_ma": round(i_actual_ma, 2),
        "power_dissipation_w": round(power_w, 3),
        "recommended_resistor_wattage_w": recommended_wattage,
    }

    if spec.get("battery_capacity_mah"):
        hours = spec["battery_capacity_mah"] / i_actual_ma if i_actual_ma > 0 else float("inf")
        result["estimated_battery_life_hours"] = round(hours, 1)

    return result


def design_led_circuit(client: Groq, description: str) -> dict:
    spec = generate_led_circuit_spec(client, description)
    if "error" in spec:
        return {"success": False, "error": spec["error"]}

    calc = compute_led_resistor(spec)
    if "error" in calc:
        return {"success": False, "error": calc["error"], "spec": spec}

    return {
        "success": True,
        "spec": spec,
        "calculation": calc,
        "disclaimer": "⚠️ حساب نظري مبسط لدارة LED واحدة. الدارات الحقيقية (بالخصوص متعددة LEDs أو عالية التيار) خاصها مراجعة مهندس إلكترونيك.",
    }


# ---------------------------------------------------------------------------
# دارة ثانية: مقسم الجهد (Voltage Divider) — أساسي فتوصيل حساسات/منظمي جهد
# ---------------------------------------------------------------------------
def generate_divider_spec(client: Groq, description: str) -> dict:
    system_prompt = """You are an electronics assistant. Read the user's description of a \
voltage divider need (input voltage, desired output voltage) and extract the parameters.

Respond ONLY with valid JSON, no markdown fences:
{
  "circuit_name": "...",
  "input_voltage_v": <float>,
  "desired_output_voltage_v": <float, must be less than input>,
  "max_current_ma": <float, typical 1-10mA for a signal divider>,
  "notes": "one short sentence"
}"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": description}],
            temperature=0.2,
            max_tokens=300,
        )
        return json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError:
        return {"error": "فشل النموذج فإرجاع مواصفات صالحة (JSON)."}
    except Exception as e:
        return {"error": str(e)}


def compute_voltage_divider(spec: dict) -> dict:
    """
    صيغة مقسم الجهد الحقيقية: Vout = Vin × R2 / (R1 + R2)
    كنختارو R1 من قيم معيارية، ومن بعد كنحسبو R2 المطلوبة رياضياً،
    ونقربوها لأقرب قيمة معيارية، ونعاودو نحسبو Vout الفعلي (كيبقى فرق
    صغير عن المطلوب — هذا طبيعي وواقعي، ماشي خطأ فالحساب).
    """
    vin = spec["input_voltage_v"]
    vout_desired = spec["desired_output_voltage_v"]
    max_i_a = spec["max_current_ma"] / 1000

    if vout_desired >= vin:
        return {"error": f"الجهد المطلوب ({vout_desired}V) يجب يكون أصغر من جهد الدخل ({vin}V)."}

    # نختارو R1 باش التيار الكلي مايتجاوزش max_current_ma عند Vin كامل
    r_total_min = vin / max_i_a
    r1_ideal = r_total_min * (1 - vout_desired / vin)
    r1_standard = _nearest_standard_resistor(r1_ideal)

    r2_ideal = r1_standard * vout_desired / (vin - vout_desired)
    r2_standard = _nearest_standard_resistor(r2_ideal)

    vout_actual = vin * r2_standard / (r1_standard + r2_standard)
    total_current_ma = (vin / (r1_standard + r2_standard)) * 1000
    error_percent = abs(vout_actual - vout_desired) / vout_desired * 100

    return {
        "r1_ohm": r1_standard,
        "r2_ohm": r2_standard,
        "actual_output_voltage_v": round(vout_actual, 3),
        "error_percent": round(error_percent, 1),
        "total_current_ma": round(total_current_ma, 3),
    }


def design_voltage_divider(client: Groq, description: str) -> dict:
    spec = generate_divider_spec(client, description)
    if "error" in spec:
        return {"success": False, "error": spec["error"]}

    calc = compute_voltage_divider(spec)
    if "error" in calc:
        return {"success": False, "error": calc["error"], "spec": spec}

    return {
        "success": True,
        "spec": spec,
        "calculation": calc,
        "disclaimer": "⚠️ مقسم الجهد البسيط مناسب لإشارات منخفضة التيار (حساسات، قراءة جهد) — ماشي لتغذية دارات عالية الاستهلاك. لتغذية حقيقية استعمل منظم جهد (voltage regulator) حقيقي.",
    }


# ---------------------------------------------------------------------------
# حاسبة ثالثة: عمر البطارية لجهاز بعدة مكونات (بدل LED وحدو)
# ---------------------------------------------------------------------------
def generate_battery_spec(client: Groq, description: str) -> dict:
    system_prompt = """You are an electronics assistant. Read the user's description of a \
battery-powered device and extract the battery capacity and the current draw of each \
component in the device.

Respond ONLY with valid JSON, no markdown fences:
{
  "device_name": "...",
  "battery_capacity_mah": <float>,
  "components": [
    {"name": "...", "current_draw_ma": <float>}
  ],
  "notes": "one short sentence"
}"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": description}],
            temperature=0.3,
            max_tokens=500,
        )
        return json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError:
        return {"error": "فشل النموذج فإرجاع مواصفات صالحة (JSON)."}
    except Exception as e:
        return {"error": str(e)}


def compute_battery_runtime(spec: dict) -> dict:
    """
    صيغة حقيقية بسيطة: العمر (ساعات) = سعة البطارية (mAh) ÷ مجموع التيار
    المستهلك من كل المكونات (mA). هذا تقدير "أسوأ حالة" (كل المكونات
    خدامين فنفس الوقت بشكل مستمر) — الاستهلاك الحقيقي غالباً أقل بفضل
    أوضاع السكون (sleep modes).
    """
    total_current_ma = sum(c["current_draw_ma"] for c in spec.get("components", []))
    if total_current_ma <= 0:
        return {"error": "مجموع استهلاك التيار صفر — ماكاينش حساب ممكن."}

    runtime_hours = spec["battery_capacity_mah"] / total_current_ma

    return {
        "total_current_draw_ma": round(total_current_ma, 2),
        "estimated_runtime_hours_worst_case": round(runtime_hours, 1),
        "estimated_runtime_days_worst_case": round(runtime_hours / 24, 1),
        "note": "هذا تقدير 'أسوأ حالة' (استهلاك مستمر بلا وضع سكون) — العمر الحقيقي غالباً أطول.",
    }


def design_battery_runtime(client: Groq, description: str) -> dict:
    spec = generate_battery_spec(client, description)
    if "error" in spec:
        return {"success": False, "error": spec["error"]}

    calc = compute_battery_runtime(spec)
    if "error" in calc:
        return {"success": False, "error": calc["error"], "spec": spec}

    return {
        "success": True,
        "spec": spec,
        "calculation": calc,
        "disclaimer": "⚠️ تقدير نظري مبسط (استهلاك ثابت). التصميم الحقيقي لإدارة الطاقة يتطلب قياسات فعلية ومراجعة مهندس.",
    }


# ---------------------------------------------------------------------------
# نقطة دخول ذكية موحدة: كتفهم أي نوع دارة المستخدم كيقصد
# ---------------------------------------------------------------------------
def classify_circuit_type(client: Groq, description: str) -> str:
    system_prompt = """Classify the described electronics request into exactly one category:
"led" (sizing a resistor for an LED circuit)
"voltage_divider" (stepping down a voltage using two resistors)
"battery_runtime" (estimating how long a battery will last given components' current draw)
Respond with ONLY the single word: led, voltage_divider, or battery_runtime"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": description}],
            temperature=0,
            max_tokens=10,
        )
        answer = response.choices[0].message.content.strip().lower()
        if "divider" in answer:
            return "voltage_divider"
        if "battery" in answer or "runtime" in answer:
            return "battery_runtime"
        return "led"
    except Exception:
        return "led"


def design_circuit(client: Groq, description: str) -> dict:
    """نقطة الدخول الموحدة — هي اللي خاصها تنستعمل من boss_spider.py."""
    circuit_type = classify_circuit_type(client, description)
    if circuit_type == "voltage_divider":
        result = design_voltage_divider(client, description)
    elif circuit_type == "battery_runtime":
        result = design_battery_runtime(client, description)
    else:
        result = design_led_circuit(client, description)
    result["circuit_type"] = circuit_type
    return result
