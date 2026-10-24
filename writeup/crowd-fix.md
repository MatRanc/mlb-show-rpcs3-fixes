# How the MLB The Show 16 crowd bug was found and fixed

Game: *MLB The Show 16*, BCUS01089, update v01.10. RPCS3 v0.0.43 (Vulkan) on Fedora 44, October 2026.

This is written so that someone else, or future me, can repeat every step. The tool setup is in [../docs/setup.md](../docs/setup.md). All the scripts named below are in [../tools](../tools).

---

## 1. The symptoms

At Kauffman Stadium (and most MLB parks) the crowd is broken in ways that change as the camera moves:
- whole sections of seats are empty
- a clump of fans stands on and around the pitcher's mound, worst in replays and the batting view
- giant stretched fans appear as black slabs and bars across the screen
- rows of fans float in the sky

People on forums usually say to play in minor league parks. A Reddit user said they had fixed it with AI and Ghidra but never posted how. That's what started this.

Also noted, and not covered here: white/blank player faces are already fixed in current RPCS3. There's a post-game freeze, and black flashes on some camera pans.

## 2. Ruling out settings

The first thing tried was RPCS3 settings:
- On: Write/Read Color Buffers, Write/Read Depth Buffer, Strict Rendering Mode, Disable Vertex Cache, shader precision High.
- Shader mode: the async recompiler, and the legacy one.

None of these changed the crowd. Adding *Disable ZCull Occlusion Queries*, *Handle RSX Memory Tiling* and *Strict Texture Flushing* made the pitcher's head transparent, so those went back off.

**Lesson:** when the same glitch survives every accuracy setting, it's usually logic, not precision. Either the game takes a path RPCS3 handles wrong, or RPCS3 has a plain bug. Time for a frame capture.

## 3. Capturing a broken frame

RenderDoc captures every Vulkan call RPCS3 makes for one frame, so you can inspect each draw afterwards. Setup gotchas (details in [setup.md](../docs/setup.md#capturing-rpcs3-with-renderdoc)):
- Use the extracted AppImage binary (`--appimage-extract`), not the AppImage itself, or RenderDoc can't inject.
- Run RPCS3 under X11 (`QT_QPA_PLATFORM=xcb`). Fedora's RenderDoc has no Wayland hooks, and RPCS3 crashes with "Segfault executing location 0".
- Capture **one** frame at a time. A 10-frame capture of this game filled 32 GB of RAM.
- Save captures somewhere other than `/tmp`. Unsaved captures vanish on reboot.

Each capture is 1–1.7 GB and holds about 10,000 draws.

## 4. Finding the draws that make the glitch

**Which draw wrote these pixels?** RenderDoc's pixel history answers that. [`tools/rd_pixel_history.py`](../tools/rd_pixel_history.py) runs it headless on chosen pixels: a black bar, the mound clump, a floating row. Every glitched pixel came from draws that use **the same vertex shader**. Normal crowd sections use it too. So it's the crowd shader, and nothing else is involved.

**What does the shader do?** In RenderDoc's disassembly (or the `disassemble_shader` MCP tool), the important part, simplified:

```
a0      = floor(color.g * 255 + 0.5) * 2        // c[466] = (255, 0.5, 2)
sprite0 = c[256 + a0]                            // relative constant addressing
sprite1 = c[257 + a0]
position = seat_position + corner_offset * sprite0/sprite1 ...
```

So every fan is a quad, and the **green byte of its vertex color is a sprite ID**. The constants `c[256..355]` hold a table of 50 sprites (2 slots each). An ID of 50 or more reads past the table into unrelated constants or zeros. RPCS3 returns 0 for constant slots ≥ 468. A fan with zero scale collapses to the origin, which is the mound. One with garbage scale gets stretched into a black bar or thrown into the sky.

**Are the IDs actually bad?** RPCS3 doesn't use normal Vulkan vertex buffers. Its shader pulls attributes from two big texel buffers, using a per-draw record that describes each attribute (stride, divider, offset). [`tools/rpcs3_drawparams.py`](../tools/rpcs3_drawparams.py) decodes that record, and [`docs/rpcs3-internals.md`](../docs/rpcs3-internals.md) explains the layout. [`tools/rd_crowd_scan.py`](../tools/rd_crowd_scan.py) reads the color byte of every fan in every crowd draw:

```
sampled fans 2314, bad id (>=50) 1238 = 53.5%
```

More than half the fans had impossible sprite IDs.

## 5. A wrong first theory

The color data in bad draws looked like a slice of *another* crowd batch's data: the tail of a color array, then 16 bytes of padding, then floats. The first guess was that the game rebuilds the crowd buffer every frame and RPCS3 reads it at the wrong moment.

Ghidra killed that theory (next section): the buffer is written **once**, when the stadium loads. The data in memory is correct, so RPCS3 had to be fetching from the wrong place.

**Lesson:** check "who writes this data and when" in the game code before building on a theory about the data.

## 6. Finding the crowd code in Ghidra

The EBOOT was decrypted with RPCS3 (**Utilities → Decrypt PS3 Binaries**) and loaded into Ghidra with the PS3 scripts ([setup.md](../docs/setup.md#ghidra)). The game has no symbols, so the crowd code had to be found by its fingerprints.

**Fingerprint: the vertex attribute formats.** The draw record from step 4 shows the crowd's attributes:

| attribute | content | RSX format word |
|---|---|---|
| 0 | seat position, 3 floats, one per 4 vertices | `0x40c32` (divider 4, stride 12, size 3, float) |
| 3 | color incl. sprite ID, 4 bytes, one per 4 vertices | `0x40444` (divider 4, stride 4, size 4, ubyte) |
| 8 | quad corner, 2 floats, modulo 4 | `0x40822` (stride 8, size 2, float) |

The game has to write those words into the GPU command buffer, so they're constants in its code. [`tools/elf_find_imm.py`](../tools/elf_find_imm.py) finds all three within 0x400 bytes of each other in exactly one place, `0x9bde24`. That's inside the function that sets up a crowd draw group.

From there, cross-references (`get_xrefs_to`, `get_function_calls`) and field offsets ([`tools/elf_find_field.py`](../tools/elf_find_field.py) answers "who reads `obj+0x7e4`?") mapped out the crowd system. I named the functions:

| address | name | what it does |
|---|---|---|
| `0x9ba0f4` | `PS3Crowd_BuildVertexBuffer` | At load: builds per-batch `[colors][pad to 16][positions]`, writes `sprite ID = n mod 50`, and builds a **descending** 16-bit index table `L-1 … 0` (L = 4 × fans). |
| `0x9bdb0c` | `PS3Crowd_BeginGroup` | Uploads the sprite table and matrices, sets the attribute formats above, sets the index buffer, then emits `SET_BEGIN_END(QUADS)`. |
| `0x9bd340` | `PS3Crowd_DrawBatch` | Per batch: sets that batch's two `SET_VERTEX_DATA_ARRAY_OFFSET`s (colors, positions), then draws it (see below). |
| `0x9bd1f4` | `PS3Crowd_EndGroup` | Emits `SET_BEGIN_END(0)`. |
| `0x9c0430` | `PS3Crowd_Render` | Loops over groups: Begin, DrawBatch × N, End. |

So **one BEGIN/END wraps many batches**, and each batch changes the vertex array offsets *inside* the BEGIN/END. That's legal on the real RSX, and unusual.

`PS3Crowd_DrawBatch` picks one of four ways to draw a batch, based on two dot products between the camera direction and the batch's orientation. This is how the game sorts fans back-to-front without sorting:

| path | code at | draw |
|---|---|---|
| single forward | `0x9bd7d8` | one `DRAW_ARRAYS`, first = 0 |
| single reversed | `0x9bd54c` | one `DRAW_INDEX_ARRAY` into the descending table, first = L − 4n |
| rows back-to-front | `0x9bd600` | one `DRAW_ARRAYS` per row, `first` **descending** |
| rows back-to-front, reversed | `0x9bd6f4` | one `DRAW_INDEX_ARRAY` per row, `first` descending |

The branch that picks between them starts at `0x9bd544`.

## 7. Bug 1: rows drawn back-to-front lose their batch's data

RPCS3 doesn't send draws to Vulkan as they arrive. Between BEGIN and END it collects them in an `rsx::draw_clause` (`rpcs3/Emu/RSX/NV47/FW/draw_call.hpp` / `.cpp`):
- Each `DRAW_*` call adds a **range** `(first, count)`.
- A state change inside BEGIN/END, like a vertex array offset, becomes a **barrier** attached to a range index. It's re-applied when that range is drawn.
- `append()` keeps ranges **sorted by `first`** within the current segment. When a new range starts lower than existing ones, it's inserted in front of them with `insert_draw_command()`.

`insert_draw_command()` then shifts every barrier whose `draw_id >= index` back by one.

Walk the crowd through that:
1. Batch B sets its offsets, which adds a barrier on a new range.
2. Its first row has the highest `first`, so it takes that range.
3. Each next row has a lower `first`, so it's inserted **in front**.
4. The insert moves B's offset barrier back as well, so it now sits behind the inserted row.

At draw time, rows 2…n of B run *before* B's offsets are applied. They read batch A's memory with B's vertex numbers. That memory holds wrong seats and wrong bytes, so wrong sprite IDs. The camera decides which batches draw by rows, which is why sections break and recover as it moves.

[`tools/sim_drawclause.py`](../tools/sim_drawclause.py) is a 1:1 Python model of those functions. It shows the effect directly:

```
Bug 1, current RPCS3:
  arrays  first=  0 count= 40 -> batch A data
  arrays  first=  0 count=  8 -> batch A data     <- should be B
  arrays  first=  8 count=  8 -> batch A data     <- should be B
  arrays  first= 16 count= 12 -> batch A data     <- should be B
  arrays  first= 28 count= 12 -> batch B data
```

## 8. Patch v1.0, and why it was only half right

Fix idea: never let the game take the row-by-row paths. If each batch is one draw, nothing gets re-sorted. Before changing draw order, I checked the crowd draws' pipeline state with [`tools/rd_cull_state.py`](../tools/rd_cull_state.py): **culling off, blending off, depth test and write on**. With those settings, draw order and triangle winding don't change the picture.

v1.0 changed two branches. In game it fixed a lot: the seats behind home plate and the outfield filled in. But replays and the batting view still showed fans on the mound, and the crowd flickered when the ball was hit.

## 9. Bug 2: one draw type for the whole BEGIN/END

New captures (`replay_fans_on_mound`, `replay_no_fans`) were scanned with `rd_crowd_scan.py`. Every batch was a single draw now, so v1.0 had worked as designed. Yet half the fans were still bad. Dumping a bad draw ([`tools/rd_draw_dump.py`](../tools/rd_draw_dump.py)) showed that the "position" attribute held color bytes and the "color" attribute held floats. The reads were running far past the batch's own data.

The index data gave it away. Every bad draw used vertex numbers `1603, 1602, … 1604 − 4n`. That's entry 0 onward of the descending index table, when the batch should only have used vertices `0 … 4n−1`. In fact 106 of 113 crowd draws had `lowest vertex + vertex count = 1604` exactly.

Back to `draw_clause`: it has **one** `command` field (arrays, indexed or inline) for the whole clause. `nv4097::draw_arrays()` and `draw_index_array()` simply overwrite it on every call:
- If the last batch in a BEGIN/END is indexed, every `DRAW_ARRAYS` batch before it is replayed as indexed. Its `first = 0, count = 4n` then reads the start of the index table.
- In the reverse case, indexed batches are drawn as plain arrays from vertex `L − 4n`.

Either way, fans read memory that isn't theirs.

It also turned out that I had two of the four paths **swapped** when writing v1.0 (the disassembly at `0x9bd544`–`0x9bd548` settles it). v1.0 did remove both row paths, but it left the single forward path and the single reversed (indexed) path both active, and that's exactly the mix that triggers bug 2.

## 10. Patch v1.1: one path for everything

```
0x009bd544:  41 9a 01 ac  (beq cr6, 0x9bd6f0)   ->   48 00 02 94  (b 0x9bd7d8)
```

Every batch now jumps straight to the single forward `DRAW_ARRAYS` path:
- No descending rows, so bug 1 can't happen.
- No indexed draws, so bug 2 can't happen.

The original route from `0x9bd544` to `0x9bd7d8` went through `0x9bd6f0` without running any instruction in between, so the registers are identical. Culling is off for these draws, so the forward winding doesn't matter.

Tested in game: the crowd renders correctly in gameplay, from the batting view and in replays.

## 11. What's left

- **A possible third issue.** In one capture (`replay_sky_fans`), 10 small batches of 6–16 fans (0.5% of the crowd) read floats as colors. Their color offset points just before a crowd object's header block. That's a different pattern, not explained yet. It may be what's left of the "fans in the sky" in rare shots.
- **Upstream.** Bug 1 has a two-line fix candidate in `insert_draw_command()`: keep execution barriers on the range they were attached to, and move only primitive-restart barriers. Bug 2 needs the clause to split, or to record the draw type per range, when the type changes inside BEGIN/END. Both fixes are written up as a commit on [MatRanc/rpcs3 `fix-mlb-crowd-draw-clause`](https://github.com/MatRanc/rpcs3/commits/fix-mlb-crowd-draw-clause). It's not built or tested; it's a starting point for RPCS3 developers, not a PR. These bugs are probably behind [issue #14731](https://github.com/RPCS3/rpcs3/issues/14731) ("MLB The Show 16 artifacting").
- **Other MLB years.** MLB 11–15 likely share this crowd code. The same fingerprint search (the three attribute formats) should find it at different addresses.

## Dead ends worth knowing about

- MLB 11 logs "Invalid transform register index" warnings that people link to the crowd. MLB 16 doesn't log them, so they're unrelated here.
- RPCS3's own `.rrc` capture (Alt+C) is useful for sharing a frame, but it replays the whole frame with no draw-by-draw inspection. Use RenderDoc for analysis.
- The Ghidra decompiler's `???`s and odd variable names are normal for PS3 code. The disassembly is the ground truth. Check branch targets there before patching, because a mislabeled branch is exactly what made v1.0 incomplete.
