"""Measure the perceived speed (dense optical flow, mean over the frame) along the camera path at low
resolution, and save the progress curve render_full.py uses to make the speed one smooth bell."""
import sys, argparse, numpy as np, cv2
import render_full as RF, proxy as X, camera as C
a = argparse.Namespace(home='loft4', key='../ai/gen/loft4-end-gpt.png', reg='out/hybrid/loft4-key-A.npy', end_scale=0.92, feather=0.035,
                       light=(0.0, 0.12), glow_fade=(1.0, 0.45), ease='smoother', layers='../inside3/out/loft4', room_depth=25.0)
f = RF.Flight(a, 480, 270)
X.INLAY['alpha'] = 1.0
ts = np.linspace(0, 1, 401)
imgs = [cv2.cvtColor(C.to_u8(X.render(f.p.cam_at(float(t)))), cv2.COLOR_RGB2GRAY) for t in ts]
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
v = [0.0]
for i in range(1, len(imgs)):
    fl = dis.calc(imgs[i - 1], imgs[i], None)
    v.append(float(np.mean(np.hypot(fl[..., 0], fl[..., 1]))))
v = np.array(v)
v = np.convolve(v, np.ones(5) / 5, mode='same')
prog = np.cumsum(v); prog = (prog - prog[0]) / (prog[-1] - prog[0])
np.save('out/full/loft4-flowtiming.npy', np.stack([ts, prog]))
print('speed per 0.05 of path', np.round(v[::20], 2))
