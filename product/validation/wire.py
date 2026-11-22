"""Continuous nonlocal self-clearance for the producer's 2.20 XY by 1.20 Z lead reservation.
Every segment pair lives in a convex (u,v) parameter square. Clip by distance
along the wire and Z proximity, then minimize Euclidean XY separation exactly
over the remaining polygon (rank-deficient parallel pairs reduce to edges).
"""
import math
import json
from contracts import demand

def clip(poly,A,B,C):
    if not poly:return []
    out=[]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        f=A*p[0]+B*p[1]+C;g=A*q[0]+B*q[1]+C
        if f>=0: out.append(p)
        if (f>=0)!=(g>=0):
            t=f/(f-g);out.append(tuple(a+t*(b-a) for a,b in zip(p,q)))
    return out


def clearance(file):
    pts=json.loads(file.read_text())["centerlineXYZ_mm"]; segments=[];s=0.
    for p,q in zip(pts,pts[1:]):
        d=[b-a for a,b in zip(p,q)];length=math.dist(p,q)
        if length>1e-10:segments.append((p,d,s,length))
        s+=length
    demand(abs(s-105)<.01,"invalid installed lead length")
    margin=1.20-1e-7;best=None;hits=0
    for i,(p,dp,sp,lp) in enumerate(segments):
        for q,dq,sq,lq in segments[i+1:]:
            # Ignore the contiguous bend neighborhood, not separate runs.
            if sq+lq-sp<6:continue
            poly=[(0,0),(1,0),(1,1),(0,1)]
            poly=clip(poly,-lp,lq,sq-sp-6)
            poly=clip(poly,dp[2],-dq[2],p[2]-q[2]+margin)
            poly=clip(poly,-dp[2],dq[2],q[2]-p[2]+margin)
            if not poly:continue
            def xy(u,v):return [p[k]+u*dp[k]-q[k]-v*dq[k] for k in [0,1]]
            cand=poly[:];det=dp[1]*dq[0]-dp[0]*dq[1]
            if abs(det)>1e-12:
                x,y=xy(0,0);u=(x*dq[1]-y*dq[0])/det;v=(dp[1]*x-dp[0]*y)/det
                if 0<=u<=1 and 0<=v<=1 and sq+lq*v-sp-lp*u>=6 and abs(p[2]+u*dp[2]-q[2]-v*dq[2])<=margin:cand.append((u,v))
            for a,b in zip(poly,poly[1:]+poly[:1]):
                x,y=xy(*a);xx,yy=xy(*b);dx,dy=xx-x,yy-y
                if dx*dx+dy*dy<=1e-20:continue
                t=max(0,min(1,-(x*dx+y*dy)/(dx*dx+dy*dy)))
                cand.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
            rho,u,v=min((math.hypot(*xy(u,v)),u,v) for u,v in cand)
            hits+=rho<2.2-1e-7
            if best is None or rho<best[0]:
                best=(rho,abs(p[2]+u*dp[2]-q[2]-v*dq[2]),sp+lp*u,sq+lq*v)
    demand(best,"no eligible separated cable segments")
    rho,dz,a,b=best
    obs=(f"{s:.3f} mm path, {len(segments)} linear pieces; {hits} nonlocal segment-pair overlaps in the assumed 2.20 mm XY × 1.20 mm Z wire reservation. "
         f"Over all continuous points ≥6 mm apart along the wire and <1.20 mm apart in Z, minimum XY {rho:.3f} mm (Z separation {dz:.3f}; arc lengths {a:.3f}/{b:.3f} mm). "
         "This tests the reserved volume, not actual conductor geometry, conductor strain, or the local 6 mm bend neighborhood.")
    return ("FAIL" if hits else "PASS_DIGITAL"),obs
