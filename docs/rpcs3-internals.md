# RPCS3 / RSX cheat sheet

Just enough of the PS3 GPU (RSX) and RPCS3's implementation to read a capture and the game code. Verified against RPCS3 v0.0.43 source. Paths are relative to the RPCS3 repo.

## RSX commands (GCM methods) worth recognising

The game writes commands into a FIFO as `header, args...`. The header is `(count << 18) | method`; bit 30 set means "same register for all args" (non-incrementing).

| method | name | args |
|---|---|---|
| `0x1680 + 4*i` | `SET_VERTEX_DATA_ARRAY_OFFSET` (attribute i) | offset; bit 31 = main memory |
| `0x1740 + 4*i` | `SET_VERTEX_DATA_ARRAY_FORMAT` (attribute i) | `freq<<16 \| stride<<8 \| size<<4 \| type` |
| `0x1fc0` | `SET_FREQUENCY_DIVIDER_OPERATION` | bit i = attribute i uses modulo instead of divide |
| `0x1808` | `SET_BEGIN_END` | primitive (8 = QUADS), 0 = end |
| `0x1814` | `DRAW_ARRAYS` | `(count-1)<<24 \| first`, one word per ≤256 vertices |
| `0x1824` | `DRAW_INDEX_ARRAY` | same encoding, in indices |
| `0x181c` | `SET_INDEX_ARRAY_ADDRESS` + `_DMA` | address; format (`0x10` = u16, bit 0 = location) |
| `0x1738` / `0x173c` | `SET_VERTEX_DATA_BASE_OFFSET` / `_BASE_INDEX` | |
| `0x1efc`, `0x1f00…` | transform constant load / upload | vertex program constants `c[]` |

Attribute types: 1 snorm16, 2 float, 3 half, 4 unorm8, 5 sint16, 6 cmp, 7 uint8.

On real hardware, a state change between draws inside one `SET_BEGIN_END` simply takes effect for the next draw. RPCS3 has to emulate that (see `draw_clause` below), and that's where both crowd bugs live.

## How vertex data looks in a RenderDoc capture

RPCS3 (Vulkan) doesn't bind Vulkan vertex buffers. The vertex shader fetches attributes itself:
- Two texel buffers: `persistent_input_stream` and `volatile_input_stream`. The PS3 vertex data is copied into these each draw.
- A storage buffer of per-draw records (`DrawParametersBuffer`). The first push constant u32 selects this draw's record. Each record is 168 bytes:
  ```
  +0   u32 vertex_base_index      // usually the lowest vertex index of the draw
  +4   u32 vertex_index_offset
  +8   u32 draw_id
  +12  u32 xform_constants_offset // into the vertex constants buffer, in vec4s
  +40  16 × { u32 x, u32 y }      // attribute descriptors
         x: stride[0:8]  frequency[8:24]  type[24:27]  size[27:30]
         y: start_offset[0:29]  swap_bytes[29]  volatile[30]  modulo[31]
  ```
- Element read for vertex `v`:
  - modulo: `(v + vertex_index_offset) % freq`
  - otherwise: `(v - vertex_base_index) / freq`
  - The byte address is `start_offset + element * stride` in the selected stream.
- Vertex program constants are in a uniform buffer starting at `xform_constants_offset`. RPCS3 returns 0 for indices ≥ 468.

`tools/rpcs3_drawparams.py` implements all of this. If a newer RPCS3 changes the record, look for `attrib_data` / `DrawParametersBuffer` in `rpcs3/Emu/RSX/Program/GLSLSnippets/` and the VK vertex program code.

Index buffers in the capture are RPCS3's converted ones: QUADS are expanded to triangles, 6 indices per quad. The *values* are still the game's vertex numbers.

## `rsx::draw_clause`: how RPCS3 batches a BEGIN/END

Files: `rpcs3/Emu/RSX/NV47/FW/draw_call.hpp`, `draw_call.cpp`, `draw_call.inc.h`; called from `rpcs3/Emu/RSX/NV47/HW/nv4097.cpp`.

- `begin`: resets the clause.
- `DRAW_ARRAYS` / `DRAW_INDEX_ARRAY` call `append(first, count)`:
  - **Sets `command` (arrays/indexed) for the whole clause. The last call wins** (crowd bug 2).
  - If the range continues the previous one, it extends it.
  - Otherwise it keeps ranges sorted by `first` within the current segment, inserting with `insert_draw_command()` (crowd bug 1: that shifts barriers with `draw_id >= index`).
- State changes inside BEGIN/END (vertex array offset, base offset/index, transform constants) go through `util::push_draw_parameter_change()`. It rolls the register back and records a **barrier** (`insert_command_barrier`) on the current range. Execution barriers start a new range.
- `end`: the backend (`VKGSRender`) loops over the ranges. Before each one, `execute_pipeline_dependencies()` re-applies that range's barriers.

So anything that reorders ranges, or treats the whole clause uniformly, can break games that change state between draws inside one BEGIN/END. Sony's engines do this a lot.

## Other places to look, by symptom

| symptom | look at |
|---|---|
| geometry exploding / wrong positions | vertex fetch (`rsx_vertex_data`, `VKVertexBuffers.cpp`), draw clause, constants upload (`nv4097::set_transform_constant`) |
| wrong textures / stale images | texture cache (`rpcs3/Emu/RSX/Common/texture_cache*.h`), "Strict Texture Flushing" |
| missing or flickering objects | ZCull / occlusion queries (`RSXZCULL.cpp`), conditional render |
| black frames / flashes | surface (render target) cache, `Write Color Buffers` |
| wrong lighting or exposure, blank generated textures | the game reading GPU renders back on the CPU. Without `Write Color Buffers` RPCS3 never writes them to memory, so the game reads stale data. Results the game saves to disk stay wrong after the fix (MLB 16's `HeadFaceCacheFile`) |
