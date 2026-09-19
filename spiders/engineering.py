"""Engineering Spider: real deterministic engineering calculations + CAD drafts.

The LLM proposes concepts; ALL numbers are verified by real deterministic code
(beam bending theory, section properties). Designs are drafts, NOT for real
manufacturing without a licensed engineer's review.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from .base import BaseSpider

# Real material properties (approximate, for draft calculations)
MATERIALS = {
    "PLA": {"yield_MPa": 60, "elastic_modulus_GPa": 3.5, "density_kg_m3": 1240},
    "ABS": {"yield_MPa": 40, "elastic_modulus_GPa": 2.3, "density_kg_m3": 1050},
    "aluminum_6061": {"yield_MPa": 240, "elastic_modulus_GPa": 68.9, "density_kg_m3": 2700},
    "steel_1018": {"yield_MPa": 370, "elastic_modulus_GPa": 200, "density_kg_m3": 7870},
}


def compute_bracket_strength(length_mm: float, width_mm: float, thickness_mm: float,
                             load_n: float, material: str = "PLA") -> dict:
    """Cantilever bracket check using real beam bending theory.

    sigma = M * c / I with M = F * L (max at the wall), I = w*t^3/12, c = t/2.
    Also checks deflection delta = F*L^3 / (3*E*I).
    """
    mat = MATERIALS.get(material)
    if not mat:
        raise ValueError(f"Unknown material '{material}'. Choose from {list(MATERIALS)}")
    for name, value, lo in [("length_mm", length_mm, 1), ("width_mm", width_mm, 1),
                            ("thickness_mm", thickness_mm, 0.1), ("load_n", load_n, 0)]:
        if value < lo:
            raise ValueError(f"{name} must be >= {lo}")

    L = length_mm / 1000.0
    w = width_mm / 1000.0
    t = thickness_mm / 1000.0

    moment_Nm = load_n * L                    # fixed-end cantilever moment
    inertia_m4 = w * t ** 3 / 12.0            # second moment of area
    c = t / 2.0
    stress_Pa = moment_Nm * c / inertia_m4
    stress_MPa = stress_Pa / 1e6
    yield_MPa = mat["yield_MPa"]
    safety_factor = yield_MPa / stress_MPa if stress_MPa > 0 else float("inf")

    E = mat["elastic_modulus_GPa"] * 1e9
    deflection_m = load_n * L ** 3 / (3 * E * inertia_m4)
    deflection_mm = deflection_m * 1000

    return {
        "material": material,
        "max_stress_MPa": round(stress_MPa, 2),
        "yield_strength_MPa": yield_MPa,
        "safety_factor": round(safety_factor, 2),
        "safe": safety_factor >= 2.0,          # minimum design SF = 2
        "tip_deflection_mm": round(deflection_mm, 3),
        "verdict": (
            "SAFE (draft): SF >= 2.0" if safety_factor >= 2.0
            else "NOT SAFE (draft): increase thickness/width or reduce load"
        ),
    }


def generate_openscad_bracket(length_mm: float, width_mm: float, thickness_mm: float,
                              hole_diameter_mm: float = 5.0, out_path: str = "bracket.scad") -> str:
    """Generate a real OpenSCAD model of an L-bracket (draft geometry)."""
    hole_d = min(hole_diameter_mm, width_mm * 0.4)
    scad = f"""// Spider Network - Engineering Spider (DRAFT, not for manufacturing without licensed review)
$fn = 64;
length = {length_mm};
width   = {width_mm};
thick   = {thickness_mm};
hole_d  = {hole_d:.2f};

module l_bracket() {{
    union() {{
        // vertical wall
        cube([thick, width, length]);
        // horizontal base
        translate([0, 0, 0])
            cube([length, width, thick]);
    }}
}}

module with_holes() {{
    difference() {{
        l_bracket();
        // hole in vertical wall (top)
        translate([thick / 2, width / 2, length * 0.8])
            rotate([0, 90, 0])
                cylinder(h = thick + 2, d = hole_d, center = true);
        // hole in horizontal base
        translate([length * 0.8, width / 2, thick / 2])
            cylinder(h = thick + 2, d = hole_d, center = true);
    }}
}}

with_holes();
"""
    Path(out_path).write_text(scad, encoding="utf-8")
    return out_path


class EngineeringSpider(BaseSpider):
    name = "engineering"
    title = "Engineering Spider (عنكبوت الهندسة والحسابات)"
    persona = (
        "You are the Engineering Spider of the Spider Network: a mechanical "
        "design assistant. You propose concepts, dimensions and materials, but "
        "you ALWAYS state that real numbers must come from the deterministic "
        "calculation engine, and that designs are drafts requiring a licensed "
        "engineer's review before any manufacturing."
    )
    instructions = (
        "Tasks you handle: describing engineering parts (brackets, frames, "
        "enclosures), proposing dimensions/materials as JSON, and explaining "
        "results of the real physics calculations you are given. Never invent "
        "stress or safety numbers yourself; quote only the calculation output. "
        "Write in Arabic with engineering terms in English."
    )
    output_format = (
        "1) وصف القطعة "
        "2) JSON بالأبعاد المقترحة: "
        '{"length_mm": 60, "width_mm": 30, "thickness_mm": 5, '
        '"hole_diameter_mm": 5, "material": "PLA"} '
        "3) شرح نتائج الحساب الحقيقي (إن وُجدت) "
        "4) تحذير: التصميم draft يحتاج مراجعة مهندس مرخص."
    )

    # ---- deterministic design pipeline (LLM proposes, physics verifies) ----
    def design_bracket(self, description: str, workdir: str = ".") -> dict:
        """Full pipeline: LLM proposes dimensions -> real physics check -> OpenSCAD file."""
        result = self.run(
            "قترح أبعاد L-bracket لهذا الوصف وأرجع فقط JSON بالحقول المطلوبة:\n"
            f"{description}\n"
            'أرجع JSON فقط: {"length_mm": .., "width_mm": .., "thickness_mm": .., '
            '"hole_diameter_mm": .., "material": "PLA|ABS|aluminum_6061|steel_1018"}'
        )
        params = {}
        if result.ok:
            match = re.search(r"\{.*\}", result.output, re.S)
            if match:
                try:
                    params = json.loads(match.group(0))
                except json.JSONDecodeError:
                    params = {}
        if not params:
            # conservative fallback draft
            params = {"length_mm": 60, "width_mm": 30, "thickness_mm": 5,
                      "hole_diameter_mm": 5, "material": "PLA"}

        calc = compute_bracket_strength(
            length_mm=float(params["length_mm"]),
            width_mm=float(params["width_mm"]),
            thickness_mm=float(params["thickness_mm"]),
            load_n=50.0,  # default draft load; caller can override below
            material=str(params.get("material", "PLA")),
        )
        scad_path = generate_openscad_bracket(
            length_mm=float(params["length_mm"]),
            width_mm=float(params["width_mm"]),
            thickness_mm=float(params["thickness_mm"]),
            hole_diameter_mm=float(params.get("hole_diameter_mm", 5.0)),
            out_path=str(Path(workdir) / "bracket.scad"),
        )
        return {"proposed": params, "physics": calc, "scad_file": scad_path,
                "llm_output": result.output if result.ok else result.error,
                "note": "DRAFT - requires licensed engineer review before manufacturing."}
