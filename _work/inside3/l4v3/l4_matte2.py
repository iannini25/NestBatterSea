import cv2,numpy as np
SP=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/inside3/l4v3/'
W_=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/'
K=cv2.imread(W_+'ai/gen/loft4-end-gpt.png').astype(np.float32)
Z=np.load(SP+'mattes.npz'); d=Z['d']; Bg=Z['Bg']; mull=Z['mull']>0.5
h,w=K.shape[:2]; yy,xx=np.mgrid[0:h,0:w].astype(np.float32); X,Y=xx,yy
hsv=cv2.cvtColor(np.clip(K,0,255).astype(np.uint8),cv2.COLOR_BGR2HSV).astype(np.float32); H,S,V=hsv[...,0],hsv[...,1],hsv[...,2]
def zone(x0,y0,x1,y1): return (X>=x0)&(X<x1)&(Y>=y0)&(Y<y1)
treez=zone(640,600,1560,1340); parz=zone(1320,1000,1880,1140)|zone(1578,1100,1616,1345)
plantz=zone(620,1140,1380,1345)|zone(1790,1180,2060,1345); lampz=zone(960,1170,1045,1345); floorlamp=zone(740,1050,915,1300)
green=(H>=22)&(H<=90)&(S>38); strong=(H>=22)&(H<=90)&(S>70)
brown=(H<=24)&(S>30)&(V<150); dark=V<92
leafc=green|dark|brown
md=cv2.dilate(mull.astype(np.uint8),np.ones((3,5),np.uint8)).astype(bool)
leafc_m=leafc&(~md|strong)    # on mullions only green foliage, not the bronze bar
pole=zone(826,1090,840,1300)|zone(1695,740,1725,1040)|zone(1462,740,1492,1040)
leafc_m2=leafc_m&~(pole&~green)
a=np.clip((d-9.0)/20.0,0,1)*(leafc_m2&treez&~zone(1320,1000,1880,1340))
# keep what is connected to the trunks (the foliage tree); drop slat gaps etc
m8=(a>0.25).astype(np.uint8)
n,lb,st,_=cv2.connectedComponentsWithStats(cv2.dilate(m8,np.ones((5,5),np.uint8)),8)
keep=np.zeros(n,bool)
for i in range(1,n):
    x,y,ww,hh,ar=st[i]
    if ar>30000: keep[i]=True
a=a*keep[lb]
# parasol
aP=((V<100)&parz&(d>10)).astype(np.float32); aP=cv2.morphologyEx(aP,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
# planters (leaf colours only, not the table seen through the glass)
pa=np.clip((d-8.0)/18.0,0,1)*((plantz&~zone(1360,1000,1800,1345))&(green|dark|((H<=24)&(V<150))))
pa=np.where(plantz&(Y>1185)&((green&(d>9))),np.maximum(pa,0.95),pa)
pa=np.where(zone(1790,1180,2060,1345)&~green,0,pa)
n,lb,st,_=cv2.connectedComponentsWithStats((pa>0.3).astype(np.uint8),8)
keep=st[:,cv2.CC_STAT_AREA]>500; keep[0]=False; pa=pa*keep[lb]
# balcony lamp
aL=np.zeros((h,w),np.uint8); cv2.ellipse(aL,(1003,1198),(32,24),0,0,360,1,-1); aL[1198:1345,990:1016]=1
la=np.maximum(aL.astype(np.float32),np.clip((d-8)/15.,0,1)*lampz)
# rail: only the top line (dark/bright thin line) and the glass end posts
railline=zone(640,1130,2060,1150)&(np.clip((d-6)/16,0,1)>0.0)
rail_a=zone(640,1144,2052,1147).astype(np.float32)
# solid lip of the balcony: everything below 1340 in the balcony width counts as balcony structure
lip=np.zeros((h,w),np.float32); lip[1336:1352,620:2060]=1
aT=np.maximum.reduce([a,aP,pa,la,rail_a,lip])
aT=np.clip(cv2.GaussianBlur(aT.astype(np.float32),(0,0),0.7),0,1)
np.save(SP+'aT.npy',aT.astype(np.float32))
cr=(np.array([255,0,255.])*(1-aT[...,None])+K*aT[...,None])[560:1400,620:1600]
cv2.imwrite(SP+'matte-T.jpg',cr)
cr=(np.array([255,0,255.])*(1-aT[...,None])+K*aT[...,None])[980:1360,620:2100]
cv2.imwrite(SP+'matte-T2.jpg',cr)
