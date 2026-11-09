"""
Check the seams of the published clips (mean absolute difference per channel, 0..255):
  flight first frame vs the site's facade image, flight last vs its arrival still,
  Step inside first vs flight last, Step inside last vs the living room photo,
  reversed clips vs the forward ends. Also saves a contact sheet of every seam.
usage: python verify_seams.py [loft4 bung3]
"""
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
V = os.path.join(ROOT, 'assets', 'video')
PHOTO = {'loft4': 'loft4-living', 'bung3': 'bung3-living'}


def frame(path, which):
    """first or last frame of a clip, RGB uint8"""
    if which == 'first':
        args = ['ffmpeg', '-v', 'error', '-i', path, '-frames:v', '1']
    else:
        args = ['ffmpeg', '-v', 'error', '-sseof', '-0.2', '-i', path, '-update', '1']
    out = subprocess.run(args + ['-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    if which == 'last':
        # -update 1 with a pipe writes every frame; keep the last PNG
        sig = b'\x89PNG\r\n\x1a\n'
        out = sig + out.split(sig)[-1]
    img = cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def load(path, size=(1920, 1080)):
    img = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
    if (img.shape[1], img.shape[0]) != size:
        img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    return img


def mad(a, b):
    return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())


def main():
    homes = sys.argv[1:] or ['loft4', 'bung3']
    facade = load(os.path.join(ROOT, 'assets', 'facade', 'master-2560.jpg'))
    tiles = []
    for h in homes:
        fl, ins = os.path.join(V, f'{h}-flight.mp4'), os.path.join(V, f'{h}-inside.mp4')
        f0, f1 = frame(fl, 'first'), frame(fl, 'last')
        i0, i1 = frame(ins, 'first'), frame(ins, 'last')
        r0, r1 = frame(os.path.join(V, f'{h}-flight-rev.mp4'), 'first'), frame(os.path.join(V, f'{h}-flight-rev.mp4'), 'last')
        still = load(os.path.join(ROOT, 'assets', 'stills', f'{h}-flight-last.jpg'))
        photo = load(os.path.join(ROOT, 'assets', 'interiors', PHOTO[h] + '.jpg'))
        print(h)
        print('  flight first vs facade image   %.2f' % mad(f0, facade))
        print('  flight last vs arrival still   %.2f' % mad(f1, still))
        print('  inside first vs flight last    %.2f' % mad(i0, f1))
        print('  inside last vs living photo    %.2f' % mad(i1, photo))
        print('  reverse first vs flight last   %.2f' % mad(r0, f1))
        print('  reverse last vs flight first   %.2f' % mad(r1, f0))
        tiles += [f0, facade, f1, i0, i1, photo]
    sm = [cv2.resize(t, (480, 270), interpolation=cv2.INTER_AREA) for t in tiles]
    rows = [np.hstack(sm[k:k + 6]) for k in range(0, len(sm), 6)]
    cv2.imwrite(os.path.join(HERE, 'out', 'seams.jpg'), cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print('sheet', os.path.join(HERE, 'out', 'seams.jpg'))


if __name__ == '__main__':
    main()
