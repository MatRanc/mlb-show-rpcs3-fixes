"""Which draws wrote a pixel? Prints the last few passing writes for each (x,y).

usage: python rd_pixel_history.py capture.rdc X,Y [X,Y ...]
The target is the colour output of the frame's last draw; pass coordinates in that image's pixels
(open the PNG from rd_final_frame.py to pick them).
"""
import sys
from rd_common import *

cap, ctrl = open_capture(sys.argv[1])
ds = draws(ctrl); by_id = {d.eventId: d for d in ds}
last = [d for d in ds if d.outputs[0] != rd.ResourceId.Null()][-1]
ctrl.SetFrameEvent(last.eventId, True)
for xy in sys.argv[2:]:
    x, y = map(int, xy.split(','))
    hist = ctrl.PixelHistory(last.outputs[0], x, y, rd.Subresource(0, 0, 0), rd.CompType.Typeless)
    passed = [h for h in hist if h.Passed()]
    print(f'== ({x},{y}) writes={len(hist)} passed={len(passed)}')
    for h in passed[-4:]:
        d = by_id.get(h.eventId)
        ctrl.SetFrameEvent(h.eventId, False)
        vs = ctrl.GetPipelineState().GetShader(rd.ShaderStage.Vertex)
        print(f'   event {h.eventId} indices={d.numIndices if d else "?"} vs={vs}')
close(cap, ctrl)
