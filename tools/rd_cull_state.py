"""Print cull / blend / depth state for some draws (is it safe to change their order or winding?).

usage: python rd_cull_state.py capture.rdc EID[,EID...]
"""
import sys
from rd_common import *

cap, ctrl = open_capture(sys.argv[1])
for eid in map(int, sys.argv[2].split(',')):
    ctrl.SetFrameEvent(eid, True)
    vk = ctrl.GetVulkanPipelineState()
    r, ds = vk.rasterizer, vk.depthStencil
    blend = [b.enabled for b in vk.colorBlend.blends]
    print(f'event {eid}: cull={r.cullMode} frontCCW={r.frontCCW} blend={blend} '
          f'depthTest={ds.depthTestEnable} depthWrite={ds.depthWriteEnable}')
close(cap, ctrl)
