"""Save the colour target of the last draw in a capture as a PNG (a quick "what did this frame look like").

usage: python rd_final_frame.py capture.rdc out.png
"""
import sys
from rd_common import *

cap, ctrl = open_capture(sys.argv[1])
last = [d for d in draws(ctrl) if d.outputs[0] != rd.ResourceId.Null()][-1]
ctrl.SetFrameEvent(last.eventId, True)
save_png(ctrl, last.outputs[0], sys.argv[2])
print('saved', sys.argv[2], 'from event', last.eventId)
close(cap, ctrl)
