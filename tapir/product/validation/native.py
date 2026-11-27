"""Minimal read-only extractors for native files. Reject syntax/geometry we do not test."""
from __future__ import annotations
import json
import math
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path


class Blocked(Exception):
    pass


def sexp(s):
    tok = re.compile(r'\s+|"(?:\\.|[^"\\])*"|[()]|[^()\s"]+')
    stack = [[]]
    for t in tok.findall(s):
        if t.isspace():
            continue
        if t == "(":
            item = []
            stack[-1].append(item)
            stack.append(item)
        elif t == ")":
            if len(stack) < 2:
                raise ValueError("Unexpected )")
            stack.pop()
        else:
            stack[-1].append(t[1:-1].replace(r'\"', '"') if t.startswith('"') else t)
    if len(stack) != 1 or len(stack[0]) != 1:
        raise ValueError("Incomplete or multiple top-level KiCad expressions")
    return stack[0][0]


def children(e, key):
    return [v for v in e if isinstance(v, list) and v and v[0] == key]


def get(e, key, default=None):
    return next(iter(children(e, key)), default)


def numpt(node):
    return tuple(map(float, node[1:3]))


def normnet(s):
    return s.lstrip("/") if s else ""


class Board:
    def __init__(self, path):
        tree = sexp(path.read_text())
        if tree[0] != "kicad_pcb":
            raise ValueError("Not a KiCad board")
        self.tree = tree
        self.thickness = float(get(get(tree, "general"), "thickness")[1])
        self.tracks = len(children(tree, "segment")) + len(children(tree, "arc"))
        self.vias = len(children(tree, "via"))
        self.parts = {}
        for f in children(tree, "footprint"):
            props = {p[1]: p[2] for p in children(f, "property")}
            ref = props.get("Reference")
            if not ref or ref in self.parts:
                raise ValueError(f"Missing or duplicate footprint reference: {ref}")
            at = get(f, "at")
            pads = []
            for p in children(f, "pad"):
                net = get(p, "net")
                # v9 has (net ID "name"); v10 uses (net "name").
                netname = normnet(net[-1]) if net else ""
                drill = get(p, "drill", ["drill"])
                pads.append(dict(pin=p[1], kind=p[2], local=numpt(get(p, "at")),
                                 drill=[float(v) for v in drill[1:] if isinstance(v, str) and re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', v)],
                                 net=netname))
            self.parts[ref] = dict(footprint=f[1], value=props.get("Value",""),
                                   xy=numpt(at), angle=float(at[3]) if len(at)>3 else 0,
                                   layer=get(f, "layer")[1], pads=pads, models=[m[1] for m in children(f,"model")])

    def endpoints(self):
        ep = {}
        for ref, f in self.parts.items():
            for p in f["pads"]:
                if not p["pin"] or not p["net"] or p["net"].startswith("unconnected-"):
                    continue
                key = (ref, p["pin"])
                if key in ep and ep[key] != p["net"]:
                    raise ValueError(f"Stacked pads disagree on {key}")
                ep[key] = p["net"]
        return ep

    def outline(self):
        edges = []
        for e in self.tree:
            if not isinstance(e,list) or len(e)<2 or not str(e[0]).startswith("gr_"):
                continue
            if get(e,"layer", ["",""])[1] != "Edge.Cuts":
                continue
            if e[0] == "gr_line":
                edges.append([numpt(get(e,"start")),numpt(get(e,"end"))])
            elif e[0] == "gr_poly":
                pts = [numpt(p) for p in children(get(e, "pts"), "xy")]
                edges.extend(zip(pts, pts[1:]+pts[:1]))
            else:
                raise Blocked(f"Edge.Cuts contains {e[0]}; no silently approximated arc/slot")
        if not edges:
            raise Blocked("No native Edge.Cuts lines/polygons")
        return edges


def nets_from_xml(file):
    root = ET.parse(file).getroot()
    ep = {}
    for n in root.findall("./nets/net"):
        name = normnet(n.get("name"))
        if not name or name.startswith("unconnected-"):
            continue
        for p in n.findall("node"):
            key = (p.get("ref"), p.get("pin"))
            if key in ep:
                raise ValueError(f"Duplicate schematic endpoint {key}")
            ep[key] = name
    if not ep:
        raise ValueError("Empty exported schematic netlist")
    return ep


def point_segment(p, edge):
    a,b=edge
    d=[b[i]-a[i] for i in range(2)]
    n=sum(x*x for x in d)
    t=min(1,max(0,sum((p[i]-a[i])*d[i] for i in range(2))/n)) if n else 0
    return math.dist(p, [a[i]+t*d[i] for i in range(2)])


def contour_residual(a, b):
    # Requiring matching endpoints *and segment midpoints* in both directions
    # detects misordered vertices/concave contours, not just matching bboxes.
    def dist(edges, target):
        return max(min(point_segment(p,t) for t in target)
                   for u,v in edges for p in (u,v,[(u[i]+v[i])/2 for i in range(2)]))
    return max(dist(a,b),dist(b,a))


def uf2_info(path):
    data = path.read_bytes()
    if not data or len(data)%512:
        raise ValueError("Invalid UF2 size")
    seen = set()
    ranges = []
    total = len(data)//512
    for i in range(total):
        h = struct.unpack_from("<8I", data, i*512)
        m0,m1,flags,target,n,block,blocks,family = h
        if (m0,m1) != (0x0A324655,0x9E5D5157) or struct.unpack_from("<I",data,i*512+508)[0] != 0x0AB16F30:
            raise ValueError("Invalid UF2 magic")
        if not(flags&0x2000) or family != 0xADA52840 or n<1 or n>476 or blocks!=total or block>=total or block in seen:
            raise ValueError("Invalid family, flags, payload or block number")
        if target<0x1000 or target+n>0x100000:
            raise ValueError("Block outside nRF52840 app flash")
        seen.add(block)
        ranges.append((target,target+n))
    sr=sorted(ranges)
    if any(v[1]>w[0] for v,w in zip(sr,sr[1:])):
        raise ValueError("Overlapping flash ranges")
    return dict(blocks=total, payload_bytes=sum(b-a for a,b in ranges), lowest_address=hex(sr[0][0]),
                end_exclusive=hex(sr[-1][1]))
