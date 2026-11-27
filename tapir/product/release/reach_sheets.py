"""True-scale, one-hand reach and cable sheets; millimetres in the native PCB frame."""
from html import escape
from math import hypot
from xml.etree.ElementTree import fromstring

def sheet(h):
    hand=h["hand"];m=h["usbMouth"];dx,dy=m["direction"]
    assert abs(hypot(dx,dy)-1)<1e-8
    plug=[[m["x"]+d*dx-w*dy,m["y"]+d*dy+w*dx] for d,w in [(0,-6.175),(36,-6.175),(36,6.175),(0,6.175)]]
    allpt=h["outline"]+plug
    x0=min(pt[0] for pt in allpt);x1=max(pt[0] for pt in allpt)
    y0=min(pt[1] for pt in allpt);y1=max(pt[1] for pt in allpt)
    # Translation only: neither orientation nor print scale is inferred or fitted.
    tx=(210-x1-x0)/2;ty=45-y0
    assert 12<=x0+tx<x1+tx<=198 and y1+ty<222
    def poly(p,fill,stroke,w=.25,dash=""):
        return '<polygon points="'+' '.join(f"{x:.5f},{y:.5f}" for x,y in p)+f'" fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-dasharray="{dash}"/>'
    def text(x,y,label,size=3,anchor="start",color="#26332d"):
        return f'<text x="{x:.5f}" y="{y:.5f}" fill="{color}" font-family="sans-serif" font-size="{size}" text-anchor="{anchor}">{escape(str(label))}</text>'
    v=['<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">','<title>Tapir Rev A · true-scale '+hand+' reach pattern</title>','<rect width="210" height="297" fill="white"/>',
       text(15,16,"TAPIR  /  REV A  /  REACH AND CABLE",3),text(15,26,hand.title()+" hand · top view",6),
       text(15,33,"Finger rows above, thumb row below. One unit on this drawing equals one millimetre.",2.9),
       f'<g transform="translate({tx:.5f} {ty:.5f})">',
       poly(h["outline"],"#e7eee5","#355040",.4),poly(plug,"#f5ddc7","#994f30",.28,"1 .5")]
    for s in h["switches"]:
        v += [poly(s["capPolygon"],"#f4f1df" if not s["thumb"] else "#dce4db","#435344"),
              text(s["x"],s["y"]+1.1,s["label"],3.1,"middle")]
    for b in h["buttons"]:
        v += [poly(b["paddle"]["polygon"],"#dbe4db","#546256"),text(b["x"],b["y"]+0.8,b["label"],2.3,"middle")]
    if hand=="right":
        c=h["components"]["rubberCap"];v += [poly(c["polygon"],"#c65d40","#6b281f"),text(c["x"],c["y"]+.7,"+",2.6,"middle","white")]
    for b in h["mountingHoles"]:v.append(f'<circle cx="{b["x"]}" cy="{b["y"]}" r="{b["diameter"]/2}" fill="white" stroke="#4b6552" stroke-width=".2"/>')
    v+=['</g>',text(15,216,"Scale check · measure between end ticks",3.2),'<path d="M 15 221 v 5 M 15 223.5 h 50 M 65 221 v 5" fill="none" stroke="#243b2e" stroke-width=".35"/>',text(70,224.5,"50.00 mm",3.3),
        text(15,237,"Print at 100% / actual size. Disable fit-to-page and measure the rule before using this sheet.",3),
        text(15,245,"Green boundary: actual carrier, not the case. Orange outline: external USB-C shoulder gauge.",3),
        text(15,253,"Place your hand in typing position. Try the thumb keys, controls and plug approach without lifting your palm.",2.85),
        text(15,261,"Record: reachable controls, unintended presses, wrist/plug contact and desired shift in mm.",3),
        text(15,279,"Rev A · packaging study only; paper cannot test key travel, electrical contact or pointer force.",2.8),'</svg>']
    out='\n'.join(v);fromstring(out);return out
