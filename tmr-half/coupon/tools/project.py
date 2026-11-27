"""Write the KiCad project file: design rules and net classes shared by the router and DRC."""
import json
from design import ROOT, STEM, LIB

POWER = ("VCC", "VS_A", "VS_B", "VSW_A", "VSW_B", "BAT_P", "BAT_SW")


def create(directory, lib_rel=".", margin=0.0):
    """margin widens the clearances the autorouter sees, leaving room to restore class widths afterwards."""
    p = {"meta": {"filename": STEM + ".kicad_pro", "version": 1},
         "board": {"design_settings": {
             "drc_exclusions": [], "defaults": {}, "diff_pair_dimensions": [],
             "track_widths": [0, 0.2, 0.4], "via_dimensions": [],
             "rules": {"min_clearance": 0.20, "min_track_width": 0.15, "min_via_diameter": 0.60,
                       "min_via_annular_width": 0.15, "min_through_hole_diameter": 0.30,
                       "min_copper_edge_clearance": 0.30, "min_hole_clearance": 0.25,
                       "min_hole_to_hole": 0.50, "min_resolved_spokes": 1}}},
         "net_settings": {"meta": {"version": 3}, "classes": [
             dict(name="Default", description="Signals and ground", clearance=round(0.2 + margin / 3, 3), track_width=0.2,
                  via_diameter=0.6, via_drill=0.3),
             dict(name="Power", description="Supply and battery", clearance=0.2 + margin, track_width=0.4,
                  via_diameter=0.7, via_drill=0.3)],
             "netclass_patterns": [dict(netclass="Power", pattern=n) for n in POWER]},
         "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
         "pcbnew": {"page_layout_descr_file": ""}, "sheets": [], "text_variables": {}}
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (STEM + ".kicad_pro")).write_text(json.dumps(p, indent=2) + "\n")
    (directory / "fp-lib-table").write_text(
        f'(fp_lib_table (version 7) (lib (name "{LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/{lib_rel}/{LIB}.pretty")'
        '(options "")(descr "TMR half project footprints")))\n')


if __name__ == "__main__":
    create(ROOT)
    create(ROOT / "build", "..")
