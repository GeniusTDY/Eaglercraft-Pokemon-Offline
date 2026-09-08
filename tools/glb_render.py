#!/usr/bin/env python3
"""从 bedrock_to_glb.py 生成的 .glb 软件渲染预览 PNG（rest 姿态）。
验证 gltf 节点层级、网格、UV、贴图正确性（无 WebGL 环境）。"""
import json, struct, sys, math
from io import BytesIO
from PIL import Image

def read_glb(path):
    with open(path,'rb') as f: data=f.read()
    off=12; j=None; b=None
    while off<len(data):
        ln,typ=struct.unpack('<II',data[off:off+8])
        chunk=data[off+8:off+8+ln]
        if typ==0x4E4F534A: j=json.loads(chunk)
        elif typ==0x004E4942: b=chunk
        off+=8+ln
    return j,b

def acc_data(j,b,ai):
    a=j['accessors'][ai]; bv=j['bufferViews'][a['bufferView']]
    start=bv['byteOffset']+a.get('byteOffset',0)
    ct={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]*4
    comp={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    n=a['count']
    raw=b[start:start+n*ct]
    return [struct.unpack_from('<f',raw,4*i)[0] for i in range(n*comp)], comp

def mat_id(): return [[1 if i==j else 0 for j in range(4)] for i in range(4)]
def mul(A,B): return [[sum(A[i][k]*B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def apply(M,p):
    x,y,z=p
    return (M[0][0]*x+M[0][1]*y+M[0][2]*z+M[0][3],
            M[1][0]*x+M[1][1]*y+M[1][2]*z+M[1][3],
            M[2][0]*x+M[2][1]*y+M[2][2]*z+M[2][3])
def rot_m(q):
    x,y,z,w=q
    xx,yy,zz=x*x,y*y,z*z
    xy,xz,yz=x*y,x*z,y*z
    wx,wy,wz=w*x,w*y,w*z
    return [[1-2*(yy+zz),2*(xy-wz),2*(xz+wy),0],
            [2*(xy+wz),1-2*(xx+zz),2*(yz-wx),0],
            [2*(xz-wy),2*(yz+wx),1-2*(xx+yy),0],
            [0,0,0,1]]
def trans_m(t):
    M=mat_id(); M[0][3],M[1][3],M[2][3]=t; return M

def point_in_quad(x,y,pts):
    def sign(a,b): return (a[0]-x)*(b[1]-y)-(b[0]-x)*(a[1]-y)
    pos=neg=0
    for i in range(len(pts)):
        s=sign(pts[i],pts[(i+1)%len(pts)])
        if s>0: pos=1
        elif s<0: neg=1
        if pos and neg: return False
    return True

def render(path, out, size=640):
    j,b=read_glb(path)
    # 贴图
    img0=j['images'][0]
    bv=j['bufferViews'][img0['bufferView']]
    png=b[bv['byteOffset']:bv['byteOffset']+bv['byteLength']]
    tex=Image.open(BytesIO(png)).convert('RGBA'); tw,th=tex.size; tpx=tex.load()
    # nodes world matrices
    nodes=j['nodes']; children_of={}
    for i,n in enumerate(nodes):
        children_of[i]=n.get('children',[])
    # compute world
    def local(i):
        n=nodes[i]
        q=n.get('rotation',[0,0,0,1]); t=n.get('translation',[0,0,0]); s=n.get('scale',[1,1,1])
        M=trans_m(t); R=rot_m([q[0]*s[0],q[1]*s[1],q[2]*s[2],q[3]]); 
        # T*R*S
        R[0][0]*=s[0]; R[0][1]*=s[0]; R[0][2]*=s[0]
        R[1][0]*=s[1]; R[1][1]*=s[1]; R[1][2]*=s[1]
        R[2][0]*=s[2]; R[2][1]*=s[2]; R[2][2]*=s[2]
        return mul(M,R)
    world={}
    def comp(i,parent):
        world[i]=mul(parent,local(i))
        for c in children_of[i]: comp(c,world[i])
    roots=[i for i in range(len(nodes)) if i not in {c for cs in children_of.values() for c in cs}]
    for r in roots: comp(r,mat_id())
    # meshes
    meshes=j['meshes']
    faces=[]
    maxv=[]
    for mi,m in enumerate(meshes):
        pr=m['primitives'][0]
        pos=list(acc_data(j,b,pr['attributes']['POSITION']))
        uv=list(acc_data(j,b,pr['attributes']['TEXCOORD_0']))
        nrm=list(acc_data(j,b,pr['attributes']['NORMAL']))
        P,V,Pc=pos[0],uv[0],pos[1]
        # 找这个 mesh 挂的 node
        owner=[i for i,n in enumerate(nodes) if n.get('mesh')==mi][0]
        M=world[owner]
        tri_count=len(P)//9
        for ti in range(tri_count):
            tri=[]
            for k in range(3):
                base=(ti*3+k)
                vert=(P[base*3],P[base*3+1],P[base*3+2])
                wv=apply(M,vert)
                uu, vv= V[base*2], V[base*2+1]
                tri.append((wv,uu,vv))
            faces.append(tri)
    # 包围盒
    xs=[wv[0] for tri in faces for (wv,uu,vv) in tri]
    ys=[wv[1] for tri in faces for (wv,uu,vv) in tri]
    zs=[wv[2] for tri in faces for (wv,uu,vv) in tri]
    cx_=(min(xs)+max(xs))/2; cy_=(min(ys)+max(ys))/2; cz_=(min(zs)+max(zs))/2
    mx_=max(max(xs)-min(xs),max(ys)-min(ys),max(zs)-min(zs)) or 1.0
    print(f"  vertices(裸) span={mx_:.1f} center=({cx_:.1f},{cy_:.1f},{cz_:.1f})")
    # 相机
    zfit=1.15/mx_
    def scaleM(k): return [[k,0,0,0],[0,k,0,0],[0,0,k,0],[0,0,0,1]]
    def roty(a):
        M=mat_id(); c=math.cos(a); s=math.sin(a); M[0][0]=M[2][2]=c; M[0][2]=s; M[2][0]=-s; return M
    def rotx(a):
        M=mat_id(); c=math.cos(a); s=math.sin(a); M[1][1]=M[2][2]=c; M[1][2]=-s; M[2][1]=s; return M
    cam=mul(mul(mul(roty(math.radians(30)),rotx(math.radians(-25))),scaleM(zfit)),trans_m((-cx_,-cy_,-cz_)))
    proj=[]
    for tri in faces:
        p3=[apply(cam,t[0]) for t in tri]
        depth=sum(v[2] for v in p3)/3
        proj.append((depth,tri,p3))
    proj.sort(key=lambda x:x[0], reverse=True)
    img=Image.new('RGBA',(size,size),(0,0,0,255)); px=img.load()
    cx=cy=size/2; pop=size*0.70/1.15
    def to_screen(v):
        x,y,z=v; persp=1.0/(1.0+z*0.35)
        return cx+x*pop*persp, cy - y*pop*persp
    for depth,tri,p3 in proj:
        ndc=[to_screen(v) for v in p3]
        uvs=[(t[1],t[2]) for t in tri]
        # 平均法线：用三角顶点决定光照，简化用 y 分量（俯视）
        light=0.35+0.65*abs(0.8)
        # 采样中心 uv
        uf=sum(u for u,v in uvs)/3; vf=sum(v for u,v in uvs)/3
        tx=int(((uf%1.0)*tw)); ty=int((((1-vf)%1.0)*th))
        tx=max(0,min(tw-1,tx)); ty=max(0,min(th-1,ty))
        r,g,gg,a=tpx[tx,ty]
        if a<10: continue
        rr=int(r*light); ggg=int(g*light); bb=int(gg*light)
        # 扫描线填三角
        xv=[p[0] for p in ndc]; yv=[p[1] for p in ndc]
        x0,x1=int(min(xv)),int(max(xv)); y0,y1=int(min(yv)),int(max(yv))
        x0,y0=max(0,x0),max(0,y0); x1,y1=min(size-1,x1),min(size-1,y1)
        for yy in range(y0,y1+1):
            for xx in range(x0,x1+1):
                if point_in_quad(xx,yy,ndc):
                    px[xx,yy]=(min(rr,255),min(ggg,255),min(bb,255),255)
    bbox=img.getbbox()
    if bbox: img=img.crop(bbox).resize((size,size),Image.NEAREST)
    img.save(out)
    print(f"  {math.floor(len(faces)/3)} faces -> {out}")

if __name__=='__main__':
    for p in sys.argv[1:]:
        out=p.replace('.glb','_glb.png')
        print('==',p); render(p,out)