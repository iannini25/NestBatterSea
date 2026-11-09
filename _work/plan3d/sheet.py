# contact sheet: python sheet.py out.jpg cols w h img1 img2 ...
import sys
from PIL import Image
out, cols, w, h = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
files = sys.argv[5:]
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (w * cols, h * rows), (20, 20, 26))
for i, f in enumerate(files):
    sheet.paste(Image.open(f).convert('RGB').resize((w, h)), ((i % cols) * w, (i // cols) * h))
sheet.save(out, quality=88)
print(out, sheet.size)
