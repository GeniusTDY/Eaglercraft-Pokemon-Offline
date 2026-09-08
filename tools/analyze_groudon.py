#!/usr/bin/env python3
"""分析固拉多 GLB：列出每个带 mesh 的骨骼在世界空间的包围盒，定位漂浮碎片。"""
import json, struct, sys, math

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
    comp={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    n=a['count']
    raw=b[start:start+n*comp*4]
    return [struct.unpack_from('<f',raw,4*i)[0] for i in range(n*comp)]

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

def local(i,nodes):
    n=nodes[i]
    q=n.get('rotation',[0,0,0,1]); t=n.get('translation',[0,0,0]); s=n.get('scale',[1,1,1])
    M=trans_m(t); R=rot_m([q[0]*s[0],q[1]*s[1],q[2]*s[2],q[3]])
    R[0][0]*=s[0]; R[0][1]*=s[0]; R[0][2]*=s[0]
    R[1][0]*=s[1]; R[1][1]*=s[1]; R[1][2]*=s[1]
    R[2][0]*=s[2]; R[2][1]*=s[2]; R[2][2]*=s[2]
    return mul(M,R)

def main(path):
    j,b=read_glb(path)
    nodes=j['nodes']
    children_of={i:n.get('children',[]) for i,n in enumerate(nodes)}
    world={}
    def comp(i,parent):
        world[i]=mul(parent,local(i,nodes))
        for c in children_of[i]: comp(c,world[i])
    roots=[i for i in range(len(nodes)) if i not in {c for cs in children_of.values() for c in cs}]
    for r in roots: comp(r,mat_id())
    meshes=j['meshes']
    print(f"{'bone':<22} {'minx':>7} {'miny':>7} {'minz':>7} {'maxx':>7} {'maxy':>7} {'maxz':>7} {'span':>6}  cx cy cz")
    allmin=[1e9]*3; allmax=[-1e9]*3
    for mi,m in enumerate(meshes):
        pr=m['primitives'][0]
        pos=acc_data(j,b,pr['attributes']['POSITION'])
        owner=[i for i,n in enumerate(nodes) if n.get('mesh')==mi][0]
        M=world[owner]
        name=nodes[owner].get('name','?')
        pts=[apply(M,(pos[3*i],pos[3*i+1],pos[3*i+2])) for i in range(len(pos)//3)]
        mn=[min(p[k] for p in pts) for k in range(3)]
        mx=[max(p[k] for p in pts) for k in range(3)]
        span=max(mx[k]-mn[k] for k in range(3))
        cx,cy,cz=(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2
        print(f"{name:<22} {mn[0]:7.1f} {mn[1]:7.1f} {mn[2]:7.1f} {mx[0]:7.1f} {mx[1]:7.1f} {mx[2]:7.1f} {span:6.1f}  {cx:5.1f} {cy:5.1f} {cz:5.1f}")
        for k in range(3):
            allmin[k]=min(allmin[k],mn[k]); allmax[k]=max(allmax[k],mx[k])
    print(f"\nTOTAL bbox: min={allmin} max={allmax}")
    model_cx=(allmin[0]+allmax[0])/2
    # 找出几何中心偏离模型中心 > 25 的骨骼（漂浮碎片候选）
    print("\n远离主体的骨骼:")
    for mi,m in enumerate(meshes):
        pr=m['primitives'][0]
        pos=acc_data(j,b,pr['attributes']['POSITION'])
        owner=[i for i,n in enumerate(nodes) if n.get('mesh')==mi][0]
        M=world[owner]
        name=nodes[owner].get('name','?')
        pts=[apply(M,(pos[3*i],pos[3*i+1],pos[3*i+2])) for i in range(len(pos)//3)]
        cx=sum(p[0] for p in pts)/len(pts)
        if abs(cx-model_cx)>25:
            print(f"  {name}: 几何中心x={cx:.1f} (模型中心x={model_cx:.1f})")

if __name__=='__main__':
    main(sys.argv[1])
