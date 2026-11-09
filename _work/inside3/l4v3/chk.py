import sys,cv2,numpy as np
name=sys.argv[1]
exec(open('step.py',encoding='utf8').read().split("if __name__")[0])
c=cv2.VideoCapture(name); F=[]
while True:
    ok,f=c.read()
    if not ok:break
    F.append(cv2.resize(f,(960,540),interpolation=cv2.INTER_AREA).astype(np.float32))
N=len(F); d=np.array([np.abs(F[i+1]-F[i]).mean() for i in range(N-1)])
dd=np.abs(np.diff(d)); print('frames',N,'frame diff MAD every 10',np.round(d[::10],2).tolist())
print('largest diff jumps (frame,jump):',[(int(i),round(float(dd[i]),2)) for i in np.argsort(dd)[::-1][:6]])
p=P(N=N)
xs,ys=np.meshgrid(np.linspace(200,1720,9),np.linspace(150,930,6)); Pt=np.stack([xs.ravel(),ys.ravel(),np.ones(xs.size)])
def mot(z):
    H=[hz(p,z,cam(p,i/(N-1))) for i in range(N)]
    v=[]
    for i in range(N-1):
        if p.fr[i+1]>=z-1e-3: v.append(np.nan); continue
        M=H[i+1]@np.linalg.inv(H[i]); q=M@Pt; q=q[:2]/q[2]; v.append(float(np.mean(np.hypot(q[0]-Pt[0],q[1]-Pt[1]))))
    return np.array(v)
r=mot(1.0); print('room motion px/frame every 10:',np.round(r[::10],2).tolist()); print('room peak',round(float(np.nanmax(r)),2),'at',int(np.nanargmax(r)),'monotone rise then fall:',bool(np.all(np.diff(r[:int(np.nanargmax(r))])>=-1e-3) and np.all(np.diff(r[int(np.nanargmax(r)):])<=1e-3)))
