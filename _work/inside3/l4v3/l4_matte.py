"""LOFT 4 exact layers in the key image's space (2688 x 1520): R room, W window wall, T balcony things."""
import os,cv2,numpy as np
SP=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/inside3/l4v3/'
W_=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/'
K=cv2.imread(W_+'ai/gen/loft4-end-gpt.png').astype(np.float32); Cl=cv2.imread(W_+'ai/gen/loft4-clean.png')
h,w=K.shape[:2]
Hg=np.load(W_+'inside3/out/loft4-clean-H.npy')
B=cv2.warpPerspective(Cl,Hg,(w,h),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REFLECT).astype(np.float32)
# optional refine by a smooth flow of the clean plate to K on the room (the clean plate is a redraw)
gk=cv2.cvtColor(np.clip(K,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY); gb=cv2.cvtColor(np.clip(B,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY)
flow=cv2.calcOpticalFlowFarneback(cv2.resize(gb,(w//4,h//4)),cv2.resize(gk,(w//4,h//4)),None,0.5,4,31,5,7,1.5,0)
flow=np.clip(flow,-1.5,1.5)
flow=cv2.resize(flow,(w,h))*4.0
flow=cv2.GaussianBlur(flow,(0,0),90)
yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
# flow = B -> K displacement; to align B to K: B_al(x)=B(x - F(x)) approx
Bal=cv2.remap(B,xx-flow[...,0],yy-flow[...,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT)
print('flow max',np.percentile(np.abs(flow),99.5))
# low frequency gain of B to K
room=np.zeros((h,w),np.float32); room[264:1336,652:1940]=1
num=cv2.GaussianBlur(K*room[...,None],(0,0),30); den=cv2.GaussianBlur(Bal*room[...,None],(0,0),30)
wv=cv2.GaussianBlur(room,(0,0),30)[...,None]
gain=np.clip(np.where(wv>0.02,(num+1)/(den+1),1.0),0.8,1.25)
Bg=Bal*gain
lab=lambda im: cv2.cvtColor(np.clip(im,0,255).astype(np.uint8),cv2.COLOR_BGR2LAB).astype(np.float32)
d=np.sqrt(((lab(K)-lab(Bg))**2).sum(2)); d=cv2.GaussianBlur(d,(0,0),0.8)
hsv=cv2.cvtColor(np.clip(K,0,255).astype(np.uint8),cv2.COLOR_BGR2HSV).astype(np.float32)
H,S,V=hsv[...,0],hsv[...,1],hsv[...,2]
X,Y=xx,yy
glass=(X>=652)&(X<1940)&(Y>=264)&(Y<1336)
def zone(x0,y0,x1,y1): return (X>=x0)&(X<x1)&(Y>=y0)&(Y<y1)
treez=zone(640,600,1560,1340)
parz=zone(1320,1000,1880,1140)|zone(1578,1100,1616,1345)
plantz=zone(620,1140,1380,1345)|zone(1790,1180,2060,1345)
lampz=zone(960,1170,1045,1345)
# leaf colour: green or dark or brown branch (not bright wood)
green=(H>=22)&(H<=90)&(S>38)
brown=(H<=24)&(S>30)&(V<150)
dark=V<92
leafc=green|dark|brown
# floor lamp of the room (K's drawing) is room, not foreground
floorlamp=zone(740,1050,915,1300)
# tree soft matte
aT_tree=np.clip((d-9.0)/20.0,0,1)*(leafc&treez&~floorlamp)
aT_tree=cv2.morphologyEx(aT_tree,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
# solidify branches/leaves: where colour says leaf strongly and d large
# parasol: dark solid
aPar=((V<100)&parz&(d>10)).astype(np.float32); aPar=cv2.morphologyEx(aPar,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
# planters below rail
aPl=np.clip((d-8.0)/18.0,0,1)*(plantz&~zone(1360,1000,1800,1345))
aPl=np.where(plantz&(Y>1180)&((green&(d>9))|(dark)),np.maximum(aPl,0.95),aPl)
# balcony lamp: pole + head
aLamp=np.clip((d-8)/15.,0,1)*lampz
yl=1200; lmask=np.zeros((h,w),np.uint8); cv2.ellipse(lmask,(1003,1198),(32,24),0,0,360,1,-1); lmask[1198:1345,990:1016]=1
aLamp=np.maximum(aLamp,lmask.astype(np.float32)*1.0)
# balcony balustrade: glass band: very faint overlay from d in the band, rail top line solid
railz=zone(640,1130,2060,1345)
aRail=np.clip((d-3.0)/18.0,0,0.5)*railz
aT=np.maximum.reduce([aT_tree,aPar,aPl,aLamp,aRail])
# solid planter trough / front lip below the glass
solid_bottom=zone(620,1336,2060,1350)
aT[solid_bottom]=1.0
aT=np.clip(cv2.GaussianBlur(aT,(0,0),0.7),0,1)
# window wall alpha: everything outside the glass except the balcony front; mullions & transom
g=cv2.cvtColor(np.clip(K,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)
colv=np.median(g[272:356,:],axis=0)
loc=cv2.GaussianBlur(colv[None,:],(0,0),25)[0]
mull_c=(colv<loc-25)&(np.arange(w)>=642)&(np.arange(w)<1950)
print('mull cols',np.nonzero(mull_c)[0])
rowv=np.median(g[:,1800:1900],axis=1); locr=cv2.GaussianBlur(rowv[:,None],(0,0),25)[:,0]
tr=(rowv<locr-45)&(np.arange(h)>880)&(np.arange(h)<950); print('trans rows',np.nonzero(tr)[0])
tr[905:946]=True           # the whole transom band
mull=np.zeros((h,w),np.float32); mull[:,mull_c]=1; mull[tr,:]=1
mull*=glass
# frame inner lines: the top frame of glass and bottom sill as part of W
aW=np.maximum.reduce([(~glass).astype(np.float32),mull])
aW=np.clip(cv2.GaussianBlur(aW,(0,0),0.8),0,1)
np.savez_compressed(SP+'mattes.npz',aT=aT.astype(np.float32),aW=aW.astype(np.float32),d=d.astype(np.float32),Bg=Bg.astype(np.float32),Bal=Bal.astype(np.float32),mull=mull)
cr=(np.array([255,0,255.])*(1-aT[...,None])+K*aT[...,None])[560:1400,620:1600]
cv2.imwrite(SP+'matte-T.jpg',cr)
cr=(np.array([255,0,255.])*(1-aW[...,None])+K*aW[...,None])[200:1400,620:2000]
cv2.imwrite(SP+'matte-W.jpg',cv2.resize(cr,(0,0),fx=.7,fy=.7))
cv2.imwrite(SP+'d.jpg',np.clip(d[560:1400,620:1600]*4,0,255).astype(np.uint8))
