# Workflow: from a glitch to a patch

The general loop used for the crowd fix. It should work for most RPCS3 graphics bugs in the MLB The Show games, and in other Sony first-party PS3 titles. [../writeup/crowd-fix.md](../writeup/crowd-fix.md) is a full worked example of every step.

```
 reproduce ──► capture ──► find the draw ──► decode its inputs ──► find the game code
     ▲                                                                  │
     │                                                                  ▼
  verify  ◄── patch ◄── decide: game patch and/or RPCS3 fix ◄── understand the mismatch
```

## 1. Reproduce and describe

- Find a spot where the glitch shows reliably: a stadium, a camera, a replay.
- Write down what changes it. Does camera movement change it? Time? Which settings?
- Try RPCS3's accuracy settings once (Write Color/Depth Buffers, Strict Rendering, shader precision, etc.).
  - If one of them fixes it, you're done: it's a config, not a patch. Then turn the others back off one at a time: in MLB 16 only Write Color Buffers mattered, and the other buffer options plus Disable Vertex Cache cut dugout close-ups from 30–40 FPS to 7–11.
  - If nothing changes it, it's logic, so keep going.
  - Check the settings really applied: RPCS3's settings window can re-save the game's custom config over your edit. `RPCS3.log` prints the full config at boot.
  - A fix may not show right away if the game saved the broken result to disk. MLB 16 renders generated faces on the GPU once and caches them in `HeadFaceCacheFile`; faces built without Write Color Buffers stay white until that file is deleted.

## 2. Capture

- Take one RenderDoc frame per symptom and name the file for the symptom (see [setup.md](setup.md#capturing-rpcs3-with-renderdoc)).
- Also capture a frame where things look right. It's useful for comparison.
- Export what the frame looks like with `tools/rd_final_frame.py capture.rdc out.png`.

## 3. Find the draw that's wrong

- Pick pixels that are obviously wrong and run `tools/rd_pixel_history.py capture.rdc X,Y ...`, or use the MCP `pixel_history` tool. Note the event IDs and the vertex shader.
- If many glitch pixels share a shader, look at that shader. Pull its disassembly (RenderDoc, or the MCP `disassemble_shader` tool).
- Translate the shader into a few lines of pseudo-code. Look for:
  - **relative constant indexing** (`c[a0 + N]`), the classic way a bad byte turns into a wild vertex
  - attributes with a frequency divider or modulo (instancing-style data)
  - texture coordinates derived from vertex data

## 4. Decode the draw's inputs

RPCS3's vertex pulling hides the real inputs from RenderDoc's normal mesh viewer. Use `tools/rpcs3_drawparams.py`; [rpcs3-internals.md](rpcs3-internals.md) explains the layout.

- `tools/rd_draw_dump.py capture.rdc EID` shows every attribute's stride, divider, type and first bytes.
- Ask: **is the input data wrong, or is RPCS3 reading it from the wrong place?**
  - Check for impossible values (the crowd's sprite IDs ≥ 50).
  - Check for data that looks like it belongs to another attribute (floats where bytes should be).
- Write a scanner for your symptom across the whole frame. `tools/rd_crowd_scan.py` is the crowd's. Percentages and patterns, like "every bad draw starts at 1604 − 4n", point straight at the cause.

## 5. Find the game code

The EBOOT has no symbols. Find code by its fingerprints:

| fingerprint | how |
|---|---|
| RSX register values you saw (vertex formats, blend modes, …) | `tools/elf_find_imm.py EBOOT.elf 0x40c32,...` (low 16 bits; search several and look where they cluster) |
| GCM method numbers (`0x1680` vertex offset, `0x1824` indexed draw, …) | same tool; also look for calls to the libgcm inline helpers |
| Shader constant names | Many Sony engines look constants up by string (`"UVP_SpriteTable"`). Search strings in Ghidra (`list_strings`) |
| Struct fields | once you know one field (`obj+0x7e4`), `tools/elf_find_field.py` finds every reader and writer |

Then walk outward with xrefs (`get_xrefs_to`, `get_function_calls`):
- Rename functions as you understand them (`rename_function_by_address`).
- Comment the key instructions (`set_decompiler_comment`).
- Save the project.

Read the disassembly around anything you plan to patch (`tools/elf_disasm.py`). The decompiler's control flow can mislead you about which branch goes where.

## 6. Understand the mismatch

You now know what the game asks the RSX to do (from the code) and what RPCS3 actually drew (from the capture). Find where they diverge:
- Read the relevant RPCS3 source. The usual suspects are listed in [rpcs3-internals.md](rpcs3-internals.md).
- Model it. A small Python replica of the RPCS3 function fed the game's command pattern (`tools/sim_drawclause.py`) proves the theory without rebuilding the emulator.
- Check that the game's data is really static or really dynamic before blaming timing.

## 7. Decide what to fix

- **Game patch:** steer the game onto a code path RPCS3 handles correctly. It's quick, safe and per-game. Check that the alternative path draws the same image: blend/cull/depth state via `tools/rd_cull_state.py`.
- **RPCS3 fix:** fixes every game, but has to be built, tested across games and accepted upstream. Read RPCS3's CONTRIBUTING first: open an issue before a PR, AI-assisted research is allowed, and communication must be your own.
- Often you'll want both: the patch now, the RPCS3 fix later.

How to write and test the patch is in [patching.md](patching.md).

## 8. Verify

- Play the spot from step 1 with the patch on.
- Capture the same shots again and re-run your scanner. The crowd went from 54% bad fans to 0.
- Look at other cameras and situations too. The crowd fix needed a second round because v1.0 only fixed gameplay cameras.
