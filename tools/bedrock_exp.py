#!/usr/bin/env python3
"""把 Cobblemon 的 Bedrock (.geo.json + .png + .animation.json) 转换为带动画的 .glb。

工作原理：
- 每个 geo 骨骼(bone) 变成一个 glTF 节点；bone.transform = T(pivot) R T(-pivot)
  等价于 glTF 节点: rotation=R, translation=pivot - R*pivot
- 每个 cube 合并为挂在该骨骼节点下的 Mesh 子节点（骨骼局部坐标），由 glTF 层级自动复合。
- 每个动画 clip 采样成 glTF animation（rotation quat + translation vec3 关键帧）。
  骨骼没被动画覆盖的通道保持 rest pose。
用法: python3 bedrock_to_glb.py <species_name> <geo.json> <texture.png> <anim.json...>
输出:  写入 species_name.glb 到当前目录
"""
import os, sys, json, struct, math

# 实验开关：翻转 X 轴旋转符号
FLIPX_BONE = os.environ.get("FLIPX_BONE") == "1"
FLIPX_CUBE = os.environ.get("FLIPX_CUBE") == "1"
# 只翻转尾巴子树骨骼的 X 旋转（祖先链包含 tail 的骨骼）
TAILX = os.environ.get("TAILX") == "1"


def in_tail_subtree(name, by):
    """name 的祖先链是否包含名为 tail 的骨骼。"""
    seen = set()
    while name in by and name not in seen:
        seen.add(name)
        if name == "tail":
            return True
        name = by[name].get("parent", "")
    return False


def flip_x_bone(name, b, by):
    if TAILX and in_tail_subtree(name, by):
        rng = b.get("rotation", [0, 0, 0])
        return [-rng[0], rng[1], rng[2]]
    if FLIPX_BONE:
        rng = b.get("rotation", [0, 0, 0])
        return [-rng[0], rng[1], rng[2]]
    return b.get("rotation", [0, 0, 0])

# ================= glTF/GLB 二进制写入器 =================
class GlbWriter:
    def __init__(self):
        self.nodes = []      # dict list
        self.meshes = []     # dict list
        self.accessors = []
        self.buffer_views = []
        self.images = []
        self.textures = []
        self.samplers = []
        self.materials = []
        self.animations = []
        self._bin = bytearray()
        self._buf_floats = b""
        self._pad = 0

    def add_bytes(self, data, target=None):
        """返回一个 bufferView，data 为 bytes，target 0=ARRAY_BUFFER. 对齐到 4。"""
        start = len(self._bin)
        self._bin += data
        while len(self._bin) % 4 != 0:
            self._bin += b"\x00"
        bv = {"buffer": 0, "byteOffset": start, "byteLength": len(data)}
        if target is not None:
            bv["target"] = target
        self.buffer_views.append(bv)
        return len(self.buffer_views) - 1

    def _f32(self, vals):
        return struct.pack("<%df" % len(vals), *vals)

    def add_attr(self, positions, uvs, normals):
        """把一组几何打包成一个 primitive 的 accessor 组，返回 dict。"""
        po = positions + uvs + normals
        byte_str = self._f32(po)
        pts = len(positions) // 3
        # 单独 bufferView 便于计算访问偏移
        part_data = self._f32(positions) + self._f32(uvs) + self._f32(normals)
        bv = self.add_bytes(part_data, target=0)
        # 三个 accessor 在同一 bufferView 的偏移
        off = 0
        count = len(self._f32(positions)) // 4 // 3
        # 偏移按字节算：我们先记录各部分字节去重
        # 简化：一次 add_bytes 放了三份数据，这里重新整数偏移
        start = self.buffer_views[bv]["byteOffset"]
        self.buffer_views[bv]["byteLength"] = len(part_data)
        acc_pos = self._mk_acc(bv, off, count, 5126, True, 3)
        off_uv = off + len(self._f32(positions))
        acc_uv = self._mk_acc(bv, off_uv, count, 5126, True, 2)
        off_n = off_uv + len(self._f32(uvs))
        acc_n = self._mk_acc(bv, off_n, count, 5126, True, 3)
        prim = {
            "attributes": {"POSITION": acc_pos, "TEXCOORD_0": acc_uv, "NORMAL": acc_n},
            "mode": 4,
            "material": 0,
        }
        return prim

    def _mk_acc(self, bv, byte_offset, count, comp, normalized, comp_type_count, maxv=None, minv=None):
        a = {
            "bufferView": bv,
            "byteOffset": byte_offset,
            "componentType": comp,
            "count": count,
            "type": ["SCALAR", "VEC2", "VEC3", "VEC4"][None or comp_type_count - 1],
        }
        if normalized:
            pass
        if maxv is not None:
            a["max"] = maxv
        if minv is not None:
            a["min"] = minv
        self.accessors.append(a)
        return len(self.accessors) - 1

    def to_glb(self):
        # scenes / scene
        scene_children = []
        sc_idx = 0
        # 找所有没有父节点的根骨骼
        # nodes 里已含 children；根节点 = 不在任何 children 列表里的
        children_set = set()
        for n in self.nodes:
            for c in n.get("children", []):
                children_set.add(c)
        roots = [i for i in range(len(self.nodes)) if i not in children_set]
        scene = {"nodes": roots}
        gltf = {
            "asset": {"version": "2.0", "generator": "bedrock_to_glb.py"},
            "scene": 0,
            "scenes": [scene],
            "scene_children": None,  # 占位，下面删
        }
        if self.nodes: gltf["nodes"] = self.nodes
        if self.meshes: gltf["meshes"] = self.meshes
        if self.accessors: gltf["accessors"] = self.accessors
        if self.buffer_views: gltf["bufferViews"] = self.buffer_views
        if self.images: gltf["images"] = self.images
        if self.textures: gltf["textures"] = self.textures
        if self.samplers: gltf["samplers"] = self.samplers
        if self.materials: gltf["materials"] = self.materials
        if self.animations: gltf["animations"] = self.animations
        gltf["buffers"] = [{"byteLength": len(self._bin)}]
        del gltf["scene_children"]

        gltf_json = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        while len(gltf_json) % 4 != 0:
            gltf_json += b" "
        while len(self._bin) % 4 != 0:
            self._bin += b"\x00"
        total = 12 + 8 + len(gltf_json) + 8 + len(self._bin)
        out = bytearray()
        out += struct.pack("<I", 0x46546C67)  # glTF magic
        out += struct.pack("<I", 2)
        out += struct.pack("<I", total)
        out += struct.pack("<I", len(gltf_json))
        out += struct.pack("<I", 0x4E4F534A)  # JSON
        out += gltf_json
        out += struct.pack("<I", len(self._bin))
        out += struct.pack("<I", 0x004E4942)  # BIN
        out += self._bin
        return bytes(out)


# ================= 数学 =================
def quat_from_euler(rx, ry, rz):
    """bedrock 旋转 (度,X,Y,Z) 按 Rz*Ry*Rx 叠加 -> 单位四元数 (x,y,z,w)。与 viewer 一致。"""
    cx = math.cos(math.radians(rx) / 2)
    cy = math.cos(math.radians(ry) / 2)
    cz = math.cos(math.radians(rz) / 2)
    sx = math.sin(math.radians(rx) / 2)
    sy = math.sin(math.radians(ry) / 2)
    sz = math.sin(math.radians(rz) / 2)
    # R = Rz * Ry * Rx (列向量，从 world->local 或点变换)
    # 四元数复合: q = (cos() ... ), 顺序 Rx then Ry then Rz applied to vector v => q = Rz*Ry*Rx (vector) 
    w = cx * cy * cz + sx * sy * sz
    x = sx * cy * cz - cx * sy * sz
    y = cx * sy * cz + sx * cy * sz
    z = cx * cy * sz - sx * sy * cz
    return (x, y, z, w)


def rot_apply_pt(rx, ry, rz, p):
    """R*p。R 与 quat_from_euler 严格一致：矩阵 R = Rz*Ry*Rx（点先绕 X 轴旋转）。

    用于求 translation = pivot - R*pivot。若旋转顺序与四元数不一致，
    多轴旋转骨骼的节点位置会被错误平移（如手指悬浮）。"""
    a, b, c = math.radians(rx), math.radians(ry), math.radians(rz)
    ca, sa = math.cos(a), math.sin(a)
    cb, sb = math.cos(b), math.sin(b)
    cc, sc = math.cos(c), math.sin(c)
    x, y, z = p
    # Rx（先绕 X）
    y1 = ca * y - sa * z
    z1 = sa * y + ca * z
    # Ry
    x2 = cb * x + sb * z1
    z2 = -sb * x + cb * z1
    # Rz
    x3 = cc * x2 - sc * y1
    y3 = sc * x2 + cc * y1
    return (x3, y3, z2)


# ================= 表达式求值 =================
class Parser:
    def __init__(self, s, t):
        self.s = s
        self.i = 0
        self.t = t

    def skip(self):
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def peek(self):
        self.skip()
        return self.s[self.i] if self.i < len(self.s) else ""

    def expr(self):
        v = self.term()
        while True:
            c = self.peek()
            if c == "+":
                self.i += 1
                v = v + self.term()
            elif c == "-":
                self.i += 1
                v = v - self.term()
            else:
                return v

    def term(self):
        v = self.factor()
        while True:
            c = self.peek()
            if c == "*":
                self.i += 1
                v = v * self.factor()
            elif c == "/":
                self.i += 1
                v = v / self.factor()
            else:
                return v

    def factor(self):
        c = self.peek()
        if c.isdigit() or c == ".":
            return self.number()
        if c == "(":
            self.i += 1
            v = self.expr()
            self.i += 1  # )
            return v
        if c == "-":
            self.i += 1
            return -self.factor()
        if c == "+":
            self.i += 1
            return self.factor()
        if c.isalpha():
            return self.word()
        raise ValueError("bad expr: %r" % self.s)

    def number(self):
        start = self.i
        while self.i < len(self.s) and (self.s[self.i].isdigit() or self.s[self.i] in ".-e"):
            if self.s[self.i] == "-" and self.i > start:
                break
            self.i += 1
        return float(self.s[start:self.i])

    def word(self):
        start = self.i
        while self.i < len(self.s) and (self.s[self.i].isalnum() or self.s[self.i] == "." or self.s[self.i] == "_"):
            self.i += 1
        w = self.s[start:self.i]
        if w == "q.anim_time" or w == "q.variant":
            return self.t
        if w in ("math.sin", "sin"):
            self.i += 1  # (
            v = self.expr()
            self.i += 1
            return math.sin(v)
        if w in ("math.cos", "cos"):
            self.i += 1  # (
            v = self.expr()
            self.i += 1
            return math.cos(v)
        # 未知 -> 0
        return 0.0


def comp_val(c, t):
    if isinstance(c, (int, float)):
        return float(c)
    p = Parser(str(c), t)
    return p.expr()


def chan_value(chan, t):
    """返回该 channel 在时间 t 的 [v1,v2,v3]."""
    if isinstance(chan, list):
        return [comp_val(c, t) for c in chan]
    if isinstance(chan, dict):
        items = []
        for k, v in chan.items():
            tv = float(k)
            if isinstance(v, dict):
                v = v.get("pre", v.get("post"))
            items.append((tv, v))
        items.sort()
        times = [x[0] for x in items]
        if t <= times[0]:
            return items[0][1]
        if t >= times[-1]:
            return items[-1][1]
        for i in range(len(items) - 1):
            t0, v0 = items[i]
            t1, v1 = items[i + 1]
            if t0 <= t <= t1:
                if t1 == t0:
                    return v0
                f = (t - t0) / (t1 - t0)
                return [v0[j] + (v1[j] - v0[j]) * f for j in range(3)]
    return [0.0, 0.0, 0.0]


# ================= Bedrock 模型解析 =================
def load_geo(path):
    g = json.load(open(path, encoding="utf-8"))
    geo = g["minecraft:geometry"]
    if isinstance(geo, list):
        geo = geo[0]
    desc = geo.get("description", {})
    texW = desc.get("texture_width", 64)
    texH = desc.get("texture_height", 64)
    bones = []
    by = {}
    for b in geo.get("bones", []):
        bones.append(b)
        by[b["name"]] = b
    return {"texW": texW, "texH": texH, "bones": bones, "by": by}


def build_cube_geometry(cube, texW, texH):
    """生成一个 cube 的 positions/uvs/normals (骨骼局部坐标)。"""
    ori = cube["origin"]
    size = cube["size"]
    Inf = cube.get("inflate", 0)
    ox = ori[0] - Inf; oy = ori[1] - Inf; oz = ori[2] - Inf
    sx = size[0] + 2 * Inf; sy = size[1] + 2 * Inf; sz = size[2] + 2 * Inf
    U = cube.get("uv", [0, 0])[0]
    V = cube.get("uv", [0, 0])[1]
    c = [
        [ox, oy, oz], [ox + sx, oy, oz], [ox + sx, oy, oz + sz], [ox, oy, oz + sz],
        [ox, oy + sy, oz], [ox + sx, oy + sy, oz], [ox + sx, oy + sy, oz + sz], [ox, oy + sy, oz + sz],
    ]
    # cube 自身 rotation（绕其 pivot）—— 与骨骼旋转同顺序
    cr = cube.get("rotation", [0, 0, 0])
    if FLIPX_CUBE:
        cr = [-cr[0], cr[1], cr[2]]
    if any(cr):
        piv = cube.get("pivot", [0, 0, 0])
        c = [
            list(rot_apply_pt(cr[0], cr[1], cr[2],
                              (p[0] - piv[0], p[1] - piv[1], p[2] - piv[2])))
            for p in c
        ]
        c = [[p[0] + piv[0], p[1] + piv[1], p[2] + piv[2]] for p in c]
    faces = [
        ([0, 1, 5, 4], [0, 0, -1], U + sz + sx + sz, V + sz, U + sz + sx + sz + sx, V + sz + sy),
        ([4, 5, 6, 7], [0, 1, 0],  U + sz, V + 0, U + sz + sx, V + sz),
        ([3, 7, 6, 2], [0, 0, 1],  U + sz, V + sz, U + sz + sx, V + sz + sy),
        ([1, 2, 6, 5], [1, 0, 0],  U + sz + sx, V + sz, U + sz + sx + sz, V + sz + sy),
        ([2, 3, 7, 6], [0, -1, 0], U + sx, V, U + sx + sz, V + sz),
        ([3, 0, 4, 7], [-1, 0, 0], U, V + sz, U + sz, V + sz + sy),
    ]
    pos = []
    uvs = []
    nrm = []
    for idx, n, u0, v0, u1, v1 in faces:
        a, b, d, e = c[idx[0]], c[idx[1]], c[idx[2]], c[idx[3]]
        tris = [(a, b, d), (a, d, e)]
        for (p0, p1, p2) in tris:
            pos += p0 + p1 + p2
            ux0 = u0 / texW; ux1 = u1 / texW
            vy0 = v0 / texH; vy1 = v1 / texH
            # 三.js: v=1 是图像顶部 => 用 1-y0 与 viewer 一致
            uvs += [ux0, 1 - vy0, ux1, 1 - vy0, ux1, 1 - vy1]
            uvs += [ux0, 1 - vy0, ux1, 1 - vy1, ux0, 1 - vy1]
            nrm += n + n + n
    return pos, uvs, nrm


# ================= 主转换 =================
def convert(species, geo_path, png_path, anim_paths, out_path, fps=24):
    mdl = load_geo(geo_path)
    texW, texH = mdl["texW"], mdl["texH"]
    by = mdl["by"]

    w = GlbWriter()
    # 材质 + 贴图
    with open(png_path, "rb") as f:
        image_bytes = f.read()
    im_idx = len(w.images)
    w.images.append({"uri": "__embedded__"})  # 占位，最后不保留 uri，改 bufferView
    w.images.pop()
    bv_img = w.add_bytes(image_bytes)
    w.images.append({"bufferView": bv_img, "mimeType": "image/png"})
    w.samplers.append({"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497})  # LINEAR, LINEAR_MIPMAP_LINEAR
    w.textures.append({"sampler": 0, "source": 0})
    w.materials.append({
        "name": species,
        "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0},
            "metallicFactor": 0.0,
            "roughnessFactor": 1.0,
        },
    })

    # 节点构建
    bone_names = list(by.keys())
    node_of = {}
    for name in bone_names:
        node_of[name] = len(w.nodes)
        w.nodes.append({"name": name, "children": []})

    # 每个 bone 的 cube mesh 作为子节点
    mesh_of_bone = {}
    for name, b in by.items():
        cubes = b.get("cubes")
        if not cubes:
            continue
        pos, uvs, nrm = [], [], []
        for c in cubes:
            p, u, n = build_cube_geometry(c, texW, texH)
            pos += p; uvs += u; nrm += n
        m_idx = len(w.meshes)
        w.meshes.append({"primitives": []})
        mesh_of_bone[name] = m_idx
        byte_str = make_f32(pos) + make_f32(uvs) + make_f32(nrm)
        bv = w.add_bytes(byte_str, target=0)
        cnt = len(pos) // 3
        acc_pos = w._mk_acc(bv, 0, cnt, 5126, None, 3,
                            maxv=_mx(pos, 3), minv=_mn(pos, 3))
        acc_uv = w._mk_acc(bv, _sz(pos), cnt, 5126, None, 2)
        acc_n = w._mk_acc(bv, _sz(pos) + _sz(uvs), cnt, 5126, None, 3)
        w.meshes[m_idx]["primitives"].append({
            "attributes": {"POSITION": acc_pos, "TEXCOORD_0": acc_uv, "NORMAL": acc_n},
            "mode": 4, "material": 0,
        })
        # 子节点
        cm_node = {"name": name + "_mesh", "mesh": m_idx}
        w.nodes.append(cm_node)
        w.nodes[node_of[name]]["children"].append(len(w.nodes) - 1)

    # 设置骨骼节点 rest TRS 与层级
    for name, b in by.items():
        ni = node_of[name]
        pivot = b.get("pivot", [0, 0, 0])
        rng = flip_x_bone(name, b, by)
        rx, ry, rz = rng
        q = quat_from_euler(rx, ry, rz)
        rp = rot_apply_pt(rx, ry, rz, pivot)
        t = [pivot[0] - rp[0], pivot[1] - rp[1], pivot[2] - rp[2]]
        w.nodes[ni]["rotation"] = list(q)
        w.nodes[ni]["translation"] = t
        if b.get("parent") in by:
            w.nodes[node_of[b["parent"]]]["children"].append(ni)

    # 动画
    for apath in anim_paths:
        adata = json.load(open(apath, encoding="utf-8"))
        clips = adata["animations"]
        for cname, cdef in clips.items():
            if not cdef.get("loop"):
                continue
            length = float(cdef.get("animation_length", 2.0))
            bones_anim = cdef.get("bones", {})
            if not bones_anim:
                continue
            n = int(round(length * fps)) + 1
            times = [i / fps for i in range(n)]
            # 收集此 clip 需要动画的骨骼
            anim_bones = [bn for bn in bones_anim.keys() if bn in by]
            # 对每个 sample 计算每个 animated bone 的最新 euler/pos
            # glTF animation：每 node/每 path 一个 channel+sampler
            channels = []
            samplers = []
            # 统一 input: times
            in_bv = w.add_bytes(make_f32(times))
            acc_in = w._mk_acc(in_bv, 0, len(times), 5126, None, 1)
            for bn in anim_bones:
                b = by[bn]
                pivot = b.get("pivot", [0, 0, 0])
                rot_chan = bones_anim[bn].get("rotation")
                pos_chan = bones_anim[bn].get("position")
                has_rot = rot_chan is not None
                has_pos = pos_chan is not None
                # rest base
                rest_r = b.get("rotation", [0, 0, 0])
                rest_q = quat_from_euler(*rest_r)
                rest_rp = rot_apply_pt(*rest_r, pivot)
                rest_t = [pivot[0] - rest_rp[0], pivot[1] - rest_rp[1], pivot[2] - rest_rp[2]]
                # 采样
                rot_out = []
                t_out = []
                for t in times:
                    if has_rot:
                        rr = chan_value(rot_chan, t)
                    else:
                        rr = rest_r
                    R = rot_apply_pt(rr[0], rr[1], rr[2], pivot)
                    tt = [pivot[0] - R[0], pivot[1] - R[1], pivot[2] - R[2]]
                    if has_pos:
                        d = chan_value(pos_chan, t)
                        tt = [tt[0] + d[0], tt[1] + d[1], tt[2] + d[2]]
                    q = quat_from_euler(rr[0], rr[1], rr[2])
                    rot_out += list(q)
                    t_out += tt
                # 如果既有 rot 又没 pos，也要输出 rotation path + translation(rest? 不，用 animated rot 的 translation)
                # 输出 rotation channel
                node_idx = node_of[bn]
                out_bv = w.add_bytes(make_f32(rot_out))
                acc_out = w._mk_acc(out_bv, 0, len(rot_out) // 4, 5126, None, 4)
                s_idx = len(samplers)
                samplers.append({"input": acc_in, "output": acc_out, "interpolation": "LINEAR"})
                channels.append({"sampler": s_idx, "target": {"node": node_idx, "path": "rotation"}})
                # translation channel
                out_bv2 = w.add_bytes(make_f32(t_out))
                acc_t = w._mk_acc(out_bv2, 0, len(t_out) // 3, 5126, None, 3)
                s_idx2 = len(samplers)
                samplers.append({"input": acc_in, "output": acc_t, "interpolation": "LINEAR"})
                channels.append({"sampler": s_idx2, "target": {"node": node_idx, "path": "translation"}})
            if channels:
                w.animations.append({"name": cname, "channels": channels, "samplers": samplers})

    data = w.to_glb()
    with open(out_path, "wb") as f:
        f.write(data)
    print("wrote", out_path, len(data), "bytes,", len(w.animations), "clips")


def p_f32(vals):
    return struct.pack("<%df" % len(vals), *vals)


make_f32 = p_f32


def _sz(a):
    return len(a) * 4


def _mx(a, n):
    m = []
    for i in range(n):
        m.append(max(a[j] for j in range(i, len(a), n)))
    return m


def _mn(a, n):
    m = []
    for i in range(n):
        m.append(min(a[j] for j in range(i, len(a), n)))
    return m


if __name__ == "__main__":
    # args: species geo png anim... --out out
    argv = sys.argv[1:]
    out = None
    if "--out" in argv:
        k = argv.index("--out")
        out = argv[k + 1]
        argv = argv[:k] + argv[k + 2:]
    species = argv[0]
    geo = argv[1]
    png = argv[2]
    anims = argv[3:]
    if not out:
        out = species + ".glb"
    convert(species, geo, png, anims, out)