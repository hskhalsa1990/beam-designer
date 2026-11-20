"""Indian / metric steel beam section catalog + stress checks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import numpy as np

@dataclass
class SteelSection:
    name: str
    h: float          # overall depth mm
    b: float          # flange width mm
    tw: float         # web thickness mm
    tf: float         # flange thickness mm
    Ixx: float        # cm^4
    Zxx: float        # cm^3  (elastic section modulus)
    A: float          # cm^2
    weight: float     # kg/m
    rxx: float = 0.0  # cm

    @property
    def I_m4(self) -> float:
        return self.Ixx * 1e-8   # cm^4 -> m^4

    @property
    def Z_m3(self) -> float:
        return self.Zxx * 1e-6   # cm^3 -> m^3

    @property
    def A_m2(self) -> float:
        return self.A * 1e-4

# Representative ISMB / UB-style catalog (approximate published values)
SECTIONS: Dict[str, SteelSection] = {
    "ISMB 150": SteelSection("ISMB 150", 150, 80, 4.8, 7.6, 636, 84.8, 15.0, 14.9, 6.51),
    "ISMB 175": SteelSection("ISMB 175", 175, 90, 5.1, 8.1, 980, 112.0, 18.1, 19.3, 7.36),
    "ISMB 200": SteelSection("ISMB 200", 200, 100, 5.4, 7.8, 2235, 223.5, 22.4, 25.4, 9.99),  # approx
    "ISMB 250": SteelSection("ISMB 250", 250, 125, 6.1, 8.2, 5131, 410.5, 32.9, 37.3, 12.5),
    "ISMB 300": SteelSection("ISMB 300", 300, 140, 7.6, 10.6, 8603, 573.6, 46.8, 44.2, 13.6),
    "ISMB 350": SteelSection("ISMB 350", 350, 140, 8.1, 11.4, 12540, 716.6, 55.0, 52.4, 15.1),
    "ISMB 400": SteelSection("ISMB 400", 400, 140, 8.6, 12.7, 19306, 965.3, 61.6, 57.6, 17.7),
    "ISMB 450": SteelSection("ISMB 450", 450, 150, 9.1, 13.7, 27536, 1223.8, 70.0, 72.4, 19.8),
    "ISMB 500": SteelSection("ISMB 500", 500, 180, 10.9, 14.7, 38579, 1543.2, 89.0, 86.9, 20.8),
    "UB 203x133x25": SteelSection("UB 203x133x25", 203.2, 133.2, 5.7, 7.8, 2340, 230.0, 32.0, 25.1, 8.56),
    "UB 254x146x31": SteelSection("UB 254x146x31", 251.4, 146.1, 6.0, 8.6, 4000, 318.0, 40.0, 31.1, 10.0),
    "UB 305x165x40": SteelSection("UB 305x165x40", 303.4, 165.0, 6.0, 10.2, 8500, 560.0, 51.3, 40.3, 12.9),
}

STEEL_GRADES = {
    "Fe 250 (E250)": {"fy": 250, "fu": 410, "E": 2.0e5},   # MPa, MPa, MPa
    "Fe 410 (E410)": {"fy": 250, "fu": 410, "E": 2.0e5},
    "Fe 450 (E450)": {"fy": 300, "fu": 450, "E": 2.0e5},
    "S275": {"fy": 275, "fu": 430, "E": 2.1e5},
    "S355": {"fy": 355, "fu": 510, "E": 2.1e5},
}

def list_section_names() -> List[str]:
    return list(SECTIONS.keys())

def get_section(name: str) -> SteelSection:
    return SECTIONS[name]

def stress_check(M_max_Nm: float, V_max_N: float, section: SteelSection,
                 grade: str = "Fe 250 (E250)", gamma_m0: float = 1.10) -> dict:
    """
    Simple working-stress / limit-style checks.
    sigma = M / Z,  tau_avg = V / (d * tw) approx.
    """
    g = STEEL_GRADES[grade]
    fy = g["fy"]  # MPa
    E = g["E"] * 1e6  # Pa if needed later

    Z = section.Z_m3
    sigma = abs(M_max_Nm) / Z / 1e6 if Z > 0 else 0.0  # MPa
    # web area approx h * tw (mm -> m)
    Aw = (section.h * section.tw) * 1e-6  # m^2
    tau = abs(V_max_N) / Aw / 1e6 if Aw > 0 else 0.0

    # allowable (simplified IS800-style partial)
    sigma_all = fy / gamma_m0
    tau_all = (fy / np.sqrt(3)) / gamma_m0

    util_b = sigma / sigma_all if sigma_all else 0
    util_s = tau / tau_all if tau_all else 0

    return {
        "sigma_MPa": sigma,
        "tau_MPa": tau,
        "sigma_all_MPa": sigma_all,
        "tau_all_MPa": tau_all,
        "util_bending": util_b,
        "util_shear": util_s,
        "safe_bending": util_b <= 1.0,
        "safe_shear": util_s <= 1.0,
        "safe": util_b <= 1.0 and util_s <= 1.0,
        "fy": fy,
        "section": section.name,
        "grade": grade,
    }

def compare_sections(M_max_Nm: float, V_max_N: float, grade: str = "Fe 250 (E250)") -> list:
    """Return list of dicts sorted by weight among safe sections, else all."""
    rows = []
    for name, sec in SECTIONS.items():
        chk = stress_check(M_max_Nm, V_max_N, sec, grade)
        rows.append({
            "section": name,
            "weight_kg_m": sec.weight,
            "Zxx_cm3": sec.Zxx,
            "sigma_MPa": round(chk["sigma_MPa"], 2),
            "tau_MPa": round(chk["tau_MPa"], 2),
            "util_b": round(chk["util_bending"], 3),
            "util_s": round(chk["util_shear"], 3),
            "safe": chk["safe"],
        })
    rows.sort(key=lambda r: (not r["safe"], r["weight_kg_m"]))
    return rows

def recommend_section(M_max_Nm: float, V_max_N: float, grade: str = "Fe 250 (E250)",
                      prefer_lightest: bool = True) -> dict:
    """Return lightest safe section, or strongest if none safe."""
    rows = compare_sections(M_max_Nm, V_max_N, grade)
    safe = [r for r in rows if r["safe"]]
    if safe:
        best = min(safe, key=lambda r: r["weight_kg_m"]) if prefer_lightest else safe[0]
        return {"status": "safe", "recommended": best["section"], **best}
    # none safe — pick lowest util
    best = min(rows, key=lambda r: r["util_b"])
    return {"status": "none_safe", "recommended": best["section"], **best}
