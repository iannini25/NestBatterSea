"""Re-write an untagged (BT.601 written) master as BT.709 limited yuv444p, the way finish_video2 reads masters."""
import sys, subprocess, cv2
src, dst = sys.argv[1:3]
cap = cv2.VideoCapture(src)
ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '1920x1080', '-r', '60', '-i', '-',
                       '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv444p', '-c:v', 'ffv1', '-level', '3',
                       '-colorspace', 'bt709', '-color_range', 'tv', dst], stdin=subprocess.PIPE)
n = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    ff.stdin.write(f.tobytes()); n += 1
ff.stdin.close(); ff.wait(); print(dst, n)
