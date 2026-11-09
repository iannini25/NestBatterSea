"""Final layers: R room plate (extended), W window wall RGBA, T balcony RGBA, exact recomposition to K."""
import cv2,numpy as np
SP=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/inside3/l4v3/'
W_=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/'
K=cv2.imread(W_+'ai/gen/loft4-end-gpt.png').astype(np.float32)
Z=np.load(SP+'mattes.npz'); d=Z['d']; Bg=Z['Bg']; mull=(Z['mull']>0.5).astype(np.uint8); aW0=Z['aW']; aT=np.load(SP+'aT.npy')
h,w=K.shape[:2]
# room layer: K where the room is seen directly, the (flow aligned, colour matched) clean plate behind foreground
hide=((aT>0.04)|(mull>0)|(aW0>0.04)).astype(np.uint8)
# bars: the room behind a bar is its own pixels from either side (thin, so nothing is invented)
colm=np.zeros((h,w),np.uint8); colm[:,np.nonzero(mull[300:880].any(0))[0]]=1; colm[:264]=0; colm[1336:]=0
barV=cv2.dilate(colm,np.ones((1,3),np.uint8)).astype(bool)
Ks=np.where((aT[...,None]>0.04),Bg,K)      # samples beside a bar never take a leaf
Kb=Ks.copy()
for y in range(264,1336):
    xs=np.nonzero(barV[y])[0]
    if not len(xs): continue
    for r in np.split(xs,np.nonzero(np.diff(xs)>1)[0]+1):
        if len(r)>40: continue
        a_,b_=r[0],r[-1]
        L_=Ks[y,max(a_-4,0):a_-1].mean(0); R_=Ks[y,b_+2:b_+5].mean(0)
        for x in r: Kb[y,x]=L_+(R_-L_)*(x-a_+1)/(b_-a_+2)
rows=np.arange(903,948)                                # the transom assembly band
for x in range(652,1940):
    a_,b_=rows[0],rows[-1]
    L_=Kb[a_-5:a_-1,x].mean(0); R_=Kb[b_+2:b_+6,x].mean(0)
    for y in rows: Kb[y,x]=L_+(R_-L_)*(y-a_+1)/(b_-a_+2)
# the head of the glass: its shadow belongs to the window wall; the room above it is its ceiling
for x in range(652,1940):
    Kb[262:288,x]=np.median(Kb[300:330,max(x-12,0):x+12].reshape(-1,3),axis=0)
hide_tree=((aT>0.04)).astype(np.uint8)
hide=cv2.dilate(hide,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)))
zr=cv2.GaussianBlur(cv2.dilate(hide_tree,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7))).astype(np.float32),(0,0),2.0)[...,None]
# gain of the clean plate towards K measured on the room only (never through the foreground)
vis=(1-cv2.dilate(hide,np.ones((15,15),np.uint8)).astype(np.float32))[...,None]; vis[:264]=0; vis[1336:]=0; vis[:,:652]=0; vis[:,1940:]=0
Bal=Z['Bal']
num=cv2.GaussianBlur(K*vis,(0,0),25); den=cv2.GaussianBlur(Bal*vis,(0,0),25); wv=cv2.GaussianBlur(vis,(0,0),25)[...,None]
gain=np.where(wv>0.03,(num/np.maximum(wv,1e-3)+1)/(den/np.maximum(wv,1e-3)+1),1.0); gain=np.clip(gain,0.82,1.2)
gain=cv2.GaussianBlur(gain,(0,0),18)
Bg=Bal*gain
R=Kb*(1-zr)+Bg*zr
# outside the glass: continue the room's own edges (plain ceiling, walls, floor)
X0,X1,Y0,Y1=652,1940,264,1336
m=8
box=R[Y0+m:Y1-m,X0+m:X1-m]
# plain continuation: edge bands blurred along the edge (ceiling, walls, floor have no structure worth keeping)
# plain continuation of the room beyond the glass from the bands just inside the glass edge, smoothed along the edge
def edge_ext():
    Tb=np.percentile(R[Y0+24:Y0+62,X0+m:X1-m],80,axis=0,keepdims=True); Bb=np.percentile(R[Y1-70:Y1-30,X0+m:X1-m],55,axis=0,keepdims=True)
    Tb=cv2.GaussianBlur(Tb,(0,0),sigmaX=90,sigmaY=.5); Bb=cv2.GaussianBlur(Bb,(0,0),sigmaX=90,sigmaY=.5)
    Lb=np.percentile(R[Y0+m:Y1-m,X0+20:X0+200],85,axis=1,keepdims=True)
    Lb=cv2.GaussianBlur(Lb,(0,0),sigmaX=.5,sigmaY=120); Rb=Lb.copy()
    ext_h=np.zeros((h,w,3),np.float32); ext_v=np.zeros((h,w,3),np.float32)
    for yy_ in range(h):
        k=min(max(yy_-(Y0+m),0),Lb.shape[0]-1)
        ext_h[yy_,:X0]=Lb[k,0]; ext_h[yy_,X1:]=Rb[k,0]
    for xx_ in range(w):
        k=min(max(xx_-(X0+m),0),Tb.shape[1]-1)
        ext_v[:Y0,xx_]=Tb[0,k]; ext_v[Y1:,xx_]=Bb[0,k]
    return ext_h,ext_v
yy_g,xx_g=np.mgrid[0:h,0:w].astype(np.float32)
ext_h,ext_v=edge_ext()
dxo=np.maximum.reduce([X0-xx_g,xx_g-(X1-1),np.zeros((h,w),np.float32)]); dyo=np.maximum.reduce([Y0-yy_g,yy_g-(Y1-1),np.zeros((h,w),np.float32)])
wh=(dxo/(dxo+dyo+1e-3))[...,None]
ext=ext_h*wh+ext_v*(1-wh)
ext[Y0:Y1,X0:X1]=R[Y0:Y1,X0:X1]
ext=cv2.GaussianBlur(ext,(0,0),3)

inner=np.zeros((h,w),np.float32); inner[Y0+4:Y1-4,X0+4:X1-4]=1; inner=cv2.GaussianBlur(inner,(0,0),3)[...,None]
Rx=R*inner+ext*(1-inner)
# window wall: a mullion hidden behind tree pixels takes the column's mullion colour
Wc=K.copy()
# the glass head (frame reveal) belongs to the window wall
aW0=aW0.copy(); aW0[264:280,X0:X1]=1.0
col_mull=np.nonzero(mull[300,:])[0]
tree=aT>0.05
for x in np.nonzero(mull[300:900,:].any(0))[0]:
    ys=np.nonzero(mull[:,x]>0)[0]
    if len(ys)<50: continue
    clear=ys[~tree[ys,x]]
    med=np.median(K[clear,x],axis=0) if len(clear)>20 else np.array([60,60,70.])
    y2=ys[tree[ys,x]]
    Wc[y2,x]=med
for y in np.nonzero(mull[:,1200:1800].any(1))[0]:
    xs=np.nonzero(mull[y,:]>0)[0]
    if len(xs)<100: continue
    clear=xs[~tree[y,xs]]
    med=np.median(K[y,clear],axis=0) if len(clear)>20 else np.array([60,60,70.])
    x2=xs[tree[y,xs]]; Wc[y,x2]=med
# bars plain: pixels of the bar that differ from it (leaves, branches crossing) go to T, exact
bar=np.zeros((h,w),np.float32)
for x in np.nonzero(mull[300:900,:].any(0))[0]:
    ys=np.nonzero(mull[:,x]>0)[0]
    if len(ys)<50: continue
    med=np.median(K[ys,x],axis=0); Wc[ys,x]=med
    bar[ys,x]=(np.abs(K[ys,x]-med).max(1)>22).astype(np.float32)
for y in np.nonzero(mull[:,1200:1800].any(1))[0]:
    xs=np.nonzero(mull[y,:]>0)[0]
    if len(xs)<100: continue
    med=np.median(K[y,xs],axis=0); df=(np.abs(K[y,xs]-med).max(1)>22)
    tree_=tree[y,xs]
    Wc[y,xs[tree_|df]]=med
    bar[y,xs[df]]=1
bar=cv2.morphologyEx(bar,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
nearT=cv2.dilate((aT>0.25).astype(np.uint8),np.ones((13,13),np.uint8)).astype(np.float32)
bar=bar*nearT
aT=np.maximum(aT,cv2.GaussianBlur(bar,(0,0),0.6))
n,lb,st,_=cv2.connectedComponentsWithStats((aT>0.2).astype(np.uint8),8)
keep=(st[:,cv2.CC_STAT_AREA]>2500); keep[0]=False
aT=aT*cv2.GaussianBlur(cv2.dilate(keep[lb].astype(np.uint8),np.ones((5,5),np.uint8)).astype(np.float32),(0,0),1)
Fw=np.where(aW0[...,None]>0.02,(K-(1-aW0[...,None])*Rx)/np.maximum(aW0[...,None],0.02),Wc)
Fw=np.where(mull[...,None]>0,Wc,Fw)
# bar edges: never the leaf or room pixels mixed into them, the bar's own colour reaches its soft edge
_,lab_=cv2.distanceTransformWithLabels((mull==0).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
ly,lx=np.nonzero(mull>0); mp=np.zeros(lab_.max()+1,int); mp[lab_[ly,lx]]=np.arange(len(ly))
idx=mp[lab_]
edge=(mull==0)&(aW0>0.02)&(xx_g>=X0-2)&(xx_g<X1+2)&(yy_g>=Y0+18)&(yy_g<Y1-2)
Fw[edge]=Wc[ly[idx[edge]],lx[idx[edge]]]
# transom: leaf mottling smoothed along its length, its horizontal lines kept
band=Fw[903:948,X0:X1].copy()
Fw[903:948,X0:X1]=cv2.GaussianBlur(band,(0,0),sigmaX=16,sigmaY=0.01)
Fw=np.clip(Fw,0,255)
# mullions: colour smoothed along each bar so nothing mottles when they pass the lens (width and edges unchanged)
for r0_,r1_ in ((Y0+18,903),(948,Y1-2)):
    Fw[r0_:r1_,X0:X1]=cv2.GaussianBlur(Fw[r0_:r1_,X0:X1],(0,0),sigmaX=0.01,sigmaY=45,borderType=cv2.BORDER_REPLICATE)
C=aW0[...,None]*Fw+(1-aW0[...,None])*Rx
Ft=np.where(aT[...,None]>0.02,(K-(1-aT[...,None])*C)/np.maximum(aT[...,None],0.02),K); Ft=np.clip(Ft,0,255)
Ft[1144:1147,640:2052]=np.median(K[1144:1147,700:1600].reshape(-1,3),axis=0)          # the rail is one plain line (no bars or room in its colour)
comp=aT[...,None]*Ft+(1-aT[...,None])*C
print('recompose MAD',np.abs(comp-K).mean())
cv2.imwrite(SP+'R.png',np.clip(Rx,0,255).astype(np.uint8))
cv2.imwrite(SP+'W.png',np.dstack([np.clip(Fw,0,255),aW0*255]).astype(np.uint8))
cv2.imwrite(SP+'T.png',np.dstack([np.clip(Ft,0,255),aT*255]).astype(np.uint8))
cv2.imwrite(SP+'R-view.jpg',cv2.resize(np.clip(Rx,0,255).astype(np.uint8),(1344,760),interpolation=cv2.INTER_AREA))
