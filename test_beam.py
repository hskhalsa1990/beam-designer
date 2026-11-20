import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from beam_solver import BeamModel, Support, PointLoad, UDL, analyse, serviceability
from steel_sections import get_section, stress_check, compare_sections, recommend_section

def test_simple_udl():
    L, w = 6.0, 5000.0
    sec = get_section("ISMB 300")
    m = BeamModel(L=L, E=2e11, I=sec.I_m4,
                  supports=[Support(0,"pinned"), Support(L,"roller")],
                  udls=[UDL(0, L, w)])
    r = analyse(m, 600)
    assert abs(r["M_max"] - w*L**2/8)/(w*L**2/8) < 0.03
    assert abs(r["V_max"] - w*L/2)/(w*L/2) < 0.03

def test_cantilever_tip():
    L, P = 4.0, 10000.0
    sec = get_section("ISMB 250")
    m = BeamModel(L=L, E=2e11, I=sec.I_m4,
                  supports=[Support(0,"fixed")],
                  point_loads=[PointLoad(L, P)])
    r = analyse(m, 400)
    assert abs(r["M_max"] - P*L)/(P*L) < 0.05
    assert abs(r["V_max"] - P)/P < 0.05

def test_serviceability():
    s = serviceability(10.0, 5.0, 250)
    assert s["allow_mm"] == 20.0
    assert s["ok"] is True
    assert serviceability(25.0, 5.0, 250)["ok"] is False

def test_recommend():
    rec = recommend_section(50e3, 20e3)
    assert "recommended" in rec

def test_overhang_runs():
    sec = get_section("ISMB 300")
    m = BeamModel(L=8.0, E=2e11, I=sec.I_m4,
                  supports=[Support(1.0,"pinned"), Support(6.5,"roller")],
                  udls=[UDL(0, 8, 4000)])
    r = analyse(m, 400)
    assert r["M_max"] > 0 and r["V_max"] > 0

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
