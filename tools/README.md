# Tools

Small, single-purpose scripts used for the crowd fix. They're meant to be read and adapted, not to be a framework.

**RenderDoc replay scripts.** These need `RENDERDOC_MODULE_PATH` pointing at the folder with `renderdoc.so` / `.pyd`, and a matching Python (see [../docs/setup.md](../docs/setup.md)).

| script | does |
|---|---|
| `rd_common.py` | open a capture, list draws, save PNGs |
| `rpcs3_drawparams.py` | decode RPCS3's per-draw vertex attribute records and vertex constants |
| `rd_final_frame.py capture.rdc out.png` | save what the frame looks like |
| `rd_pixel_history.py capture.rdc X,Y ...` | which draws (and vertex shaders) wrote these pixels |
| `rd_draw_dump.py capture.rdc EID[,EID] [attrs]` | attribute layout and first bytes for some draws |
| `rd_cull_state.py capture.rdc EID[,EID]` | cull / blend / depth state |
| `rd_crowd_scan.py capture.rdc` | MLB 16 crowd: per-draw count of fans with bad sprite IDs |

**EBOOT scripts.** These read a decrypted `EBOOT.elf`. `elf_disasm.py` needs `pip install capstone`.

| script | does |
|---|---|
| `ps3elf.py` | maps virtual addresses to file bytes |
| `elf_find_imm.py EBOOT.elf 0x0c32,0x0444` | instructions loading these 16-bit immediates, plus where they cluster |
| `elf_find_field.py EBOOT.elf 0x7e4` | loads/stores of a struct field offset |
| `elf_disasm.py EBOOT.elf START END` | disassemble a range |
| `ppc_branch.py ADDR TARGET` | encode `b TARGET` at ADDR for a patch |

**Models**

| script | does |
|---|---|
| `sim_drawclause.py` | Python replica of RPCS3's `draw_clause` showing both crowd bugs (self-checking) |

The RenderDoc scripts were written against RenderDoc 1.45 and RPCS3 v0.0.43 (Vulkan).
