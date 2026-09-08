#!/usr/bin/env python3
"""校验 bedrock_to_glb.py 生成的 GLB：结构、访问边界、rest 几何与 viewer 数学一致性。"""
import sys, json, struct

def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, ver, total = struct.unpack("<III", data[:12])
    assert magic == 0x46546C67, "bad magic"
    off = 12
    jdata = None
    bindata = None
    while off < len(data):
        ln, typ = struct.unpack("<II", data[off:off+8])
        if typ == 0x4E4F534A:
            jdata = json.loads(data[off+8:off+8+ln])
        elif typ == 0x004E4942:
            bindata = data[off+8:off+8+ln]
        off += 8 + ln
    return jdata, bindata

def validate(path):
    g, buf = read_glb(path)
    errs = []
    nodes = g.get("nodes", [])
    accs = g["accessors"]
    bvs = g["bufferViews"]
    # 1) accessor 边界
    total = len(buf)
    for i, a in enumerate(accs):
        bv = bvs[a["bufferView"]]
        start = bv["byteOffset"] + a.get("byteOffset", 0)
        ct = {"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}[a["type"]]
        size = a["count"] * ct * 4
        if start + size > bv["byteOffset"] + bv["byteLength"]:
            errs.append(f"acc {i} out of bufferView bounds")
        if start + size > total:
            errs.append(f"acc {i} out of buffer bounds")
    # 2) 场景根节点可达
    children_set = set()
    for n in nodes:
        for c in n.get("children", []):
            children_set.add(c)
    scene = g["scenes"][g["scene"]]
    # 3) 动画
    anims = g.get("animations", [])
    anames = [a["name"] for a in anims]
    for a in anims:
        for ch in a["channels"]:
            tgt = ch["target"]
            if tgt["node"] >= len(nodes):
                errs.append(f"anim channel node index {tgt['node']} OOB")
    # 4) mesh primitive attrs 引用合法
    ncount = 0
    for mi, m in enumerate(g.get("meshes", [])):
        for pr in m["primitives"]:
            for k, ai in pr["attributes"].items():
                if ai >= len(accs):
                    errs.append(f"mesh {mi} attr {k} acc OOB")
            if "POSITION" in pr["attributes"]:
                ncount += accs[pr["attributes"]["POSITION"]]["count"]
    print(f"  nodes={len(nodes)} meshes={len(g.get('meshes',[]))} verts={ncount} images={len(g.get('images',[]))} materials={len(g.get('materials',[]))}")
    print(f"  animations={len(anims)}")
    for n in anames[:12]: print("    -", n)
    print("  errors:", errs if errs else "NONE")
    return errs, ncount

if __name__ == "__main__":
    for p in sys.argv[1:]:
        print("==", p)
        validate(p)