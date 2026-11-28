"""Write the KiCad project file: design rules and net classes shared by the router and DRC."""
import json
from design import ROOT, STEM, LIB, ANALOG, BATTERY, CONTROL

POWER = ("VCC", "VS_A", "VS_B", "VSW_A", "VSW_B")
CLASSES = {"Power": POWER, "Battery": BATTERY, "Analog": ANALOG,
           "Control": tuple(net for net in CONTROL if net not in BATTERY)}


def create(directory, lib_rel=".", margin=0.0):
    """margin widens the clearances the autorouter sees, leaving room to restore class widths afterwards."""
    p = {"meta": {"filename": STEM + ".kicad_pro", "version": 1},
         "board": {"design_settings": {
             "drc_exclusions": [], "defaults": {}, "diff_pair_dimensions": [],
             "track_widths": [0, 0.2, 0.4], "via_dimensions": [],
             "rules": {"min_clearance": 0.20, "min_track_width": 0.15, "min_via_diameter": 0.60,
                       "min_via_annular_width": 0.15, "min_through_hole_diameter": 0.30,
                       "min_copper_edge_clearance": 0.30, "min_hole_clearance": 0.30,
                       "min_hole_to_hole": 0.50, "min_resolved_spokes": 2}}},
         "net_settings": {"meta": {"version": 3}, "classes": [
             dict(name="Default", description="Signals and ground", clearance=round(0.2 + margin / 3, 3), track_width=0.2,
                  via_diameter=0.6, via_drill=0.3),
             dict(name="Power", description="Supply and battery", clearance=0.2 + margin, track_width=0.4,
                  via_diameter=0.7, via_drill=0.3),
             dict(name="Battery", description="Battery and charge path", clearance=0.2, track_width=0.4,
                  via_diameter=0.7, via_drill=0.3),
             dict(name="Analog", description="Sensor to ADC paths", clearance=0.2, track_width=0.2,
                  via_diameter=0.6, via_drill=0.3),
             dict(name="Control", description="Digital controls", clearance=0.2, track_width=0.2,
                  via_diameter=0.6, via_drill=0.3)],
             "netclass_patterns": [dict(netclass=cls, pattern=net) for cls, nets in CLASSES.items() for net in nets]},
         "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
         "pcbnew": {"page_layout_descr_file": ""}, "sheets": [], "text_variables": {}}
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (STEM + ".kicad_pro")).write_text(json.dumps(p, indent=2) + "\n")
    (directory / (STEM + ".kicad_dru")).write_text(
        '(version 1)\n'
        '(rule "Battery track width"\n'
        '  (condition "A.NetClass == \'Battery\'")\n'
        '  (constraint track_width (min 0.40mm)))\n'
        '(rule "Analog separation from control and battery"\n'
        '  (condition "A.NetClass == \'Analog\' && (B.NetClass == \'Control\' || B.NetClass == \'Battery\') && A.Type == \'Track\' && B.Type == \'Track\'")\n'
        '  (constraint clearance (min 0.50mm)))\n'
        '(rule "Controller through-hole ground can connect solid"\n'
        '  (condition "A.memberOfFootprint(\'A1\') && A.Pad_Number == \'3\'")\n'
        '  (constraint zone_connection solid))\n')
    (directory / "fp-lib-table").write_text(
        f'(fp_lib_table (version 7) (lib (name "{LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/{lib_rel}/{LIB}.pretty")'
        '(options "")(descr "TMR half project footprints")))\n')


if __name__ == "__main__":
    create(ROOT)
    create(ROOT / "build", "..")
