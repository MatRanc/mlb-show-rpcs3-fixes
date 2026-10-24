"""Dump RPCS3's vertex attribute layout and the first bytes of chosen attributes for some draws.

usage: python rd_draw_dump.py capture.rdc EID[,EID...] [ATTR,ATTR]   (default attrs 0,3)
"""
import sys
from rd_common import *
from rpcs3_drawparams import draw_params, vertex_indices, TYPES

cap, ctrl = open_capture(sys.argv[1])
ds = {d.eventId: d for d in draws(ctrl)}
show = [int(a) for a in (sys.argv[3] if len(sys.argv) > 3 else '0,3').split(',')]
for eid in map(int, sys.argv[2].split(',')):
    d = ds[eid]; ctrl.SetFrameEvent(eid, True)
    p = draw_params(ctrl)
    idx = vertex_indices(ctrl, d)
    print(f'=== event {eid}: {d.numIndices} indices, vertex range {min(idx)}..{max(idx)}, vbase={p["vbase"]}')
    print('    first indices:', idx[:12])
    for loc, a in p['attrs'].items():
        print(f'  attr{loc}: stride={a["stride"]} freq={a["freq"]} type={TYPES.get(a["type"], a["type"])} size={a["size"]}'
              f' start={a["start"]} modulo={a["modulo"]}')
        if loc in show:
            print('      ', p['attr_bytes'](loc, 0, 64).hex(' ', 4))
close(cap, ctrl)
