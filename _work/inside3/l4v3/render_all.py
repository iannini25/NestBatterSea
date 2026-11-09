exec(open(r'C:/Users/berna/Desktop/NestBatterSea-LONDON/_work/inside3/l4v3/step.py',encoding='utf8').read().split("if __name__")[0])
import subprocess
from concurrent.futures import ProcessPoolExecutor
N=271; BL=7; SH=0.5; CENTRE=None
G={}
def init(c):
    G['s']=load(); p=P(N=N); G['p']=p
    r0=render(G['s'],p,0.0); G['r0']=G['s'].S.astype(np.float32)-r0
    r1=render(G['s'],p,1.0); G['r1']=G['s'].Eexact.astype(np.float32)-r1
def job(i):
    s,p=G['s'],G['p']; dt=1.0/(N-1); tau=i*dt
    ts=[tau] if i in (0,N-1) else [min(1,max(0,tau+SH*dt*((k+.5)/BL-.5))) for k in range(BL)]
    acc=sum(render(s,p,t) for t in ts)/len(ts)
    w0=1-smooth(i/14.); w1=smooth((i-(N-1-14))/14.)
    img=acc+G['r0']*w0+G['r1']*w1
    if i==0: img=s.S.astype(np.float32)
    if i==N-1: img=s.Eexact.astype(np.float32)
    return i,np.clip(img+.5,0,255).astype(np.uint8).tobytes()
if __name__=='__main__':
    c=0
    out=sys.argv[1]
    ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1920x1080','-r','60','-i','-','-c:v','ffv1','-level','3','-pix_fmt','yuv444p',out],stdin=subprocess.PIPE)
    pend={};nx=0
    with ProcessPoolExecutor(4,initializer=init,initargs=(c,)) as ex:
        for i,b in ex.map(job,range(N),chunksize=4):
            pend[i]=b
            while nx in pend:
                ff.stdin.write(pend.pop(nx)); 
                if nx%40==0: print('frame',nx,flush=True)
                nx+=1
    ff.stdin.close(); ff.wait(); print('done',out)
