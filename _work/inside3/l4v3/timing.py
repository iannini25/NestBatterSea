exec(open('step.py',encoding='utf8').read().split("if __name__")[0])
import sys
CL=float(os.environ.get('CL','15000')); RM=700.0
def perceived(s,p,n=240,clip=None):
    # per-tz perceived image motion: median over the output of the rate of the layer each pixel shows
    tz=np.linspace(0,p.tzend-1e-4,n); dt=(p.tzend)/ (n*4)
    res=[]
    Sg=np.diag([.25,.25,1.])  # 480x270 grid
    xs,ys=np.meshgrid(np.arange(480)*4+2.0,np.arange(270)*4+2.0)
    P_=np.stack([xs.ravel(),ys.ravel(),np.ones(xs.size)])
    for t in tz:
        layers=[]
        for z,img in ((p.zT,s.Ta),(p.zW,s.Wa),(p.zR,None)):
            if t>=z-1e-4: continue
            H=hz(p,z,t)@s.TKS; H1=hz(p,z,min(t+dt,z-1e-5))@s.TKS
            Hd=np.linalg.inv(H)
            mot=H1@Hd@P_; mot=mot[:2]/mot[2]-P_[:2]
            rate=np.hypot(mot[0],mot[1]).reshape(xs.shape)/dt
            if img is None:
                a=np.ones_like(xs)
            else:
                a=cv2.warpPerspective(img,Sg@H,(480,270),flags=cv2.INTER_LINEAR)
                a=np.clip(a,0,1) if a.ndim==2 else a
            if z==p.zW and t>=p.zT: rate=np.minimum(rate,RM)          # after the tree the thin bars must not slow the room
            layers.append((a,rate))
        out=np.zeros_like(xs,dtype=np.float32); rem=np.ones_like(xs,dtype=np.float32)
        for a,r in layers:
            m=rem*(a>.5); out=np.where(m>0,r,out); rem=rem*(1-(a>.5)); 
        res.append(float(np.mean(np.minimum(out,CL))))
    return tz,np.array(res)
if __name__=='__main__':
    s=load(); p=P(); tz,v=perceived(s,p)
    np.save('tz_v.npy',np.stack([tz,v]))
    v=cv2.GaussianBlur(v.astype(np.float64)[None,:],(0,0),sigmaX=5,sigmaY=.01)[0]
    v=v+float(os.environ.get('BUMP','9000'))*np.exp(-((tz-.097)/.006)**2)   # time for the foliage to clear the lens
    np.save('tz_v.npy',np.stack([tz,v]))
    S=np.concatenate([[0],np.cumsum((v[1:]+v[:-1])/2*np.diff(tz))])
    print('v/1000 every 12',np.round(v[::12]/1000,2).tolist(),'total',int(S[-1]),'peak',round(1.875*S[-1]/204,1))
    f=lambda z:np.interp(z,tz,S)/S[-1]; print('frac tree exit',round(f(.1),3),'win exit',round(f(.14),3))
