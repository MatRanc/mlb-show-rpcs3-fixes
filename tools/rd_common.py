"""Shared helpers for the RenderDoc replay scripts.

Set RENDERDOC_MODULE_PATH to the folder that holds renderdoc.so (or renderdoc.pyd on Windows).
"""
import os, sys
sys.path.insert(0, os.environ.get('RENDERDOC_MODULE_PATH', '.'))
import renderdoc as rd


def open_capture(path):
    rd.InitialiseReplay(rd.GlobalEnvironment(), [])
    cap = rd.OpenCaptureFile()
    assert cap.OpenFile(path, '', None) == rd.ResultCode.Succeeded, 'cannot open ' + path
    res, ctrl = cap.OpenCapture(rd.ReplayOptions(), None)
    assert res == rd.ResultCode.Succeeded, res
    return cap, ctrl


def close(cap, ctrl):
    ctrl.Shutdown(); cap.Shutdown(); rd.ShutdownReplay()


def draws(ctrl):
    """Every draw call in the frame, in submission order."""
    out = []
    def walk(actions):
        for a in actions:
            if a.flags & rd.ActionFlags.Drawcall:
                out.append(a)
            walk(a.children)
    walk(ctrl.GetRootActions())
    return out


def save_png(ctrl, resource_id, path):
    s = rd.TextureSave(); s.resourceId = resource_id; s.destType = rd.FileType.PNG
    s.alpha = rd.AlphaMapping.Discard
    ctrl.SaveTexture(s, path)
