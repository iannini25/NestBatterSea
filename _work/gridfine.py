import sys
from PIL import Image, ImageDraw
x0,y0,x1,y1=map(int,sys.argv[1:5]); out=sys.argv[5]; W=int(sys.argv[6]); step=int(sys.argv[7])
t=Image.open('frames/tower_up.png'); s=t.width/680
c=t.crop((round(x0*s),round(y0*s),round(x1*s),round(y1*s))).convert('RGB')
sc=W/c.width; c=c.resize((W,int(c.height*sc)),Image.LANCZOS)
d=ImageDraw.Draw(c)
for x in range((x0//step+1)*step,x1,step):
    X=(x-x0)*s*sc; major=x%10==0
    d.line([(X,0),(X,c.height)],fill=(255,0,255) if major else (0,200,255),width=1)
    if major: d.text((X+2,2),str(x),fill=(255,255,0))
for y in range((y0//step+1)*step,y1,step):
    Y=(y-y0)*s*sc; major=y%10==0
    d.line([(0,Y),(c.width,Y)],fill=(255,0,255) if major else (0,200,255),width=1)
    if major: d.text((2,Y+2),str(y),fill=(255,255,0))
c.save(out,quality=90)
