"""Beam Designer v2 — SFD/BMD, serviceability, auto section, parametric, 3D, CSV."""
from __future__ import annotations
import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from beam_solver import (
    BeamModel, Support, PointLoad, UDL, UVL, PointMoment, analyse, parametric_udl
)
from steel_sections import (
    list_section_names, get_section, STEEL_GRADES, stress_check,
    compare_sections, recommend_section
)

st.set_page_config(page_title="Beam Designer v2", layout="wide", page_icon="📐")
st.title("Beam Designer v2")
st.caption("SFD · BMD · Deflection · Serviceability · Steel safety · Auto-select · 3D · Parametric")

with st.sidebar:
    st.header("Geometry & steel")
    L = st.number_input("Span L (m)", 0.5, 40.0, 6.0, 0.5)
    support_cfg = st.selectbox("Supports", [
        "Simply supported (pin–roller)",
        "Cantilever (fixed left)",
        "Overhang (pin at 0.2L, roller at 0.85L)",
    ])
    grade = st.selectbox("Steel grade", list(STEEL_GRADES.keys()))
    sec_name = st.selectbox("Section (manual)", list_section_names(), index=4)
    sec = get_section(sec_name)
    E = STEEL_GRADES[grade]["E"] * 1e6
    I = sec.I_m4
    st.caption(f"I={sec.Ixx:.0f} cm⁴ · Z={sec.Zxx:.1f} cm³ · {sec.weight} kg/m")
    defl_limit = st.selectbox("Deflection limit", ["L/250", "L/300", "L/360", "L/500"], index=0)
    limit_ratio = float(defl_limit.split("/")[1])

    load_factor = st.number_input("Load factor (ULS)", 1.0, 2.0, 1.5, 0.05)
    st.header("Loads (↓ positive)  — service values; factored for strength")
    n_pt = st.number_input("Point loads", 0, 6, 1)
    point_loads = []
    for i in range(int(n_pt)):
        a, b = st.columns(2)
        px = a.number_input(f"P{i+1} x (m)", 0.0, L, min(L * 0.5, L), 0.1, key=f"px{i}")
        pv = b.number_input(f"P{i+1} (kN)", 0.0, 500.0, 20.0, 1.0, key=f"pv{i}")
        point_loads.append(PointLoad(px, pv * 1e3))

    udls = []
    if st.checkbox("UDL", True):
        c1, c2, c3 = st.columns(3)
        x1 = c1.number_input("x1", 0.0, L, 0.0, 0.1, key="ux1")
        x2 = c2.number_input("x2", 0.0, L, L, 0.1, key="ux2")
        w = c3.number_input("w kN/m", 0.0, 100.0, 5.0, 0.5, key="uw")
        if x2 > x1:
            udls.append(UDL(x1, x2, w * 1e3))

    uvls = []
    if st.checkbox("UVL / trapezoid"):
        c1, c2 = st.columns(2)
        vx1 = c1.number_input("UVL x1", 0.0, L, 0.0, key="vx1")
        vx2 = c2.number_input("UVL x2", 0.0, L, L, key="vx2")
        w1 = st.number_input("w1 kN/m", 0.0, 100.0, 0.0, key="w1")
        w2 = st.number_input("w2 kN/m", 0.0, 100.0, 8.0, key="w2")
        if vx2 > vx1:
            uvls.append(UVL(vx1, vx2, w1 * 1e3, w2 * 1e3))

    moments = []
    if st.checkbox("Point moment"):
        mx = st.number_input("M at x (m)", 0.0, L, L / 2)
        mv = st.number_input("M (kN·m)", -500.0, 500.0, 10.0)
        moments.append(PointMoment(mx, mv * 1e3))

    auto_sec = st.checkbox("Auto-pick lightest safe section", True)

# supports
if support_cfg.startswith("Simply"):
    supports = [Support(0.0, "pinned"), Support(L, "roller")]
elif support_cfg.startswith("Cantilever"):
    supports = [Support(0.0, "fixed")]
else:
    supports = [Support(0.2 * L, "pinned"), Support(0.85 * L, "roller")]

# service model for deflection; strength model uses load_factor on forces
model_service = BeamModel(L=L, E=E, I=I, supports=supports,
                  point_loads=point_loads, udls=udls, uvls=uvls, moments=moments)
point_f = [PointLoad(p.x, p.P*load_factor) for p in point_loads]
udl_f = [UDL(u.x1, u.x2, u.w*load_factor) for u in udls]
uvl_f = [UVL(u.x1, u.x2, u.w1*load_factor, u.w2*load_factor) for u in uvls]
mom_f = [PointMoment(m.x, m.M*load_factor) for m in moments]
model = BeamModel(L=L, E=E, I=I, supports=supports,
                  point_loads=point_f, udls=udl_f, uvls=uvl_f, moments=mom_f)
result_strength = analyse(model, n=500, defl_limit_ratio=limit_ratio)
result_service = analyse(model_service, n=500, defl_limit_ratio=limit_ratio)
# strength for V,M checks; service deflection for serviceability
result = dict(result_strength)
result["y"] = result_service["y"]
result["y_max"] = result_service["y_max"]
result["y_max_mm"] = result_service["y_max_mm"]
result["serviceability"] = result_service["serviceability"]

# optional auto section
rec = recommend_section(result["M_max"], result["V_max"], grade)
if auto_sec and rec["status"] == "safe" and rec["recommended"] != sec_name:
    sec_name = rec["recommended"]
    sec = get_section(sec_name)
    model.I = sec.I_m4
    result = analyse(model, n=500, defl_limit_ratio=limit_ratio)
    st.info(f"Auto-selected **{sec_name}** (lightest safe).")

chk = stress_check(result["M_max"], result["V_max"], sec, grade)
svc = result["serviceability"]

# KPIs
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Max |V|", f"{result['V_max']/1e3:.2f} kN")
c2.metric("Max |M|", f"{result['M_max']/1e3:.2f} kN·m")
c3.metric("Max |δ|", f"{result['y_max_mm']:.2f} mm")
c4.metric("δ limit", f"{svc['allow_mm']:.1f} mm", delta="OK" if svc["ok"] else "FAIL",
          delta_color="normal" if svc["ok"] else "inverse")
c5.metric("σ util", f"{chk['util_bending']:.0%}", delta="OK" if chk["safe_bending"] else "FAIL",
          delta_color="normal" if chk["safe_bending"] else "inverse")
c6.metric("τ util", f"{chk['util_shear']:.0%}", delta="OK" if chk["safe_shear"] else "FAIL",
          delta_color="normal" if chk["safe_shear"] else "inverse")

ok_all = chk["safe"] and svc["ok"]
if ok_all:
    st.success(f"**{sec_name}** · strength OK · serviceability OK ({defl_limit})")
elif chk["safe"] and not svc["ok"]:
    st.warning(f"**{sec_name}** strength OK but deflection exceeds {defl_limit}.")
else:
    st.error(f"**{sec_name}** fails strength check — increase section or reduce load.")

tabs = st.tabs([
    "SFD / BMD / δ", "3D Views", "Steel comparison", "Parametric", "Summary + CSV"
])

x = result["x"]

with tabs[0]:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        subplot_titles=("Shear V (kN)", "Moment M (kN·m)", "Deflection y (mm)"),
                        vertical_spacing=0.07)
    fig.add_trace(go.Scatter(x=x, y=result["V"]/1e3, fill="tozeroy", line=dict(color="#1f77b4")), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=result["M"]/1e3, fill="tozeroy", line=dict(color="#d62728")), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=result["y"]*1e3, fill="tozeroy", line=dict(color="#2ca02c")), row=3, col=1)
    fig.update_xaxes(title_text="x (m)", row=3, col=1)
    fig.update_layout(height=800, showlegend=False, template="plotly_white", title="SFD · BMD · Deflection")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=x, y=result["V"]/1e3, name="V (kN)", yaxis="y1"))
    fig2.add_trace(go.Scatter(x=x, y=result["M"]/1e3, name="M (kN·m)", yaxis="y2",
                              line=dict(color="#d62728")))
    fig2.update_layout(title="Combined SFD + BMD", xaxis_title="x (m)",
                       yaxis=dict(title="V (kN)"), yaxis2=dict(title="M (kN·m)", overlaying="y", side="right"),
                       height=400, template="plotly_white")
    st.plotly_chart(fig2, use_container_width=True)

with tabs[1]:
    scale = st.slider("Deflection scale", 50.0, 3000.0, 500.0)
    y_def = result["y"] * scale
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter3d(x=x, y=np.zeros_like(x), z=np.zeros_like(x), mode="lines",
                                line=dict(color="gray", width=5), name="Undeformed"))
    fig3.add_trace(go.Scatter3d(x=x, y=np.zeros_like(x), z=y_def, mode="lines",
                                line=dict(color="crimson", width=7), name="Deformed"))
    for s in supports:
        fig3.add_trace(go.Scatter3d(x=[s.x], y=[0], z=[0], mode="markers",
                                    marker=dict(size=5, color="green"), name=s.kind))
    for pl in point_loads:
        fig3.add_trace(go.Scatter3d(x=[pl.x, pl.x], y=[0, 0], z=[0, -0.12 * L],
                                    mode="lines", line=dict(color="orange", width=4), showlegend=False))
    fig3.update_layout(scene=dict(xaxis_title="x (m)", yaxis_title="y", zaxis_title="scaled δ",
                                  aspectmode="manual", aspectratio=dict(x=2.2, y=0.25, z=0.45)),
                       height=500, title="3D axis + scaled deflection", template="plotly_white")
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = go.Figure()
    fig4.add_trace(go.Scatter3d(x=x, y=result["V"]/1e3, z=np.zeros_like(x), mode="lines",
                                line=dict(width=5, color="#1f77b4"), name="V"))
    fig4.add_trace(go.Scatter3d(x=x, y=np.zeros_like(x), z=result["M"]/1e3, mode="lines",
                                line=dict(width=5, color="#d62728"), name="M"))
    fig4.update_layout(scene=dict(xaxis_title="x", yaxis_title="V (kN)", zaxis_title="M (kN·m)"),
                       height=460, title="3D Shear–Moment path", template="plotly_white")
    st.plotly_chart(fig4, use_container_width=True)

    # section extrusion
    h, b, tw, tf = sec.h/1000, sec.b/1000, sec.tw/1000, sec.tf/1000
    xs = np.linspace(0, L, 30)
    outline = np.array([
        [-b/2, -h/2], [b/2, -h/2], [b/2, -h/2+tf], [tw/2, -h/2+tf],
        [tw/2, h/2-tf], [b/2, h/2-tf], [b/2, h/2], [-b/2, h/2],
        [-b/2, h/2-tf], [-tw/2, h/2-tf], [-tw/2, -h/2+tf], [-b/2, -h/2+tf], [-b/2, -h/2]
    ])
    fig5 = go.Figure()
    for i, xi in enumerate(xs[::3]):
        fig5.add_trace(go.Scatter3d(x=np.full(len(outline), xi), y=outline[:,0], z=outline[:,1],
                                    mode="lines", line=dict(color="#1f77b4", width=2),
                                    showlegend=i==0, name=sec_name))
    fig5.update_layout(scene=dict(xaxis_title="x", yaxis_title="width", zaxis_title="depth", aspectmode="data"),
                       height=480, title=f"3D I-section — {sec_name}", template="plotly_white")
    st.plotly_chart(fig5, use_container_width=True)

with tabs[2]:
    rows = compare_sections(result["M_max"], result["V_max"], grade)
    st.dataframe(rows, use_container_width=True)
    st.write(f"Recommended: **{rec['recommended']}** ({rec['status']})")
    names = [r["section"] for r in rows]
    util = [r["util_b"] for r in rows]
    weights = [r["weight_kg_m"] for r in rows]
    colors = ["#2ca02c" if r["safe"] else "#d62728" for r in rows]
    col_a, col_b = st.columns(2)
    with col_a:
        fig = go.Figure(go.Bar(x=names, y=util, marker_color=colors, text=[f"{u:.0%}" for u in util], textposition="outside"))
        fig.add_hline(y=1.0, line_dash="dash")
        fig.update_layout(title="Bending utilisation", xaxis_tickangle=-35, height=400, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig = go.Figure(go.Bar(x=names, y=weights, marker_color="#17becf"))
        fig.update_layout(title="Weight kg/m", xaxis_tickangle=-35, height=400, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    fig = go.Figure(go.Scatter(x=weights, y=util, mode="markers+text", text=names, textposition="top center",
                               marker=dict(size=11, color=colors)))
    fig.add_hline(y=1.0, line_dash="dash")
    fig.update_layout(title="Utilisation vs weight", xaxis_title="kg/m", yaxis_title="util", height=420, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with tabs[3]:
    st.subheader("Parametric study — vary UDL intensity")
    w_max = st.slider("Max UDL (kN/m) for sweep", 2.0, 30.0, 15.0)
    w_list = list(np.linspace(1.0, w_max, 10))
    support_key = "cantilever" if support_cfg.startswith("Cantilever") else "simple"
    prow = parametric_udl(L, E, I, w_list, support=support_key)
    pdf = pd.DataFrame(prow)
    st.dataframe(pdf, use_container_width=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pdf["w_kNpm"], y=pdf["M_max_kNm"], mode="lines+markers", name="Mmax kNm"))
    fig.add_trace(go.Scatter(x=pdf["w_kNpm"], y=pdf["V_max_kN"], mode="lines+markers", name="Vmax kN"))
    fig.add_trace(go.Scatter(x=pdf["w_kNpm"], y=pdf["y_max_mm"], mode="lines+markers", name="δmax mm", yaxis="y2"))
    fig.update_layout(title="Response vs UDL", xaxis_title="w (kN/m)",
                      yaxis=dict(title="M / V"), yaxis2=dict(title="δ mm", overlaying="y", side="right"),
                      height=420, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with tabs[4]:
    st.subheader("Reactions")
    for xs, R in result["reactions"].items():
        st.write(f"· Support at x = {xs:.3f} m → **R = {R/1e3:.3f} kN**")
    if result.get("reactions_raw", {}).get("M_fixed") is not None:
        st.write(f"· Fixed-end moment ≈ **{result['reactions_raw']['M_fixed']/1e3:.3f} kN·m**")

    st.subheader("Design summary")
    summary = {
        "L_m": L,
        "support": support_cfg,
        "section": sec_name,
        "grade": grade,
        "V_max_kN": round(result["V_max"]/1e3, 3),
        "M_max_kNm": round(result["M_max"]/1e3, 3),
        "y_max_mm": round(result["y_max_mm"], 3),
        "defl_limit": defl_limit,
        "defl_ok": svc["ok"],
        "sigma_MPa": round(chk["sigma_MPa"], 2),
        "tau_MPa": round(chk["tau_MPa"], 2),
        "util_b": round(chk["util_bending"], 3),
        "util_s": round(chk["util_shear"], 3),
        "strength_ok": chk["safe"],
        "overall_ok": ok_all,
        "recommended_section": rec["recommended"],
    }
    st.json(summary)

    # CSV export
    df_x = pd.DataFrame({
        "x_m": result["x"],
        "V_N": result["V"],
        "M_Nm": result["M"],
        "y_m": result["y"],
    })
    csv = df_x.to_csv(index=False)
    st.download_button("Download V/M/y CSV", csv, file_name="beam_VM_deflection.csv", mime="text/csv")
    st.download_button("Download summary JSON", pd.Series(summary).to_json(), file_name="beam_summary.json")
