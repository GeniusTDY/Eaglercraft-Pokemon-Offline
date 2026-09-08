#!/usr/bin/env python3
"""软件渲染 Cobblemon/Bedrock 宝可梦 geo.json 模型，输出预览 PNG。
用于验证解析 & 生成可展示的渲染图。画家算法 + 纹理采样 + 简单兰伯特光照。"""
import json, math, os, sys
from PIL import Image

MAT_ID = lambda: [[1 if i==j else 0 for j in range(4)] for i in range(4)]
def mul(A,B):
    return [[sum(A[i][k]*B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def trans(tx,ty,tz):
    M=MAT_ID(); M[0][3]=tx; M[1][3]=ty; M[2][3]=tz; return M
def rotx(a): M=MAT_ID(); M[1][1]=M[2][2]=math.cos(a); M[1][2]=-math.sin(a); M[2][1]=math.sin(a); return M
def roty(a): M=MAT_ID(); M[0][0]=M[2][2]=math.cos(a); M[0][2]=math.sin(a); M[2][0]=-math.sin(a); return M
def rotz(a): M=MAT_ID(); M[0][0]=M[1][1]=math.cos(a); M[0][1]=-math.sin(a); M[1][0]=math.sin(a); return M
def apply(M,p):
    x,y,z=p
    return (M[0][0]*x+M[0][1]*y+M[0][2]*z+M[0][3],
            M[1][0]*x+M[1][1]*y+M[1][2]*z+M[1][3],
            M[2][0]*x+M[2][1]*y+M[2][2]*z+M[2][3])

def load_model(path):
    with open(path) as f: g=json.load(f)
    geo=g["minecraft:geometry"]
    if isinstance(geo,list): geo=geo[0]
    desc=geo.get("description",{})
    tex_w=desc.get("texture_width",64); tex_h=desc.get("texture_height",64)
    bones=geo["bones"]
    by={b["name"]:b for b in bones}
    return by, bones, tex_w, tex_h

def bone_matrix(bone, by, cache):
    """child pivot 相对父 pivot；根节点 pivot 绝对。"""
    parent=bone.get("parent")
    r=bone.get("rotation") or [0,0,0]
    p=bone.get("pivot") or [0,0,0]
    local=mul(mul(trans(*p),
                  mul(rotz(math.radians(r[2])), mul(roty(math.radians(r[1])), rotx(math.radians(r[0]))))),
              trans(-p[0],-p[1],-p[2]))
    if parent and parent in by:
        return mul(bone_matrix(by[parent], by, cache), local)
    return local

def cube_faces(origin, size, inflate, uv, tex_w, tex_h):
    """返回该 cube 的 6 个面：每面 (世界顶点列表, 纹理uv列表, 法线)。标准 blockbench 盒贴图。"""
    if inflate is None: inflate=0.0
    o=[origin[0]-inflate, origin[1]-inflate, origin[2]-inflate]
    s=[size[0]+2*inflate, size[1]+2*inflate, size[2]+2*inflate]
    u0,v0=uv
    sx,sy,sz=s
    #         顶点 (8 角)
    c=[(o[0],o[1],o[2]),(o[0]+sx,o[1],o[2]),(o[0]+sx,o[1],o[2]+sz),(o[0],o[1],o[2]+sz),
       (o[0],o[1]+sy,o[2]),(o[0]+sx,o[1]+sy,o[2]),(o[0]+sx,o[1]+sy,o[2]+sz),(o[0],o[1]+sy,o[2]+sz)]
    n=(0,1,-1); s_=(0,1,1); e=(1,0,0); w=(-1,0,0); u=(0,1,0); d=(0,-1,0)
    # (indices, face normal, [uv rect x0,y0,x1,y1 in pixels])
    down=[ [0,3,7,4], (0,-1,0),(u0+sx, v0, u0+sx+sz, v0+sz)]
    north=[ [0,1,5,4], (0,0,-1),(u0+sz+sx+sz, v0+sz, u0+sz+sx+sz+sx, v0+sz+sy)]
    east =[ [1,2,6,5], (1,0,0),(u0+sz+sx, v0+sz, u0+sz+sx+sz, v0+sz+sy)]
    south= [ [2,3,7,6],(0,0,1),(u0+sz, v0+sz, u0+sz+sx, v0+sz+sy)]
    west = [ [3,0,4,7],(-1,0,0),(u0, v0+sz, u0+sz, v0+sz+sy)]
    up   = [ [4,5,6,7],(0,1,0),(u0+sz, v0, u0+sz+sx, v0+sz)]
    for ids,normal,uvr in [up,north,east,south,west,down]:
        verts=[c[i] for i in ids]
        # uv 归一化 + 纹理空间翻转 v
        uvs=[( (uvr[0]+ (uvr[2]-uvr[0])*(i&1)), uvr[1]+(uvr[3]-uvr[1])*(1 if i&1 else 0) ) for i in range(4)]
        yield (verts,uvs,normal)

def render(species, out, size=640):
    base=os.path.join(os.path.dirname(__file__), "..", "web", "models")
    gp=os.path.join(base, species+".geo.json"); tp=os.path.join(base, species+".png")
    by, bones, tw, th = load_model(gp)
    tex=Image.open(tp).convert("RGBA"); tpx=tex.load()
    # 收集 world-space 三角面（每盒 12 三角）
    faces=[]
    cache={}
    for b in bones:
        M=bone_matrix(b, by, cache)
        for cube in (b.get("cubes") or []):
            for verts,uvs,n in cube_faces(cube["origin"], cube["size"], cube.get("inflate"), cube.get("uv"), tw, th):
                wv=[apply(M,v) for v in verts]
                faces.append((wv,uvs,n))
    # 计算模型世界包围盒，用于居中/归一
    xs=[v[0] for wv,_,_ in faces for v in wv]
    ys=[v[1] for wv,_,_ in faces for v in wv]
    zs=[v[2] for wv,_,_ in faces for v in wv]
    cx_=(min(xs)+max(xs))/2; cy_=(min(ys)+max(ys))/2; cz_=(min(zs)+max(zs))/2
    mx=max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)) or 1.0
    # 相机模型矩阵：平移到质心 → 均匀缩放(视口适配) → 旋转(俯角-25,自转30)
    zfit = 1.15 / mx
    def scaleM(k):
        return [[k,0,0,0],[0,k,0,0],[0,0,k,0],[0,0,0,1]]
    cam_mul=mul(mul(mul(roty(math.radians(30)), rotx(math.radians(-25))), scaleM(zfit)),
                trans(-cx_, -cy_, -cz_))
    cam=cam_mul
    fov=45
    f=1.0/math.tan(math.radians(fov/2.0))  # fov=45
    # 视空间坐标（已居中+缩放+旋转），z 即深度
    proj=[]
    for wv,uvs,n in faces:
        p3=[apply(cam, v) for v in wv]
        zs=[v[2] for v in p3]
        depth=sum(zs)/len(zs)
        proj.append((depth, wv, uvs, n, p3))
    proj.sort(key=lambda x:x[0], reverse=True)  # 远→近（z 大的远离相机则先画）
    img=Image.new("RGBA",(size,size),(0,0,0,255)); px=img.load()
    cx,cy=size/2,size/2
    # 像素缩放：模型视空间跨度约 ±0.6，让它占画面 ~70%
    view_span = 1.15
    px_per_unit = size*0.70/view_span
    def to_screen(v):
        x,y,z=v
        persp = 1.0/(1.0 + z*0.35)   # 轻微透视，z 越靠近立体感越强
        X=cx + x*px_per_unit*persp
        Y=cy - y*px_per_unit*persp
        return X,Y
    for depth, wv, uvs, n, p3 in proj:
        ndc=[to_screen(v) for v in p3]
        light = 0.35 + 0.65*abs(n[1])
        fill_poly(px, ndc, uvs, tpx, tw, th, depth, light, size)
    # DEBUG
    allxy=[to_screen(v) for wv,_,_,_,p3 in proj for v in p3]
    dbg_x=[p[0] for p in allxy]; dbg_y=[p[1] for p in allxy]
    print(f"  bbox: cx={cx_:.2f} cy={cy_:.2f} cz={cz_:.2f} span={mx:.2f}  screenX=[{min(dbg_x):.0f},{max(dbg_x):.0f}] screenY=[{min(dbg_y):.0f},{max(dbg_y):.0f}]")
    # 裁剪留白
    bbox=img.getbbox()
    if bbox:
        img=img.crop(bbox).resize((size,size), Image.NEAREST)
    img.save(out)
    print(f"{species}: faces={len(faces)} -> {out}")

def fill_poly(px, pts, uvs, tpx, tw, th, depth, light, size):
    # 扫描线填充凸多边形（四点），采样中心 uv
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    x0,x1=int(min(xs)),int(max(xs)); y0,y1=int(min(ys)),int(max(ys))
    W=H=size; x0=max(0,x0); y0=max(0,y0); x1=min(W-1,x1); y1=min(H-1,y1)
    for yy in range(y0,y1+1):
        for xx in range(x0,x1+1):
            if xx<0 or xx>=W or yy<0 or yy>=H: continue
            # 点在多边形内（4点凸包，近似简单测试）
            if point_in_quad(xx,yy,pts):
                # 中心 uv 采样
                uf=sum(v[0] for v in uvs)/4.0; vf=sum(v[1] for v in uvs)/4.0
                tx=int((uf % tw)); ty=int((vf % th))
                r,g,b,a=tpx[tx,ty]
                if a<10: continue
                rr=int(r*light); gg=int(g*light); bb=int(b*light)
                px[xx,yy]=(min(rr,255),min(gg,255),min(bb,255),255)

def point_in_quad(x,y,pts):
    def sign(a,b):
        return (a[0]-x)*(b[1]-y)-(b[0]-x)*(a[1]-y)
    pos=neg=0
    n=len(pts)
    for i in range(n):
        s=sign(pts[i],pts[(i+1)%n])
        if s>0: pos=1
        elif s<0: neg=1
        if pos and neg: return False
    return True

if __name__=="__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__),"..","web","models","_previews"), exist_ok=True)
    species=sys.argv[1:] or ["pikachu","charmander","squirtle","mewtwo","rayquaza","groudon","kyogre","arceus"]
    for s in species:
        out=os.path.join(os.path.dirname(__file__),"..","web","models","_previews",s+".png")
        render(s,out)