import cv2,numpy as np
SP=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/inside3/l4v3/'
W=r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/'
K=cv2.imread(W+'ai/gen/loft4-end-gpt.png'); S=cv2.imread(W+'inside3/out/loft4-flight-last-single.png')
M0=np.array([[0.77,0,-77.04],[0,0.77,-40.2],[0,0,1]])
g2=cv2.cvtColor(S,cv2.COLOR_BGR2GRAY).astype(np.float32)
g1=cv2.cvtColor(cv2.warpAffine(K,M0[:2],(1920,1080),flags=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY).astype(np.float32)
# use AFFINE from warped K to S
M=np.eye(2,3,dtype=np.float32)
cc,M=cv2.findTransformECC(g1,g2,M,cv2.MOTION_AFFINE,(3,300,1e-6),None,5)   # warps g2 coords: x_g2 = M x_g1?? check empirically
print(cc,M)
for name,Mx in (('M',np.vstack([M,[0,0,1]])),('inv',np.linalg.inv(np.vstack([M,[0,0,1]])))):
    A=Mx@M0
    im=cv2.warpAffine(K,A[:2],(1920,1080),flags=cv2.INTER_AREA)
    d=np.abs(im.astype(float)-S)
    print(name,d.mean())
    if name=='M': best=(A,im,d)
    else:
        if d.mean()<best[2].mean(): best=(A,im,d)
A,im,d=best; np.save(SP+'A_K2S.npy',A); print(A)
cv2.imwrite(SP+'ks.jpg',im); cv2.imwrite(SP+'ks-diff.jpg',np.clip(d.mean(2)*8,0,255).astype(np.uint8))
