import json, subprocess, math, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
pf="/home/claude/patternforge/target/release/pf"
def call(req):
    r=subprocess.run([pf,"call"],input=json.dumps(req),capture_output=True,text=True); return json.loads(r.stdout)
cols={"Front Bodice":"#2f7d6d","Back Bodice":"#c46a3a","Sleeve":"#4b6fb5","Front Skirt":"#2f7d6d","Back Skirt":"#c46a3a","Front Trouser":"#2f7d6d","Back Trouser":"#c46a3a"}
gs=sys.argv[1:] or ["bodice","skirt","trousers"]
fig,axes=plt.subplots(len(gs),3,figsize=(13,5.2*len(gs)),squeeze=False)
for r,g in enumerate(gs):
    pat=call({"op":"draft","garment":g})["pattern"]
    d=call({"op":"drape","pattern":pat})
    s=d["stats"]; print(g,{k:round(v,2) if isinstance(v,float) else v for k,v in s.items()})
    allpts=[]
    for m in d["meshes"]:
        f=m["frames"][-1]; allpts+= [f[i+1] for i in range(0,len(f),3)]
    ylo,yhi=min(allpts)-5,max(allpts)+5
    for c,(name,ix,iy) in enumerate([("front (x,y)",0,1),("side (z,y)",2,1),("top (x,z)",0,2)]):
        ax=axes[r][c]
        if iy==1:
            for col in [d["body"]["torso"]]+d["body"]["legs"]+d["body"]["arms"]:
                key="a" if ix==0 else "b"; ctr=col["cx"] if ix==0 else col["cz"]
                ax.plot([ctr+v for v in col[key]],col["ys"],color="#aaa",lw=1); ax.plot([ctr-v for v in col[key]],col["ys"],color="#aaa",lw=1)
        for m in d["meshes"]:
            f=m["frames"][-1]; pts=[(f[i],f[i+1],f[i+2]) for i in range(0,len(f),3)]
            ax.scatter([p[ix] for p in pts],[p[iy] for p in pts],s=3,color=cols.get(m["name"],"#777"),alpha=0.6)
        ax.set_aspect("equal"); ax.set_title(f"{g} — {name}")
        if iy==1: ax.set_ylim(ylo,yhi)
plt.tight_layout(); plt.savefig("/tmp/e2e/drape.png",dpi=55)
