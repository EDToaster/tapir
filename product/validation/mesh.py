"""Independent sectional tests on emitted, assembled-pose binary STL material.

These parts consist of straight extrusions. Compare each Z slab separated by a
mesh vertex level. This is *not* an exact swept-volume checker for a general
filleted/tilted redesign: we explicitly reject non-vertical side facets.
"""
import math
import struct
from functools import lru_cache
from native import Blocked, point_segment
from contracts import demand


def inside(p,edges):
    px,py=p; n=0
    for (x,y),(xx,yy) in edges:
        if (y>py)!=(yy>py) and px < x+(xx-x)*(py-y)/(yy-y): n+=1
    return bool(n%2)


def cross(a,b,p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])


def overlaps(poly,edges):
    if not edges: return False
    pe=list(zip(poly,poly[1:]+poly[:1]))
    x0=min(p[0] for p in poly); x1=max(p[0] for p in poly)
    y0=min(p[1] for p in poly); y1=max(p[1] for p in poly)
    for a,b in edges:
        if max(a[0],b[0])<x0 or min(a[0],b[0])>x1 or max(a[1],b[1])<y0 or min(a[1],b[1])>y1: continue
        if inside(a,pe) or inside(b,pe): return True
        for c,d in pe:
            if cross(a,b,c)*cross(a,b,d)<-1e-14 and cross(c,d,a)*cross(c,d,b)<-1e-14: return True
    return any(inside(p,edges) for p in poly)


class SectionMesh:
    def __init__(self,path):
        f=path.read_bytes(); n=struct.unpack_from("<I",f,80)[0]
        demand(len(f)==84+50*n and n>=4,"malformed binary STL")
        self.ts=[]; self.levels=set()
        for *vs,_ in struct.iter_unpack("<12fH",f[84:]):
            # Native CAD convention x,-y,z -> source plan x,+y,z.
            t=[(vs[i],-vs[i+1],vs[i+2]) for i in (3,6,9)]
            z=[v[2] for v in t]; self.levels.update(z)
            if max(z)-min(z)<1e-6: continue
            # Vertical side: area of triangle projected on XY must be zero.
            # Normalize by facet extent: float32 STL vertices of a 10-mm
            # collinear side can have a few microns *area* error but submicron
            # positional error. Reject more than 0.00002 mm off the side line.
            extent=max(math.dist(a[:2],b[:2]) for a,b in zip(t,t[1:]+t[:1]))
            if extent and abs(cross(*t))/extent>2e-5:
                raise Blocked(f"{path.name} has inclined/freeform faces; sectional prismatic proof not valid")
            self.ts.append((min(z),max(z),t))
        self.levels=sorted(self.levels)

    @lru_cache(maxsize=None)
    def edges(self,z):
        seg=[]
        for lo,hi,t in self.ts:
            if not lo<z<hi: continue
            pts=[]
            for a,b in zip(t,t[1:]+t[:1]):
                if (a[2]>z)!=(b[2]>z):
                    f=(z-a[2])/(b[2]-a[2]); pts.append(tuple(a[i]+f*(b[i]-a[i]) for i in (0,1)))
            if len(pts)==2: seg.append(pts)
        return seg

    def sweep(self,poly,lo,hi):
        bounds=sorted(set([lo,hi]+[z for z in self.levels if lo<z<hi]))
        hit=[]
        for a,b in zip(bounds,bounds[1:]):
            if b-a>1e-5 and overlaps(poly,self.edges((a+b)/2)): hit.append((a,b))
        return hit


def cases(h,tray,cover):
    tests={}
    holes=h["mountingHoles"]; e=tray.edges(-3.0); measured=[]
    for s in holes:
        p=s["x"],s["y"]
        demand(not inside(p,e),f"{s['ref']}: filled boss center at z=-3")
        r=min(point_segment(p,seg) for seg in e)
        annulus=sum(inside((p[0]+1.7*math.cos(i*math.pi/8),p[1]+1.7*math.sin(i*math.pi/8)),e) for i in range(16))
        demand(1.15<r<1.25 and annulus==16,f"{s['ref']}: radius {r:.3f}, boss material in {annulus}/16 directions")
        measured.append(r)
    tests["boss-bore"]=f"{len(holes)} boss bores in actual tray mesh at z=−3.0; centers void, 16/16 annulus probes each; minimum center-to-wall radius {min(measured):.3f} mm (nominal Ø2.4 case bores)"
    probes=[("board",h["outline"],h["pcb"]["bottom"])]+[
        (s["id"],s["polygon"],s["bottom"]) for s in h["solids"] if s["role"] in ("switch-tail","matrix-diode")]
    hit=[id for id,poly,z in probes if tray.sweep(poly,z,25)]
    tests["tray-insertion"]=(("FAIL",f"open tray intersects vertical insertion at {hit[:12]}") if hit else
         f"Vertical insertion/removal sweep: actual open tray mesh vs board outline + {len(probes)-1} switch-tail and backside-diode envelopes from seated heights to +25 mm; no material overlap. Other parts installed after board per assembly order.")
    c=h["components"]; m=h["usbMouth"]; ux,uy=m["direction"]
    gauge=[[m["x"]+ux*d-uy*w,m["y"]+uy*d+ux*w] for d,w in ((0,-6.175),(38,-6.175),(38,6.175),(0,6.175))]
    # Gauge Z explicitly declared here; verify with a real plug and actual socket mating datum.
    z=-.0; hit=tray.sweep(gauge,z,z+6.50)+cover.sweep(gauge,z,z+6.50)
    tests["usb-bezel"]=(("FAIL",f"12.35 × 6.50 mm plug gauge vs exported shell hits z slabs {hit}") if hit else
        "12.35 × 6.50 mm overmold prism, 38 mm straight approach from declared mouth, Z 0..6.50: no tray/bezel material in emitted meshes; seating datum/real overmold not validated.")
    strokes=[s for s in h["solids"] if s["role"]=="key-sweep"]
    hit=[s["id"] for s in strokes if cover.sweep(s["polygon"],s["bottom"],s["top"])]
    tests["bezel-stroke"]=(("FAIL",f"actual bezel overlaps {len(hit)} full key-strokes: {hit}") if hit else
        f"Entire 3 mm cap-travel envelope for {len(strokes)} keys vs the actual emitted bezel mesh; zero material intersections across all overlapping Z slabs.")
    return tests


def pouch(h,meshes):
    p=h["components"]["battery"]; x,y=p["x"],p["y"]
    poly=[(x+sx*12.3/2,y+sy*32/2) for sx,sy in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    conflicts=[(n,m.sweep(poly,0,4.3)) for n,m in meshes.items()]
    demand(not any(v for n,v in conflicts),f"drawing maximum cell intersects printed material: {conflicts}")
    return ("12.3 × 32 × 4.3 mm cell at drawing maximum vs actual tray, bezel and pouch organizer across all intersecting height slabs: no material intersection. "
            "Cell growth and the 105 mm lead/mate remain separate physical gates.")


def sensor_bores(h,bridge):
    c=h["components"]; z=(c["bridge"]["top"]+c["bridge"]["bottom"])/2; edges=bridge.edges(z)
    vals=[]
    for b in c["sensorHoles"]:
        p=(b["x"],b["y"])
        demand(not inside(p,edges) and b["diameter"]==1.8,"sensor-hole center obstructed or wrong sensor Ø")
        vals.append(min(point_segment(p,e) for e in edges))
    demand(len(vals)==4 and min(vals)>.68 and max(vals)<.76,f"unexpected bridge hole radii {vals}")
    return (f"4 bridge-bore centers at sensor's 9.5 mm square drill coordinates; actual mesh in-plane radii "
            f"{min(vals):.3f}..{max(vals):.3f} mm under nominal Ø1.80 sensor features. Not a screw/paste/bond specification; actual sensor retention unqualified.")


def analog_route(h,meshes):
    route=h["wiring"]["sensorToDriver"]; pts=route["points"]
    radius=route["bundleAllowance"]["width"]/2; half=route["bundleAllowance"]["height"]/2
    demand((radius,half)==(1.4,.4),"unknown analog bundle allowance")
    best=None; hits=0
    for name,m in meshes.items():
        for lo,hi in zip(m.levels,m.levels[1:]):
            if hi-lo<1e-6:continue
            edges=m.edges((lo+hi)/2)
            if not edges:continue
            for i,(p,q) in enumerate(zip(pts,pts[1:])):
                dz=q[2]-p[2]; low=0;high=1
                if abs(dz)<1e-10:
                    if p[2]+half<=lo or p[2]-half>=hi:continue
                else:
                    a,b=sorted(((lo-half-p[2])/dz,(hi+half-p[2])/dz))
                    low=max(a,0);high=min(b,1)
                    if high<=low: continue
                a,b=[tuple(p[k]+z*(q[k]-p[k]) for k in (0,1)) for z in (low,high)]
                if inside(a,edges) or inside(b,edges):rho=0.
                else:
                    def sep(e):
                        v,w=e
                        if cross(a,b,v)*cross(a,b,w)<0 and cross(v,w,a)*cross(v,w,b)<0:return 0.
                        return min(point_segment(a,e),point_segment(b,e),point_segment(v,(a,b)),point_segment(w,(a,b)))
                    rho=min(sep(e) for e in edges)
                gap=rho-radius;hits+=gap<-.00002
                if best is None or gap<best[0]:best=(gap,name,i)
    length=sum(math.dist(p,q) for p,q in zip(pts,pts[1:]))
    demand(abs(length-route["polylineLength"])<.00001 and best,"missing analog path")
    msg=(f"Continuous {length:.3f} mm 3D provisional sensor→driver centerline with 2.80 mm XY diameter and 0.80 mm height vs every slab of {len(meshes)} emitted prints. "
         f"Closest in-plane material gap in intersecting Z slab: {best[0]:+.3f} mm to {best[1]} on segment {best[2]+1}; {hits} intersecting segment/slab pairs. Solder lands, terminals, flex and retention are provisional.")
    return ("FAIL" if hits else "PASS_DIGITAL"),msg
