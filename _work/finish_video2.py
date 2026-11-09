"""
finish_video2.py: finish a generated camera move for the site (v2: smoother, sharper, lighter).

  1. decode the raw take (yuv420p, 1920x1080); optional trim in seconds from the start / end
  2. optional handover match to the still the clip starts from (--match-still):
     --match-geometry S  ECC affine alignment of frame 0 to the still, faded out over S seconds
                         (a regenerated take often starts 0.3-0.6% zoomed / a few px off)
     exposure/colour gain (per channel RGB gain, BT.709, applied exactly in YUV, no chroma resampling)
  3. retime + motion interpolate to --fps. --speed 1.15 = 15% faster, done purely by retiming:
     output frame j sits at source position j*(N-1)/M, so frame 0 and the last frame are the exact
     source end frames (bit exact before sharpening) and no source frame is dropped first.
       --interp flow   dense optical flow (OpenCV DIS) + occlusion aware bidirectional warping
                       (default; best on thin verticals, glazing, foliage in the tests)
                mci    ffmpeg minterpolate, tuned (bidir, epzs, search_param 96)
                blend  ffmpeg minterpolate frame blending: never invents structure, ghosts on
                       fast motion
       --safe LO,HI    flow engine only: where the two warped frames still disagree after
                       occlusion handling (luma levels, LO..HI ramp), fade to a plain blend
  4. optional gentle luma only unsharp (--sharpen amount, 5x5; 0 = off)
  5. lossless master (FFV1) -> 8 encodes, all silent, yuv420p, faststart, closed GOP with a
     keyframe every 0.5 s, BT.709 matrix + limited range tagged:
       <slug>.mp4 <slug>-720.mp4 <slug>-rev.mp4 <slug>-rev-720.mp4           H.264 High
       <slug>-av1.mp4 <slug>-720-av1.mp4 <slug>-rev-av1.mp4 <slug>-rev-720-av1.mp4   AV1 Main 8 bit
     reversed files are the processed frames reversed, so going back retraces the same path
  6. stills: first and last frame of the encoded 1080p H.264 file, decoded and converted with
     BT.709 (as browsers do), saved as JPG q90, WebP and AVIF, each verified against the decoded
     frame (mean abs diff < 2/255)
  7. report: durations, frame counts, sizes, VMAF / PSNR / SSIM of every encode vs the master,
     interpolation fidelity vs the real source frames (leave one out), codec strings / MIME types

Measured on the site's four clips (Nov 2026; details in the validation report):
  * interpolation, leave one out (drop every other source frame, rebuild it, compare with the real
    one): flow beats the best minterpolate setting by +0.7..+2.5 dB mean PSNR and +1..+3 dB on the
    worst 1% of blocks; minterpolate breaks close foliage and frame borders into 16 px blocks.
    In me_mode=bidir, minterpolate's mc_mode and vsbmc do nothing (bit identical output); bilat or
    a larger search_param help it. Plain minterpolate also never renders the last source interval,
    hence the padding/re-stamping in FFmpegEngine.
  * flow failure mode: thin, fast verticals (mullions passing the lens) can tear for 1 to 2 frames;
    a 5x5 median on the half-res flow and blurred consistency maps remove most seams. --safe trades
    that for ghosting (plain blend) and did not look better on these clips, so it is off by default.
  * 60 vs 48 fps: 48 saves only ~2% (H.264) / ~10% (AV1) because the 0.5 s keyframes dominate the
    bitrate, and 48 judders on 60/120 Hz screens: 60 it is.
  * colour: raw frames piped into ffmpeg 9 must be tagged BT.709/limited on the INPUT side, else an
    output tagged BT.709 triggers a silent BT.601->709 matrix conversion (warm interiors ~5% darker
    in red). The master and the H.264 file are checked against the rendered frame for this.
    Browsers decode untagged HD as BT.709 while ffmpeg's default RGB conversion is BT.601: the old
    site's stills matched the 601 reading (red off by ~5/255 on the interiors); stills here are BT.709.
  * H.264 CRF 21 / 22 (1080p / 720p): VMAF ~98 / ~96.6 vs the master. AV1 SVT preset 2 CRF 38 / 41:
    equal or better VMAF at ~40-45% / ~50% of the H.264 size.

usage:
  python _work/finish_video2.py <raw.mp4> <slug> [--speed 1.0] [--fps 60] [--trim-start S]
         [--trim-end S] [--match-still path [--match-geometry 0.5]] [--out assets] [--sharpen 0.35] [--interp flow]
         [--track js/tracks.js[:key]] [--master path.mkv] [--no-qc] [--no-vmaf]
"""
import argparse, json, math, os, shutil, struct, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1920, 1080
FS = W * H * 3 // 2
MCI_OPTS = 'mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:search_param=96:vsbmc=1:scd=none'
BLEND_OPTS = 'mi_mode=blend:scd=none'

# BT.709 limited range: [Y-16, Cb-128, Cr-128] -> RGB 0..255
M709 = np.array([[1.164384, 0.0, 1.792741],
                 [1.164384, -0.213249, -0.532909],
                 [1.164384, 2.112402, 0.0]])


def log(*a):
    print(*a, flush=True)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, **kw)
    if r.returncode:
        raise RuntimeError(' '.join(map(str, cmd))[:400] + '\n' + r.stderr.decode(errors='replace')[-2000:])
    return r


# ---------------------------------------------------------------- frames (yuv420p as flat uint8)
def planes(buf):
    b = buf if isinstance(buf, np.ndarray) else np.frombuffer(buf, np.uint8)
    return (b[:W * H].reshape(H, W), b[W * H:W * H * 5 // 4].reshape(H // 2, W // 2),
            b[W * H * 5 // 4:].reshape(H // 2, W // 2))


def join(y, u, v):
    return np.concatenate([y.ravel(), u.ravel(), v.ravel()])


def probe(path):
    r = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
             'stream=width,height,r_frame_rate', '-of', 'json', path])
    s = json.loads(r.stdout)['streams'][0]
    n, d = s['r_frame_rate'].split('/')
    return int(s['width']), int(s['height']), float(n) / float(d)


def decode(path, vf=None):
    """all frames of a video as yuv420p 1920x1080 frames"""
    w, h, _ = probe(path)
    f = [] if (w, h) == (W, H) else [f'scale={W}:{H}:flags=lanczos+accurate_rnd']
    if vf:
        f.append(vf)
    cmd = ['ffmpeg', '-v', 'error', '-i', path] + (['-vf', ','.join(f)] if f else []) + \
          ['-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-']
    o = run(cmd).stdout
    return [np.frombuffer(o, np.uint8, FS, i * FS) for i in range(len(o) // FS)]


def decode_at(path, index):
    """one frame (by index; -1 = last) of a video as a yuv420p 1920x1080 frame"""
    if index == 0:
        f = decode_first(path)
        return f
    n = count_frames(path)
    return decode(path, vf=f'trim=start_frame={n - 1 if index < 0 else index}')[0]


def decode_first(path):
    w, h, _ = probe(path)
    f = ['null'] if (w, h) == (W, H) else [f'scale={W}:{H}:flags=lanczos+accurate_rnd']
    o = run(['ffmpeg', '-v', 'error', '-i', path, '-frames:v', '1', '-vf', ','.join(f), '-f', 'rawvideo',
             '-pix_fmt', 'yuv420p', '-']).stdout
    return np.frombuffer(o, np.uint8, FS, 0)


def count_frames(path):
    r = run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
             'stream=nb_read_frames', '-of', 'csv=p=0', path])
    return int(r.stdout.decode().strip().strip(','))


def to_rgb(frame, w=W, h=H):
    """BT.709 limited -> full range RGB uint8, bilinear chroma upsampling (what browsers display)"""
    import cv2
    b = frame
    y = b[:w * h].reshape(h, w).astype(np.float32)
    u = b[w * h:w * h * 5 // 4].reshape(h // 2, w // 2).astype(np.float32)
    v = b[w * h * 5 // 4:].reshape(h // 2, w // 2).astype(np.float32)
    u = cv2.resize(u, (w, h), interpolation=cv2.INTER_LINEAR) - 128
    v = cv2.resize(v, (w, h), interpolation=cv2.INTER_LINEAR) - 128
    y = (y - 16) * M709[0, 0]
    rgb = np.stack([y + M709[0, 2] * v, y + M709[1, 1] * u + M709[1, 2] * v, y + M709[2, 1] * u], -1)
    return np.clip(rgb + 0.5, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- colour gain
def gain_for(first, still_path):
    rgb = to_rgb(first).reshape(-1, 3).astype(np.float64)
    m = np.asarray(Image.open(still_path).convert('RGB').resize((W, H), Image.LANCZOS), np.float64).reshape(-1, 3)
    g = (m.mean(0) + 1) / (rgb.mean(0) + 1)
    return np.clip(g, 0.9, 1.12), float(np.abs(rgb - m).mean())


def apply_gain(frame, g):
    """RGB' = diag(g) RGB done as the equivalent affine map in BT.709 YUV (no chroma resampling)"""
    import cv2
    T = (np.linalg.inv(M709) @ np.diag(g) @ M709).astype(np.float32)
    y, u, v = [p.astype(np.float32) for p in planes(frame)]
    yc, uc, vc = y - 16, u - 128, v - 128
    up = lambda p: cv2.resize(p, (W, H), interpolation=cv2.INTER_LINEAR)
    yd = cv2.resize(yc, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    y2 = T[0, 0] * yc + T[0, 1] * up(uc) + T[0, 2] * up(vc) + 16
    u2 = T[1, 0] * yd + T[1, 1] * uc + T[1, 2] * vc + 128
    v2 = T[2, 0] * yd + T[2, 1] * uc + T[2, 2] * vc + 128
    q = lambda p: np.clip(np.floor(p + 0.5), 0, 255).astype(np.uint8)
    return join(q(y2), q(u2), q(v2))


# ---------------------------------------------------------------- geometry match to the still
def align_to_still(first, still_path):
    """affine W (ECC, coarse to fine) with first(W.x) ~ still(x); returns (correlation, W 2x3)"""
    import cv2
    st = cv2.cvtColor(np.asarray(Image.open(still_path).convert('RGB').resize((W, H), Image.LANCZOS)), cv2.COLOR_RGB2GRAY).astype(np.float32)
    fr = cv2.cvtColor(to_rgb(first), cv2.COLOR_RGB2GRAY).astype(np.float32)
    warp = np.eye(2, 3, dtype=np.float32)
    cc = -1.0
    for s in (0.25, 0.5):
        a = cv2.resize(st, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        b = cv2.resize(fr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        w = warp.copy(); w[:, 2] *= s
        cc, w = cv2.findTransformECC(a, b, w, cv2.MOTION_AFFINE,
                                     (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-7), None, 5)
        warp = w.copy(); warp[:, 2] /= s
    return float(cc), warp


def warp_frame(frame, Wm):
    """apply the luma-space affine Wm (dst -> src) to a yuv420p frame; chroma uses the same map in its own grid"""
    import cv2
    y, u, v = planes(frame)
    fl = cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP
    y2 = cv2.warpAffine(y, Wm, (W, H), flags=fl, borderMode=cv2.BORDER_REPLICATE)
    A, t = Wm[:, :2], Wm[:, 2]
    o = np.array([0.0, 0.5])                           # chroma sample (MPEG-2 siting) in luma units
    Wc = np.hstack([A, ((A @ o + t - o) / 2)[:, None]]).astype(np.float32)
    u2 = cv2.warpAffine(u, Wc, (W // 2, H // 2), flags=fl, borderMode=cv2.BORDER_REPLICATE)
    v2 = cv2.warpAffine(v, Wc, (W // 2, H // 2), flags=fl, borderMode=cv2.BORDER_REPLICATE)
    return join(y2, u2, v2)


# ---------------------------------------------------------------- interpolation engines
class FlowEngine:
    """Bidirectional DIS optical flow (computed at half resolution, where it is smoother and was more
    accurate in the leave-one-out tests), linear flow-to-time approximation, backward warping of both
    neighbours, weights from forward/backward flow consistency (occlusions)."""

    def __init__(self, safe=None, scale=0.5, sigma=1.5, med=5, wsig=3.0, workers=8):
        import cv2
        self.cv2 = cv2
        cv2.setNumThreads(2)
        self.safe, self.scale, self.sigma, self.workers = safe, scale, sigma, workers
        self.med, self.wsig = med, wsig      # flow median (half res) and consistency-map blur: no torn seams
        self.gx, self.gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        self.gxc, self.gyc = np.meshgrid(np.arange(W // 2, dtype=np.float32), np.arange(H // 2, dtype=np.float32))
        self.local = threading.local()
        self.fallback_px = []

    def _dis(self):
        if not hasattr(self.local, 'dis'):
            self.local.dis = self.cv2.DISOpticalFlow_create(self.cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        return self.local.dis

    def _warp(self, img, fx, fy, interp=None):
        cv2 = self.cv2
        return cv2.remap(img, fx, fy, interp if interp is not None else cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    def flows(self, y0, y1):
        cv2 = self.cv2
        sw, sh = int(W * self.scale), int(H * self.scale)
        a = cv2.resize(y0, (sw, sh), interpolation=cv2.INTER_AREA)
        b = cv2.resize(y1, (sw, sh), interpolation=cv2.INTER_AREA)
        dis = self._dis()

        def up(f):
            if self.med:
                f = np.dstack([cv2.medianBlur(np.ascontiguousarray(f[..., c]), self.med) for c in range(2)])
            return cv2.resize(f, (W, H), interpolation=cv2.INTER_LINEAR) / self.scale
        f01, f10 = up(dis.calc(a, b, None)), up(dis.calc(b, a, None))
        c0 = np.hypot(*(f01 + self._warp(f10, self.gx + f01[..., 0], self.gy + f01[..., 1])).transpose(2, 0, 1)).astype(np.float32)
        c1 = np.hypot(*(f10 + self._warp(f01, self.gx + f10[..., 0], self.gy + f10[..., 1])).transpose(2, 0, 1)).astype(np.float32)
        if self.wsig:
            c0, c1 = cv2.GaussianBlur(c0, (0, 0), self.wsig), cv2.GaussianBlur(c1, (0, 0), self.wsig)
        return f01, f10, c0, c1

    def interp(self, fr0, fr1, t, fl):
        cv2 = self.cv2
        f01, f10, c0, c1 = fl
        ft0 = -(1 - t) * t * f01 + t * t * f10
        ft1 = (1 - t) * (1 - t) * f01 - t * (1 - t) * f10
        m0x, m0y = self.gx + ft0[..., 0], self.gy + ft0[..., 1]
        m1x, m1y = self.gx + ft1[..., 0], self.gy + ft1[..., 1]
        v0 = np.exp(-(self._warp(c0, m0x, m0y) / self.sigma) ** 2)
        v1 = np.exp(-(self._warp(c1, m1x, m1y) / self.sigma) ** 2)
        w0, w1 = (1 - t) * v0, t * v1
        ws = w0 + w1
        lo = ws < 0.05                                  # neither side trusted: plain temporal weights
        w0 = np.where(lo, 1 - t, w0); ws = np.where(lo, 1.0, ws)
        a0 = (w0 / ws).astype(np.float32)
        half = (W // 2, H // 2)
        chroma_maps = None
        out, mask = [], None
        for k, (p0, p1) in enumerate(zip(planes(fr0), planes(fr1))):
            if k == 0:
                mx0, my0, mx1, my1, A0 = m0x, m0y, m1x, m1y, a0
            else:
                if chroma_maps is None:
                    r = lambda p: cv2.resize(p, half, interpolation=cv2.INTER_AREA)
                    chroma_maps = (r(ft0[..., 0]) / 2 + self.gxc, r(ft0[..., 1]) / 2 + self.gyc,
                                   r(ft1[..., 0]) / 2 + self.gxc, r(ft1[..., 1]) / 2 + self.gyc, r(a0))
                mx0, my0, mx1, my1, A0 = chroma_maps
            q0, q1 = p0.astype(np.float32), p1.astype(np.float32)
            W0 = self._warp(q0, mx0, my0, cv2.INTER_CUBIC)
            W1 = self._warp(q1, mx1, my1, cv2.INTER_CUBIC)
            res = A0 * W0 + (1 - A0) * W1
            if self.safe:
                if k == 0:
                    lo_, hi_ = self.safe
                    d = cv2.GaussianBlur(np.abs(W0 - W1), (0, 0), 4)
                    mask = cv2.GaussianBlur(np.clip((d - lo_) / (hi_ - lo_), 0, 1), (0, 0), 6)
                    self.fallback_px.append(float(mask.mean()))
                    m = mask
                else:
                    m = cv2.resize(mask, half, interpolation=cv2.INTER_AREA)
                res = (1 - m) * res + m * ((1 - t) * q0 + t * q1)
            out.append(np.clip(np.floor(res + 0.5), 0, 255).astype(np.uint8))
        return join(*out)

    def render(self, frames, M):
        """M+1 output frames at source positions j*(N-1)/M (generator, in order)"""
        N = len(frames)
        groups = {}
        for j in range(M + 1):
            num = j * (N - 1)
            i, rem = divmod(num, M)
            groups.setdefault(min(i, N - 2) if rem else i, []).append((j, i, rem / M))

        def interval(i):
            todo = groups[i]
            res = []
            fl = None
            for j, ii, t in todo:
                if t == 0:
                    res.append(frames[ii])
                    continue
                if fl is None:
                    fl = self.flows(planes(frames[i])[0], planes(frames[i + 1])[0])
                res.append(self.interp(frames[i], frames[i + 1], t, fl))
            return res
        keys = sorted(groups)
        with ThreadPoolExecutor(self.workers) as ex:
            for k in range(0, len(keys), self.workers * 2):
                for res in ex.map(interval, keys[k:k + self.workers * 2]):
                    yield from res


class FFmpegEngine:
    """minterpolate driven with exact timestamps: the source is padded with two clones of its last
    frame (minterpolate never renders the final interval otherwise) and re-stamped so that source frame
    n sits at n*M/(fps*(N-1)) s; output frames fall at j/fps and the output is cut at frame M, which is
    then exactly the last source frame."""

    def __init__(self, opts):
        self.opts = opts

    def render(self, frames, M, fps=60):
        N = len(frames)
        vf = (f'tpad=stop_mode=clone:stop=2,settb=1/{fps * (N - 1)},setpts=N*{M},'
              f'minterpolate=fps={fps}:{self.opts},trim=end_frame={M + 1}')
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-s', f'{W}x{H}',
                              '-r', '24', '-i', '-', '-vf', vf, '-fps_mode', 'passthrough', '-f', 'rawvideo',
                              '-pix_fmt', 'yuv420p', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        def feed():
            try:
                for f in frames:
                    p.stdin.write(f.tobytes())
            finally:
                p.stdin.close()
        th = threading.Thread(target=feed, daemon=True)
        th.start()
        n = 0
        while True:
            b = p.stdout.read(FS)
            if len(b) < FS:
                break
            n += 1
            yield np.frombuffer(b, np.uint8)
        th.join()
        err = p.stderr.read().decode(errors='replace')
        if p.wait() or n != M + 1:
            raise RuntimeError(f'minterpolate produced {n} frames, expected {M + 1}\n{err[-1500:]}')


def make_engine(name, safe):
    if name == 'flow':
        return FlowEngine(safe=safe)
    return FFmpegEngine(MCI_OPTS if name == 'mci' else BLEND_OPTS)


# ---------------------------------------------------------------- quality helpers
def loo_fidelity(engine, frames):
    """leave one out: interpolate every odd source frame from its two even neighbours (twice the real
    motion per step) and compare with the real frame. Returns luma PSNR stats + worst 1% 32px blocks."""
    even = frames[0::2]
    ne = len(even)
    if ne < 3:
        return None
    outs = list(engine.render(even, 2 * (ne - 1)))
    ps, p1 = [], []
    for k in range(ne - 1):
        a = planes(outs[2 * k + 1])[0].astype(np.float32)
        b = planes(frames[2 * k + 1])[0].astype(np.float32)
        d2 = (a - b) ** 2
        ps.append(10 * math.log10(255 ** 2 / max(float(d2.mean()), 1e-6)))
        blk = d2[:H // 32 * 32].reshape(H // 32, 32, W // 32, 32).mean((1, 3))
        p1.append(float(np.percentile(10 * np.log10(255 ** 2 / np.maximum(blk, 1e-3)), 1)))
    ps = np.array(ps)
    return {'frames': len(ps), 'psnr_mean': round(float(ps.mean()), 2), 'psnr_min': round(float(ps.min()), 2),
            'psnr_min_at_src_frame': int(2 * ps.argmin() + 1), 'worst1pct_block_psnr_mean': round(float(np.mean(p1)), 2)}


def vmaf(dist, ref, ref_vf, cwd, tag, fps):
    # both sides re-stamped by frame index: MKV (1 ms) and MP4 timestamps round differently and would
    # otherwise make the frame sync pair neighbouring frames
    log_name = f'vmaf_{tag}.json'
    fc = (f'[0:v]settb=1/{fps},setpts=N[d];[1:v]{ref_vf},settb=1/{fps},setpts=N[r];'
          f'[d][r]libvmaf=model=version=vmaf_v0.6.1:n_threads=16:log_fmt=json:log_path={log_name}:'
          f'feature=name=psnr|name=float_ssim')
    run(['ffmpeg', '-v', 'error', '-i', os.path.abspath(dist), '-i', os.path.abspath(ref),
         '-filter_complex', fc, '-f', 'null', '-'], cwd=cwd)
    d = json.load(open(os.path.join(cwd, log_name)))
    pm = d['pooled_metrics']
    v = np.array([f['metrics']['vmaf'] for f in d['frames']])
    return {'vmaf': round(pm['vmaf']['mean'], 2), 'vmaf_min': round(float(v.min()), 2),
            'vmaf_1pct_low': round(float(np.percentile(v, 1)), 2),
            'psnr_y': round(pm['psnr_y']['mean'], 2), 'ssim': round(pm['float_ssim']['mean'], 4), 'frames': len(v)}


def codec_string(path):
    """RFC 6381 codec string read from the avcC / av1C box in the moov"""
    data = open(path, 'rb').read()
    pos = 0
    while pos + 8 <= len(data):
        size, typ = struct.unpack('>I4s', data[pos:pos + 8])
        if size == 1:
            size = struct.unpack('>Q', data[pos + 8:pos + 16])[0]
        if typ == b'moov':
            moov = data[pos:pos + size]
            break
        if size < 8:
            return None
        pos += size
    else:
        return None
    i = moov.find(b'avcC')
    if i > 0:
        b = moov[i + 4:i + 8]
        return 'avc1.%02X%02X%02X' % (b[1], b[2], b[3])
    i = moov.find(b'av1C')
    if i > 0:
        b = moov[i + 4:i + 8]
        prof, lvl = b[1] >> 5, b[1] & 31
        tier = 'H' if b[2] >> 7 else 'M'
        depth = (12 if (b[2] >> 5) & 1 else 10) if (b[2] >> 6) & 1 else 8
        return f'av01.{prof}.{lvl:02d}{tier}.{depth:02d}'
    return None


def keyframes(path):
    r = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'frame=key_frame', '-of', 'csv=p=0', path])
    k = [i for i, l in enumerate(r.stdout.decode().split()) if l.strip().startswith('1')]
    return k, len(r.stdout.decode().split())


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('raw'); ap.add_argument('slug')
    ap.add_argument('--speed', type=float, default=1.0, help='1.15 = 15%% faster (retiming only)')
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--trim-start', type=float, default=0.0, help='seconds removed from the start')
    ap.add_argument('--trim-end', type=float, default=0.0, help='seconds removed from the end')
    ap.add_argument('--match-still', help='gain match the first frame to this image')
    ap.add_argument('--match-geometry', type=float, default=0.0, metavar='SECONDS',
                    help='with --match-still: align frame 0 to the still (ECC affine) and fade the correction out over SECONDS')
    ap.add_argument('--out', default=os.path.join(ROOT, 'assets'))
    ap.add_argument('--reports', default=os.path.join(ROOT, '_work', 'reports'), help='where the JSON report goes (kept out of assets/)')
    ap.add_argument('--sharpen', type=float, default=0.35, help='luma unsharp amount (5x5), 0 = off')
    ap.add_argument('--interp', choices=['flow', 'mci', 'blend'], default='flow')
    ap.add_argument('--safe', default='', help='flow only: LO,HI disagreement ramp for the blend fallback, e.g. 30,60')
    ap.add_argument('--crf', type=int, default=21, help='H.264 1080p')
    ap.add_argument('--crf720', type=int, default=22, help='H.264 720p')
    ap.add_argument('--av1-crf', type=int, default=38)
    ap.add_argument('--av1-crf720', type=int, default=41)
    ap.add_argument('--av1-preset', type=int, default=2)
    ap.add_argument('--av1-params', default='', help='extra -svtav1-params (tune=0 measured worse per byte)')
    ap.add_argument('--track', help='js/tracks.js[:key] or a track .json: write the window outline retimed to the new frames')
    ap.add_argument('--master', help='keep the lossless master at this path (.mkv)')
    ap.add_argument('--no-qc', action='store_true', help='skip the leave one out interpolation check')
    ap.add_argument('--no-vmaf', action='store_true')
    ap.add_argument('--master-only', action='store_true', help='stop after the lossless master (needs --master)')
    ap.add_argument('--jobs', type=int, default=3, help='parallel encodes')
    a = ap.parse_args()
    t_start = time.time()

    vdir, sdir = os.path.join(a.out, 'video'), os.path.join(a.out, 'stills')
    rdir = a.reports
    for d in (vdir, sdir, rdir):
        os.makedirs(d, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='fv2_')
    slug = a.slug
    rep = {'slug': slug, 'source': os.path.abspath(a.raw), 'settings': {k: v for k, v in vars(a).items() if k not in ('raw', 'slug')}}

    # 1. decode + trim
    _, _, src_fps = probe(a.raw)
    frames = decode(a.raw)
    n_all = len(frames)
    t0f, t1f = int(round(a.trim_start * src_fps)), int(round(a.trim_end * src_fps))
    frames = frames[t0f:n_all - t1f]
    N = len(frames)
    if N < 2:
        sys.exit('nothing left after trimming')
    log(f'[{slug}] source {n_all} frames @ {src_fps:g} fps; using {N} (trim {t0f} + {t1f} frames)')

    # 2a. geometry: land frame 0 exactly on the still, fade the correction out over --match-geometry seconds
    if a.match_still and a.match_geometry > 0:
        cc, Wm = align_to_still(frames[0], a.match_still)
        A = Wm[:, :2]
        scale = float(np.sqrt(abs(np.linalg.det(A))))
        shift = float(np.hypot(*Wm[:, 2]))
        ok = cc > 0.95 and abs(scale - 1) < 0.03 and shift < 40
        K = max(1, int(round(a.match_geometry * src_fps)))
        I2 = np.eye(2, 3, dtype=np.float32)
        geo = {'ecc_corr': round(cc, 4), 'scale': round(scale, 5), 'shift_px': [round(float(x), 2) for x in Wm[:, 2]],
               'applied': bool(ok), 'fade_frames': K}
        if ok:
            _, mad_g0 = gain_for(frames[0], a.match_still)
            for i in range(min(K, N)):
                lam = 0.5 * (1 + math.cos(math.pi * i / K))
                frames[i] = warp_frame(frames[i], (I2 + lam * (Wm - I2)).astype(np.float32))
            _, mad_g1 = gain_for(frames[0], a.match_still)
            geo.update(first_vs_still_mad_before=round(mad_g0, 2), first_vs_still_mad_after=round(mad_g1, 2))
        rep['geometry'] = geo
        log(f'[{slug}] geometry vs still: corr {cc:.4f} scale {scale:.4f} shift {Wm[0, 2]:.1f},{Wm[1, 2]:.1f} px -> '
            + (f'corrected, fading over {K} source frames' if ok else 'NOT applied (alignment not trusted)'))

    # 2b. gain
    gain = np.ones(3)
    if a.match_still:
        gain, mad_before = gain_for(frames[0], a.match_still)
        frames = [apply_gain(f, gain) for f in frames]
        _, mad_after = gain_for(frames[0], a.match_still)
        rep['gain'] = {'still': os.path.abspath(a.match_still), 'rgb_gain': [round(float(g), 4) for g in gain],
                       'first_vs_still_mad_before': round(mad_before, 2), 'first_vs_still_mad_after': round(mad_after, 2)}
        log(f'[{slug}] gain {np.round(gain, 4)}; first frame vs still MAD {mad_before:.2f} -> {mad_after:.2f}')

    # 3. timeline: output frame j <-> source position j*(N-1)/M, last frame exact
    M = max(1, int(round((N - 1) * a.fps / (src_fps * a.speed))))
    eff_speed = (N - 1) * a.fps / (src_fps * M)
    n_out = M + 1
    gop = max(1, int(a.fps * 0.5))
    rep['timeline'] = {'src_frames': N, 'src_fps': src_fps, 'src_seconds': round(N / src_fps, 3), 'out_frames': n_out,
                       'fps': a.fps, 'out_seconds': round(n_out / a.fps, 3), 'speed_effective': round(eff_speed, 4),
                       'interp': a.interp, 'keyint_frames': gop}
    log(f'[{slug}] {N} frames @ {src_fps:g} -> {n_out} frames @ {a.fps} ({n_out / a.fps:.3f} s, speed x{eff_speed:.4f}), engine {a.interp}')
    safe = tuple(float(x) for x in a.safe.split(',')) if a.safe else None
    engine = make_engine(a.interp, safe)

    # 4. render -> sharpen -> lossless master
    master = a.master or os.path.join(tmp, 'master.mkv')
    os.makedirs(os.path.dirname(os.path.abspath(master)), exist_ok=True)
    vf = f'unsharp=lx=5:ly=5:la={a.sharpen}:cx=5:cy=5:ca=0' if a.sharpen > 0 else 'null'
    # the raw frames must be tagged as what they are (BT.709, limited): ffmpeg 9 otherwise treats raw input as
    # BT.601 and, because the output is tagged BT.709, silently converts the matrix (warm tones lose ~5% red)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-s', f'{W}x{H}',
                            '-r', str(a.fps), '-colorspace', 'bt709', '-color_range', 'tv', '-i', '-', '-vf', vf, '-c:v', 'ffv1', '-level', '3', '-slices', '16',
                            '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_range', 'tv', master],
                           stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    t = time.time()
    count = 0
    first_out = last_out = None
    for fr in (engine.render(frames, M) if a.interp == 'flow' else engine.render(frames, M, a.fps)):
        if count == 0:
            first_out = fr
        last_out = fr
        enc.stdin.write(fr.tobytes())
        count += 1
    enc.stdin.close()
    if enc.wait():
        raise RuntimeError(enc.stderr.read().decode())
    assert count == n_out, (count, n_out)
    exact = bool(np.array_equal(first_out, frames[0]) and np.array_equal(last_out, frames[-1]))
    rep['timeline']['ends_bit_exact_before_sharpen'] = exact
    # guard against any silent colour/range conversion on the way into the master
    m0 = decode_first(master)
    pm_in = [float(p.mean()) for p in planes(first_out)]
    pm_master = [float(p.mean()) for p in planes(m0)]
    drift = max(abs(x - y) for x, y in zip(pm_in, pm_master))
    rep['timeline']['master_plane_mean_drift'] = round(drift, 3)
    if (a.sharpen <= 0 and not np.array_equal(m0, first_out)) or drift > 0.75:
        raise RuntimeError(f'master frame 0 differs from the rendered frame (plane mean drift {drift:.2f}): colour conversion?')
    if isinstance(engine, FlowEngine) and engine.fallback_px:
        rep['timeline']['safe_fallback_mean_area'] = round(float(np.mean(engine.fallback_px)), 5)
        rep['timeline']['safe_fallback_max_area'] = round(float(np.max(engine.fallback_px)), 5)
    log(f'[{slug}] master: {count} frames in {time.time() - t:.0f} s; first/last frame = source ends: {exact}')
    if a.master_only:
        json.dump(rep, open(os.path.join(rdir, f'{slug}.master.json'), 'w'), indent=1)
        shutil.rmtree(tmp, ignore_errors=True)
        return

    # 5. encodes
    # level pinned so x264 keeps the reference count inside the level's DPB (it picks 5.0 for 1080p60 otherwise)
    x264 = lambda crf, hd: ['-c:v', 'libx264', '-preset', 'slow', '-tune', 'film', '-crf', str(crf), '-profile:v', 'high',
                            '-level:v', ('4.2' if a.fps > 30 else '4.0') if hd else ('3.2' if a.fps > 30 else '3.1'),
                            '-x264-params', 'open-gop=0']
    svt = lambda crf: ['-c:v', 'libsvtav1', '-preset', str(a.av1_preset), '-crf', str(crf)] + \
        (['-svtav1-params', a.av1_params] if a.av1_params else [])
    common = ['-g', str(gop), '-keyint_min', str(gop), '-sc_threshold', '0', '-pix_fmt', 'yuv420p',
              '-colorspace', 'bt709', '-color_range', 'tv', '-movflags', '+faststart', '-an']
    s720 = 'scale=1280:720:flags=lanczos+accurate_rnd'
    jobs = []   # (file, vf, codec args, reference filter for the quality check)
    for rev in (False, True):
        for hd in (True, False):
            sfx = ('-rev' if rev else '') + ('' if hd else '-720')
            vfx = ','.join(([] if hd else [s720]) + (['reverse'] if rev else [])) or 'null'
            jobs.append((f'{slug}{sfx}.mp4', vfx, x264(a.crf if hd else a.crf720, hd)))
            jobs.append((f'{slug}{sfx}-av1.mp4', vfx, svt(a.av1_crf if hd else a.av1_crf720)))

    def encode(job):
        name, vfx, cargs = job
        out = os.path.join(vdir, name)
        t1 = time.time()
        run(['ffmpeg', '-v', 'error', '-y', '-i', master, '-vf', vfx] + cargs + common + [out])
        return name, time.time() - t1
    t = time.time()
    with ThreadPoolExecutor(a.jobs) as ex:
        took = dict(ex.map(encode, jobs))
    log(f'[{slug}] 8 encodes in {time.time() - t:.0f} s')

    # 6. stills from the 1080p H.264 file (what the page shows right before / after the clip)
    h264 = os.path.join(vdir, f'{slug}.mp4')
    nf = count_frames(h264)
    if nf != n_out:
        raise RuntimeError(f'{h264}: {nf} frames, expected {n_out}')
    dec_first, dec_last = decode_first(h264), decode_at(h264, -1)
    drift = max(abs(float(x.mean()) - float(y.mean())) for x, y in zip(planes(dec_first), planes(m0)))
    rep['h264_vs_master_plane_mean_drift'] = round(drift, 3)
    if drift > 1.0:
        raise RuntimeError(f'{h264}: first frame drifts {drift:.2f} levels from the master: colour conversion?')
    stills = {}
    for which, fr in (('first', dec_first), ('last', dec_last)):
        rgb = to_rgb(fr)
        im = Image.fromarray(rgb)
        base = os.path.join(sdir, f'{slug}-{which}')
        im.save(base + '.jpg', quality=90, subsampling=2, optimize=True, progressive=True)   # 4:2:0 like the video
        im.save(base + '.webp', quality=90, method=6)
        im.save(base + '.avif', quality=75, subsampling='4:2:0', speed=4)                      # AV1 Main profile
        for ext in ('jpg', 'webp', 'avif'):
            back = np.asarray(Image.open(f'{base}.{ext}').convert('RGB'), np.float32)
            mad = float(np.abs(back - rgb).mean())
            stills[f'{slug}-{which}.{ext}'] = {'kb': round(os.path.getsize(f'{base}.{ext}') / 1024, 1), 'mad_vs_decoded_frame': round(mad, 3),
                                               'ok': mad < 2.0}
    # how close do the other encodes land on that same still?
    last_rgb = to_rgb(dec_last).astype(np.float32)
    ends = {}
    for name in (f'{slug}-av1.mp4', f'{slug}-720.mp4', f'{slug}-720-av1.mp4'):
        d = decode_at(os.path.join(vdir, name), -1)
        ends[name + ' last frame'] = round(float(np.abs(to_rgb(d).astype(np.float32) - last_rgb).mean()), 3)
    for name in (f'{slug}-rev.mp4', f'{slug}-rev-av1.mp4', f'{slug}-rev-720.mp4', f'{slug}-rev-720-av1.mp4'):
        d = decode_first(os.path.join(vdir, name))
        ends[name + ' first frame'] = round(float(np.abs(to_rgb(d).astype(np.float32) - last_rgb).mean()), 3)
    rep['stills'] = stills
    rep['mad_vs_last_still_by_file'] = ends

    # 7. track (window outline that rides along during a flight), retimed to the new frames
    if a.track:
        path, key = a.track, ''
        if not os.path.exists(path) and ':' in path:
            path, key = path.rsplit(':', 1)
        key = key or slug.split('-')[0]
        txt = open(path, encoding='utf-8').read()
        if path.endswith('.js'):
            src_track = json.loads(txt[txt.index('{'):txt.rindex('}') + 1])[key]
        else:
            d = json.loads(txt)
            src_track = d['frames'] if isinstance(d, dict) else d
        tr = np.array(src_track, float)
        pos = t0f + np.arange(n_out) * (N - 1) / M
        new = np.stack([np.interp(pos, np.arange(len(tr)), tr[:, c]) for c in range(tr.shape[1])], 1)
        os.makedirs(os.path.join(a.out, 'tracks'), exist_ok=True)
        tpath = os.path.join(a.out, 'tracks', f'{slug}.json')
        json.dump({'key': key, 'fps': a.fps, 'frames': [[round(float(v), 5) for v in r] for r in new]}, open(tpath, 'w'),
                  separators=(',', ':'))
        rep['track'] = {'file': tpath, 'frames': len(new), 'source_frames': len(tr)}

    # 8. quality
    files = {}
    for name, vfx, _ in jobs:
        p = os.path.join(vdir, name)
        kf, nf = keyframes(p)
        files[name] = {'mb': round(os.path.getsize(p) / 1e6, 3), 'codec': codec_string(p), 'frames': nf,
                       'max_keyframe_gap_s': round(max(np.diff(kf + [nf])) / a.fps, 3), 'encode_s': round(took[name], 1)}
    if not a.no_vmaf:
        def q(job):
            name, vfx, _ = job
            return name, vmaf(os.path.join(vdir, name), master, vfx, tmp, name.replace('.mp4', ''), a.fps)
        with ThreadPoolExecutor(2) as ex:
            for name, r in ex.map(q, jobs):
                files[name].update(r)
    rep['files'] = files
    if not a.no_qc:
        t = time.time()
        rep['interp_fidelity_leave_one_out'] = loo_fidelity(make_engine(a.interp, safe), frames)
        rep['interp_fidelity_leave_one_out']['secs'] = round(time.time() - t, 1)
    rep['seconds_total'] = round(time.time() - t_start, 1)
    json.dump(rep, open(os.path.join(rdir, f'{slug}.json'), 'w'), indent=1)
    shutil.rmtree(tmp, ignore_errors=True)

    # report
    tl = rep['timeline']
    log(f'\n== {slug}: {tl["src_frames"]} src frames ({tl["src_seconds"]} s @ {src_fps:g}) -> {tl["out_frames"]} frames '
        f'@ {a.fps} fps = {tl["out_seconds"]} s (speed x{tl["speed_effective"]}), interp {a.interp}, sharpen {a.sharpen}')
    log(f'   {"file":30s} {"MB":>7s} {"codec":>15s} {"VMAF":>6s} {"min":>6s} {"PSNR-Y":>7s} {"SSIM":>7s} {"GOP s":>6s}')
    for name, f in files.items():
        log(f'   {name:30s} {f["mb"]:7.3f} {str(f["codec"]):>15s} {f.get("vmaf", float("nan")):6.2f} {f.get("vmaf_min", float("nan")):6.2f} '
            f'{f.get("psnr_y", float("nan")):7.2f} {f.get("ssim", float("nan")):7.4f} {f["max_keyframe_gap_s"]:6.3f}')
    tot = sum(f['mb'] for n, f in files.items() if not n.endswith('-av1.mp4'))
    tav = sum(f['mb'] for n, f in files.items() if n.endswith('-av1.mp4'))
    log(f'   total H.264 {tot:.2f} MB, AV1 {tav:.2f} MB ({tav / tot * 100:.0f}%)')
    for k, v in stills.items():
        log(f'   still {k:28s} {v["kb"]:7.1f} KB  MAD vs decoded frame {v["mad_vs_decoded_frame"]:.3f} {"ok" if v["ok"] else "FAIL"}')
    if 'interp_fidelity_leave_one_out' in rep:
        r = rep['interp_fidelity_leave_one_out']
        log(f'   interpolation vs real source frames (leave one out, 2x motion): PSNR-Y {r["psnr_mean"]} dB mean, '
            f'{r["psnr_min"]} min (src frame {r["psnr_min_at_src_frame"]}), worst 1% blocks {r["worst1pct_block_psnr_mean"]} dB')
    log(f'   ends bit exact: {exact}; total {rep["seconds_total"]} s; report {os.path.join(rdir, slug + ".json")}')
    if not all(v['ok'] for v in stills.values()):
        sys.exit('still check failed')


if __name__ == '__main__':
    main()
