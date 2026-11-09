import cv2,numpy as np
SP=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/inside3/l4v3/'
W=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/'
K=cv2.imread(W+'ai/gen/loft4-end-gpt.png'); S=cv2.imread(W+'inside3/out/loft4-flight-last-single.png')
A=np.load(SP+'A_K2S.npy')
# homography refine from K-warp (affine A) to S
g2=cv2.cvtColor(S,cv2.COLOR_BGR2GRAY).astype(np.float32)
g1=cv2.cvtColor(cv2.warpAffine(K,A[:2],(1920,1080),flags=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY).astype(np.float32)
H=np.eye(3,dtype=np.float32)
cc,H=cv2.findTransformECC(g1,g2,H,cv2.MOTION_HOMOGRAPHY,(3,300,1e-7),None,5)
print(cc,H)
A3=A
for name,Hx in (('H',H),('inv',np.linalg.inv(H))):
    T=Hx@A3; im=cv2.warpPerspective(K,T,(1920,1080),flags=cv2.INTER_AREA); d=np.abs(im.astype(float)-S); print(name,d.mean())
    if name=='H': best=(T,im,d)
    elif d.mean()<best[2].mean(): best=(T,im,d)
T,im,d=best; np.save(SP+'H_K2S.npy',T); cv2.imwrite(SP+'ks-diff.jpg',np.clip(d.mean(2)*6,0,255).astype(np.uint8))
print(T)
# look at K crops
cv2.imwrite(SP+'k-tree.png',K[560:1400,620:1600]); cv2.imwrite(SP+'k-right.png',K[850:1400,1250:2100])
