"""MLB The Show 16: find every crowd draw in a capture and report how many fans read a bad sprite ID.

The crowd vertex program builds a0 = floor(color.y * c[466].x + c[466].y) * c[466].z with
c[466] = (255, 0.5, 2), then reads sprite data at c[256 + a0]. The game only writes IDs 0..49, so a
green byte >= 50 means the fan is reading data that isn't its own.

usage: python rd_crowd_scan.py capture.rdc [color_attr=3]
Output: one line per crowd draw:
  (event, fans, bad, vertex_min, vertex_min + vertices)  <- the last column is the index-table length
                                                          if the draw was replayed as indexed
"""
import sys
from rd_common import *
from rpcs3_drawparams import draw_params, vertex_indices, element_of

COLOR = int(sys.argv[2]) if len(sys.argv) > 2 else 3
cap, ctrl = open_capture(sys.argv[1])
rows = []
for d in draws(ctrl):
    ctrl.SetFrameEvent(d.eventId, True)
    p = draw_params(ctrl)
    if not p or COLOR not in p['attrs']:
        continue
    c466 = p['vconst'](466)
    if not c466 or abs(c466[0] - 255) > 0.01 or abs(c466[2] - 2) > 0.01:
        continue
    a = p['attrs'][COLOR]
    corners = sorted(set(vertex_indices(ctrl, d)))[::4]   # one vertex per quad is enough
    if not corners or not a['freq']:
        continue
    els = [element_of(a, v, p['vbase'], p['vidxoff']) for v in corners]
    lo, hi = min(els), max(els)
    blob = p['attr_bytes'](COLOR, lo, (hi - lo + 1) * a['stride'])
    ids = [blob[(e - lo) * a['stride'] + 1] for e in els if (e - lo) * a['stride'] + 1 < len(blob)]
    bad = sum(i >= 50 for i in ids)
    nverts = len(corners) * 4
    rows.append((d.eventId, len(ids), bad, corners[0], corners[0] + nverts))
fans = sum(r[1] for r in rows); bad = sum(r[2] for r in rows)
print(f'crowd draws {len(rows)}, fans {fans}, bad sprite ids {bad} ({100 * bad / max(fans, 1):.1f}%), '
      f'draws with any bad {sum(1 for r in rows if r[2])}')
for r in rows:
    print(r)
close(cap, ctrl)
