from PIL import Image
import numpy as np
def load(name):
    im = Image.open('../../_refs/plantas-oficiais/%s.png' % name).convert('RGBA')
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert('RGB')
