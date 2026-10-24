"""Decode RPCS3's per-draw vertex layout from a RenderDoc capture (Vulkan backend).

RPCS3 does not use Vulkan vertex buffers. Its vertex shader pulls attributes out of two texel
buffers (persistent / volatile streams) using a per-draw record in a storage buffer
(DrawParametersBuffer). The push constant's first u32 selects the record. Layout, as of
RPCS3 v0.0.3x-0.0.4x (check rpcs3/Emu/RSX/VK/VKVertexProgram / the GLSL "attrib_data" if it breaks):

  u32 vertex_base_index, vertex_index_offset, draw_id, xform_constants_offset, ...
  at byte 40: 16 x (u32 x, u32 y) attribute descriptors
     x: stride[0:8] frequency[8:24] type[24:27] size[27:30]
     y: start_offset[0:29] swap_bytes[29] volatile[30] modulo[31]
"""
import struct
from rd_common import rd

RECORD_SIZE = 168
TYPES = {1: 'snorm16', 2: 'float', 3: 'half', 4: 'unorm8', 5: 'sint16', 6: 'cmp', 7: 'uint8'}


def draw_params(ctrl):
    """Call after ctrl.SetFrameEvent(eid). Returns dict with header words, attributes and helpers."""
    st = ctrl.GetPipelineState(); vk = ctrl.GetVulkanPipelineState()
    if len(vk.pushconsts) < 4:
        return None
    push = struct.unpack_from('<I', bytes(vk.pushconsts), 0)[0]
    rw = {b.access.index: b.descriptor for b in st.GetReadWriteResources(rd.ShaderStage.Vertex)}
    ro = {b.access.index: b.descriptor for b in st.GetReadOnlyResources(rd.ShaderStage.Vertex)}
    cbs = {b.access.index: b.descriptor for b in st.GetConstantBlocks(rd.ShaderStage.Vertex)}
    if not rw:
        return None
    dp = rw.get(0) or next(iter(rw.values()))
    raw = ctrl.GetBufferData(dp.resource, dp.byteOffset + push * RECORD_SIZE, RECORD_SIZE)
    if len(raw) < RECORD_SIZE:
        return None
    vbase, vidxoff, draw_id, xoff = struct.unpack_from('<4I', raw, 0)
    attrs = {}
    for loc in range(16):
        x, y = struct.unpack_from('<2I', raw, 40 + 8 * loc)
        if x == 0 and y == 0:
            continue
        attrs[loc] = dict(stride=x & 0xff, freq=(x >> 8) & 0xffff, type=(x >> 24) & 7, size=(x >> 27) & 7,
                          start=y & 0x1fffffff, swap=(y >> 29) & 1, volatile=(y >> 30) & 1, modulo=(y >> 31) & 1)

    def attr_bytes(loc, element, n):
        """Raw bytes of `n` bytes starting at stream element `element` for attribute `loc`."""
        a = attrs[loc]; s = ro[1 if a['volatile'] else 0]
        return ctrl.GetBufferData(s.resource, s.byteOffset + a['start'] + element * a['stride'], n)

    def vconst(i):
        """Vertex program constant c[i] as 4 floats (RPCS3 returns 0 for i >= 468)."""
        if 1 not in cbs:
            return None
        b = ctrl.GetBufferData(cbs[1].resource, cbs[1].byteOffset + (xoff + i) * 16, 16)
        return struct.unpack('<4f', b) if len(b) == 16 else None

    return dict(vbase=vbase, vidxoff=vidxoff, draw_id=draw_id, xoff=xoff, attrs=attrs,
                attr_bytes=attr_bytes, vconst=vconst)


def element_of(a, vertex, vbase, vidxoff):
    """Which stream element a vertex index reads for attribute descriptor `a` (mirrors the shader)."""
    if a['freq'] == 0:
        return 0
    if a['modulo']:
        return (vertex + vidxoff) % a['freq']
    return (vertex - vbase) // a['freq']


def vertex_indices(ctrl, d):
    """Vertex indices used by draw `d` (after RPCS3's own quad->triangle expansion)."""
    if not d.flags & rd.ActionFlags.Indexed:
        return list(range(d.vertexOffset, d.vertexOffset + d.numIndices))
    ib = ctrl.GetPipelineState().GetIBuffer(); w = ib.byteStride or 4
    raw = ctrl.GetBufferData(ib.resourceId, ib.byteOffset + d.indexOffset * w, d.numIndices * w)
    restart = 0xffff if w == 2 else 0xffffffff
    return [i + d.baseVertex for i in struct.unpack('<%d%s' % (d.numIndices, 'H' if w == 2 else 'I'), raw) if i != restart]
