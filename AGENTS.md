# AGENTS.md: hunting RPCS3 graphics bugs in MLB The Show

Instructions for an AI coding agent (Claude Code or similar) helping a human find and fix RPCS3 rendering bugs in *MLB The Show* PS3 games, using Ghidra and RenderDoc through MCP. A human is in the loop: they play the game, take captures, and test patches.

Read first: [writeup/crowd-fix.md](writeup/crowd-fix.md) (a complete worked example), [docs/workflow.md](docs/workflow.md), [docs/rpcs3-internals.md](docs/rpcs3-internals.md).

## Environment

- **Ghidra 12.1.2** with Ps3GhidraScripts and GhidraMCP (HTTP on `127.0.0.1:8080`). The human must have the EBOOT open in **CodeBrowser** for the MCP to work.
  - Call `get_program_info` first, to check you're on the right binary.
  - Language must be `PowerISA-Altivec-64-32addr`.
  - Don't suggest upgrading Ghidra. The PS3 extension is pinned to 12.1.2.
- **RenderDoc MCP** (headless, opens `.rdc` files). Captures are 1–2 GB.
  - Open one at a time.
  - `close_capture` before running a script on the same file, or the GPU runs out of memory.
- **Scripts** in `tools/` need `RENDERDOC_MODULE_PATH` set. The generic MCP vertex tools don't understand RPCS3's vertex pulling; use `tools/rpcs3_drawparams.py`.
- **RPCS3 source:** clone it shallow, and read the files named in `docs/rpcs3-internals.md` before theorising about emulator behavior.

## Method

Follow `docs/workflow.md`. Key rules learned the hard way:

1. **Evidence before theory.** Before saying why something is wrong, show the bad values in the capture: the specific attribute bytes, index values, constants. Quantify it ("54% of fans have sprite ID ≥ 50"), and keep the scanner script so the number can be re-measured after the fix.
2. **Check who writes the data and when** (Ghidra xrefs on the buffer / field) before blaming timing or stale data. The crowd's "per-frame buffer" theory was wrong: the buffer is written once at load.
3. **Read the disassembly before patching.** Decompiler control flow and your own labels can be wrong. The first crowd patch was incomplete because two of four branch targets were mislabeled. List each branch's address, target and what the target code emits.
4. **Model RPCS3 logic in Python** to confirm a theory (`tools/sim_drawclause.py`) before claiming it.
5. **Verify every patch target's original bytes** against the EBOOT, and put them in the patch comment.
6. **Prefer patches that steer the game onto an existing path.** Check render state (blend, cull, depth) to show the alternative path draws the same image.
7. **Test in game is the only proof.** Ask the human to test the same situations that were broken, plus others (replays, other cameras, other parks), and to recapture.
8. **Rename and comment in Ghidra as you go** (`rename_function_by_address`, `set_decompiler_comment`), and remind the human to save the project.

## Finding code quickly

- RSX register values seen in the capture → `tools/elf_find_imm.py` (look for clusters).
- Shader constant names → `list_strings` in Ghidra (the engine looks up `UVP_*` names).
- A known struct field → `tools/elf_find_field.py`, then xrefs.
- Known crowd system in MLB 16 v01.10: `PS3Crowd_Render 0x9c0430`, `PS3Crowd_BeginGroup 0x9bdb0c`, `PS3Crowd_DrawBatch 0x9bd340`, `PS3Crowd_EndGroup 0x9bd1f4`, `PS3Crowd_BuildVertexBuffer 0x9ba0f4`. Other MLB years likely have the same functions at different addresses. Find them via the attribute formats `0x40c32 / 0x40444 / 0x40822`.

## Boundaries

- Never commit or publish game files: EBOOT (encrypted or decrypted), Ghidra projects, captures (`.rdc`, `.rrc`), or large decompiled listings. Short excerpts that explain logic are fine.
- RPCS3's contribution policy: AI-assisted research is allowed. Issues, comments and PRs must be written and posted **by the human**. Don't post to RPCS3 on their behalf; draft facts for them to use instead. Open an issue before any PR.
- Don't change the user's RPCS3 config without saving a backup. Some "accuracy" settings break other things (transparent heads).
- Capture one frame at a time. Multi-frame captures can exhaust RAM.

## Open leads (MLB 16)

- A few small crowd batches in rare replay shots read floats as colors: color offset just before a crowd object's header. See the writeup, §11.
- A post-game freeze.
- Black flashes on some camera pans.
- A mid-game RPCS3 crash, seen once (Oct 25, 2026, online game, accuracy settings on): the RSX thread hit a fatal "Verification failed" in
  `rsx::expected<rsx::surface_color_format>` (the game set a surface color format RPCS3 doesn't know, value 0), right after a
  FIFO `call` to 0x0549fa0. The emulation froze; the log is kept locally, not in this repo.
- Porting the crowd patch to MLB 11–15 and other regions.
