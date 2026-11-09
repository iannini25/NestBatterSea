"""LOFT 4 Step inside, deterministic: only the camera moves.
Layers (key image space): R room plate, W window wall, T balcony things; E the final room (extended).
The room seen through the glass (the flight's drawing) is exchanged for the final room while the tree fills the frame."""
import os,sys,math,json,cv2,numpy as np
SP=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/inside3/l4v3/'
W_=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/'
OW,OH=1920,1080
PAD=320
def smooth(x):
    x=min(max(x,0.0),1.0); return x*x*x*(x*(6*x-15)+10)
class Sc: pass
def over(bg,col,al): return bg*(1-al)+col
def load():
    s=Sc(); s.TKS=np.load(SP+'H_K2S.npy')
    s.R=cv2.imread(SP+'R.png').astype(np.float32)
    F=cv2.imread(SP+'W.png',cv2.IMREAD_UNCHANGED).astype(np.float32); s.Wa=F[...,3:4]/255.; s.Wc=F[...,:3]*s.Wa
    F=cv2.imread(SP+'T.png',cv2.IMREAD_UNCHANGED).astype(np.float32); s.Ta=F[...,3:4]/255.; s.Tc=F[...,:3]*s.Ta
    E=cv2.imread(W_+'ai/gen/loft4-inside-final.png')[4:1516,:]
    # extended final room: plain continuation of walls, floor, ceiling beyond its frame (seen only during the entry)
    x=cv2.copyMakeBorder(E,PAD,PAD,PAD,PAD,cv2.BORDER_REPLICATE).astype(np.float32)
    # the continuation is smoothed along each edge (no streaks), the edge colours continue flat
    vb=cv2.GaussianBlur(x,(0,0),sigmaX=4,sigmaY=45); hb=cv2.GaussianBlur(x,(0,0),sigmaX=45,sigmaY=4)
    H_,W_x=x.shape[:2]
    yy,xx=np.mgrid[0:H_,0:W_x].astype(np.float32)
    dx=np.maximum.reduce([PAD-xx,xx-(W_x-PAD-1),np.zeros_like(xx)]); dy=np.maximum.reduce([PAD-yy,yy-(H_-PAD-1),np.zeros_like(yy)])
    w_=(dx/(dx+dy+1e-3))[...,None]; ins=((dx==0)&(dy==0))[...,None]
    x=np.where(ins,x,vb*w_+hb*(1-w_))
    # exact inside
    in_=np.zeros(x.shape[:2],np.float32); in_[PAD+14:-PAD-14,PAD+14:-PAD-14]=1; in_=cv2.GaussianBlur(in_,(0,0),3)[...,None]
    Ep=x.copy(); Ep[PAD:-PAD,PAD:-PAD]=E.astype(np.float32); x=x*(1-in_)+Ep*in_
    s.E=x.astype(np.float32)
    s.Eexact=cv2.resize(cv2.imread(W_+'ai/gen/loft4-inside-final.png')[4:1516,:],(OW,OH),interpolation=cv2.INTER_AREA)
    s.S=cv2.imread(W_+'inside3/out/loft4-flight-last-single.png')
    return s
class P:
    def __init__(p,**k):
        p.mend=1.30; p.zR=1.0; p.zW=0.21; p.zT=0.17; p.f=1600.; p.pT=(989.0,741.0); p.pW=(972.0,800.0)
        p.dof=1.2; p.rack=14.0; p.swap_tz=(0.112,0.157); p.N=271
        p.c=np.array([960.,540.]); p.__dict__.update(k)
        p.tzend=p.zR*(1-1/p.mend)
        from scipy.interpolate import PchipInterpolator as PI
        c=p.c
        T1=(np.array(p.pT)-c)*p.zT/p.f; T2=(np.array(p.pW)-c)*p.zW/p.f
        # one smooth lateral curve: passes the tree gap and the pane, and comes to rest at the end
        U=p.tzend; uT,uW=p.zT/U,p.zW/U
        pw=[2,3,5]; A=np.array([[uT**k for k in pw],[uW**k for k in pw],pw],float)
        cx=np.linalg.solve(A,[T1[0],T2[0],0]); cy=np.linalg.solve(A,[T1[1],T2[1],0])
        p.Tx=lambda z:float(sum(c*(z/U)**k for c,k in zip(cx,pw))); p.Ty=lambda z:float(sum(c*(z/U)**k for c,k in zip(cy,pw)))
        p.Eout=np.diag([OW/2688.,OH/1512.,1.0])
        p.fr=np.array([cam(p,i/(p.N-1)) for i in range(p.N)])
        p.tau_of=lambda z: float(np.interp(z,p.fr,np.arange(p.N)/(p.N-1)))
        p.swap=(p.tau_of(p.swap_tz[0]),p.tau_of(p.swap_tz[1]))
        d=(p.swap[1]-p.swap[0]); p.rk=(p.swap[0]-d*1.0,(p.swap[0]+p.swap[1])/2,p.swap[1]+d*0.9)
def cam(p,tau):
    # the camera follows ONE bell: log room scale eases in and out
    m=p.mend**smooth(tau); return p.zR*(1-1/m)
def hz(p,z,tz):
    d=z-tz if tz<z-1e-6 else 1e-6
    s=z/d
    Tx,Ty=float(p.Tx(min(tz,p.tzend))),float(p.Ty(min(tz,p.tzend)))
    b=[p.c[0]*(1-s)-p.f*Tx/d,p.c[1]*(1-s)-p.f*Ty/d]
    return np.array([[s,0,b[0]],[0,s,b[1]],[0,0,1.0]])
def blur(a,sigma):
    if sigma<0.4: return a
    if sigma>6:
        f=max(1,int(sigma/3))
        h,w=a.shape[:2]; sm=cv2.resize(a,(w//f,h//f),interpolation=cv2.INTER_AREA)
        sm=cv2.GaussianBlur(sm,(0,0),sigma/f); r=cv2.resize(sm,(w,h),interpolation=cv2.INTER_LINEAR)
        return r if r.ndim==a.ndim else r[...,None]
    r=cv2.GaussianBlur(a,(0,0),sigma); return r if r.ndim==a.ndim else r[...,None]
def layer(s,p,img_c,img_a,z,tz,H0):
    sc=z/(z-tz) if tz<z-1e-6 else 1e4
    H=hz(p,z,tz)@H0
    a=cv2.warpPerspective(img_a,H,(OW,OH),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    c=cv2.warpPerspective(img_c,H,(OW,OH),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    if a.ndim==2:a=a[...,None]
    a=np.clip(a,0,1)
    sg=min(p.dof*max(sc-1.0,0),45.0)
    a=blur(a,sg); c=blur(c,sg)
    return c,a,sc
def coverage(s,p,tau):
    tz=cam(p,tau)
    if tz>=p.zT: return 0.0
    H=np.diag([.25,.25,1.])@hz(p,p.zT,tz)@s.TKS
    a=cv2.warpPerspective(s.Ta,H,(480,270),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    sc=p.zT/(p.zT-tz); a=blur(a,min(p.dof*max(sc-1,0),45)/4)
    k=1-smooth((sc-12)/(40-12))
    return float(np.mean(a))*k
def render(s,p,tau):
    tz=cam(p,tau)
    room=cv2.warpPerspective(s.R,hz(p,p.zR,tz)@s.TKS,(OW,OH),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    a,b=p.swap
    w=smooth((tau-a)/(b-a)) if b>a else float(tau>=a)
    if w>1e-4:
        G=np.linalg.inv(hz(p,p.zR,p.tzend))@p.Eout@np.array([[1,0,-PAD],[0,1,-PAD],[0,0,1.0]])
        Er=cv2.warpPerspective(s.E,hz(p,p.zR,tz)@G,(OW,OH),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
        room=room*(1-w)+Er*w
    # focus: a very slow pull, rises and falls smoothly around the exchange
    r0,r1,r2=p.rk
    bp=smooth((tau-r0)/(r1-r0)) if tau<r1 else 1-smooth((tau-r1)/(r2-r1))
    if bp>1e-3: room=blur(room,p.rack*bp)
    out=room
    if tz<p.zW-1e-5:
        c,al,sc=layer(s,p,s.Wc,s.Wa,p.zW,tz,s.TKS)
        if sc<140: out=over(out,c,al)
    if tz<p.zT-1e-5:
        c,al,sc=layer(s,p,s.Tc,s.Ta,p.zT,tz,s.TKS)
        if sc<140: out=over(out,c,al)
    return out
def sheet(s,p,idx,name,cols=4,tile=(640,360)):
    sh=[]
    for i in idx:
        img=np.clip(render(s,p,i/(p.N-1))+.5,0,255).astype(np.uint8)
        im=cv2.resize(img,tile,interpolation=cv2.INTER_AREA); cv2.putText(im,str(i),(10,40),0,1.2,(0,255,255),3); sh.append(im)
    rows=[np.hstack(sh[j:j+cols]+[np.zeros((tile[1],tile[0],3),np.uint8)]*(cols-len(sh[j:j+cols]))) for j in range(0,len(sh),cols)]
    cv2.imwrite(SP+name,np.vstack(rows),[cv2.IMWRITE_JPEG_QUALITY,90])
if __name__=='__main__':
    s=load(); p=P(); p.N=205
    cov=np.zeros(p.N)
    pk=np.argmax(cov); print('coverage max',cov.max(),'at',pk, 'cov',np.round(cov[::15],2).tolist())
    tz=[cam(p,i/(p.N-1)) for i in range(p.N)]
    print('tz at frames',[round(tz[i],3) for i in range(0,205,20)],'zT',p.zT,'zW',p.zW)
    print('frame where tz>=zT',next(i for i,t in enumerate(tz) if t>=p.zT),'zW',next(i for i,t in enumerate(tz) if t>=p.zW))
    cs=np.convolve(cov,np.ones(11)/11,'same'); c=int(np.argmax(cs)); print('swap centre',c,'cov there',cs[c]); a=(c-6)/(p.N-1); b=(c+6)/(p.N-1); p.swap=(a,b); pk=c
    sheet(s,p,[0,20,40,60,70,80,90,100,110,120,130,140,160,180,204,204],'t3.jpg')
    sheet(s,p,list(range(max(pk-20,0),min(pk+24,204),4)),'t3b.jpg')
