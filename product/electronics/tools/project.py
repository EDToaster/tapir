"""Set explicit carrier stack/rule floor in the KiCad project, shared by router and DRC."""
import json
from pathlib import Path
from design import ROOT

def create(hand):
    stem="tapir-"+hand
    p={"meta":{"filename":stem+".kicad_pro","version":1},
       "board":{"design_settings":{"drc_exclusions":[],"defaults":{},"diff_pair_dimensions":[],
         "track_widths":[0,0.2,0.3],"via_dimensions":[],
         "rules":{"min_clearance":0.20,"min_track_width":0.20,"min_via_diameter":0.60,
                  "min_via_annular_width":0.15,"min_through_hole_diameter":0.30,
                  "min_copper_edge_clearance":0.30,"min_hole_clearance":0.25}}},
       "net_settings":{"meta":{"version":3},
         "classes":[dict(name="Default",description="Signal",clearance=.2,track_width=.2,via_diameter=.60,via_drill=.30),
                    dict(name="Power",description="Low-current switched and ground buses",clearance=.2,track_width=.30,via_diameter=.65,via_drill=.30)],
         "netclass_patterns":[dict(netclass="Power",pattern=n) for n in ("CELL_PLUS","VBAT_SW","3V3","PTR_3V3","GND")]},
       "libraries":{"pinned_footprint_libs":[],"pinned_symbol_libs":[]},"pcbnew":{"page_layout_descr_file":""},
       "sheets":[],"text_variables":{}}
    for base in (ROOT/hand,ROOT/"build"/hand):
        base.mkdir(parents=True,exist_ok=True)
        (base/(stem+".kicad_pro")).write_text(json.dumps(p,indent=2)+"\n")
        rel=".." if base==ROOT/hand else "../.."
        (base/"fp-lib-table").write_text('(fp_lib_table (version 7) (lib (name "Tapir")(type "KiCad")(uri "${KIPRJMOD}/'+rel+'/Tapir.pretty")(options "")(descr "Tapir project footprints")))\n')
if __name__=="__main__":
    for side in ("left","right"):create(side)
