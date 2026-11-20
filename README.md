# Beam Designer v2.1 (Streamlit)

**SFD · BMD · Deflection · Serviceability · ULS load factor · Auto section · 3D · Parametric · CSV**

## What’s included

| Capability | Detail |
|------------|--------|
| Supports | Simply supported, cantilever, **overhang** |
| Loads | Point, UDL, UVL/trapezoid, point moment |
| **ULS load factor** | Strength uses factored loads; δ uses service |
| Diagrams | SFD, BMD, deflection, combined |
| **3D** | Axis + scaled δ, V–M path, I-section extrusion |
| Steel | ISMB/UB catalog, σ/τ check, utilisation |
| Auto-select | Lightest **safe** section |
| Serviceability | L/250 … L/500 |
| Parametric | UDL sweep charts |
| Export | CSV (V,M,y) + JSON summary |

## Quick start

```bash
pip install -r requirements.txt
streamlit run app_streamlit.py
pytest test_beam.py -v
```

## Diagram gallery

### Design workflow
![Workflow](design_workflow.png)

### Load case gallery (SFD & BMD)
![Gallery](load_case_gallery.png)

### Classic SFD / BMD / δ
![SFD](sfd_bmd_deflection.png)

### Overhang
![Overhang](overhang_sfd_bmd.png)

### Support-type comparison
![Supports](support_type_comparison.png)

### Section comparison & utilisation
![Sections](section_comparison.png)
![Util bars](utilisation_bars.png)
![Util vs weight](util_vs_weight.png)

### Auto-recommend summary
![Recommend](auto_recommend_summary.png)

### Section capacity chart
![Capacity](section_capacity_chart.png)

### Deflection by section
![Defl](deflection_by_section.png)

### Serviceability
![Service](serviceability_check.png)

### Moment heatmap (L × w)
![Heatmap](moment_heatmap.png)

### Before / after auto-select
![Auto](before_after_autoselect.png)

### 3D schematic
![3D](beam_3d_schematic.png)

### Response vs UDL
![UDL](response_vs_udl.png)

### Load schematic
![Schematic](load_support_schematic.png)

## Modules

| File | Role |
|------|------|
| `beam_solver.py` | V, M, δ, serviceability, parametric |
| `steel_sections.py` | Catalog, checks, recommend |
| `app_streamlit.py` | Dashboard |
| `test_beam.py` | 5 analytical / unit tests |

## Layout (completely flat — no sub-folders)

```
.
├── README.md  LICENSE  requirements.txt  .gitignore
├── beam_solver.py  steel_sections.py  app_streamlit.py  test_beam.py
└── 17 PNG diagrams (design_workflow.png, sfd_bmd_deflection.png, ...)
```

## Notes

Educational portfolio tool. Simplified checks — not a full IS 800 / AISC design package.

**Tags:** `beam-design` `sfd` `bmd` `steel` `streamlit` `mechanical-engineering`


## License

MIT — see [LICENSE](LICENSE).
