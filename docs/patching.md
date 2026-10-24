# Writing and testing an RPCS3 game patch

## The format

RPCS3 patch files are YAML (format version 1.2). User patches live in `<rpcs3 config>/patches/imported_patch.yml`. Linux: `~/.config/rpcs3/patches/`. Windows: the RPCS3 folder's `patches\`.

```yaml
Version: 1.2

PPU-395faa2b9c12c400d03343cad62ce7aad8ec985b:      # executable hash, from the RPCS3 log
  "Crowd fix (single-draw crowd batches)":           # patch name shown in the Patch Manager
    Games:
      "MLB The Show 16":
        BCUS01089: [ 01.10 ]                         # serial: [ app versions ]
    Author: "you"
    Notes: "what it does and why"
    Patch Version: 1.1
    Patch:
      - [ be32, 0x009bd544, 0x48000294 ]             # type, address, value
```

- **The hash:** boot the game once and search the log (`RPCS3.log`) for `PPU executable hash`. It identifies the exact EBOOT, so a patch never applies to the wrong version.
- **Addresses** are virtual addresses as shown in Ghidra (EBOOT loaded at its normal base).
- **Types:** `be32` writes one big-endian 32-bit word (one PowerPC instruction). That's what you'll use most. There are also `be16`, `byte`, `bef32`, `utf8`, and more; see the [RPCS3 wiki on patches](https://wiki.rpcs3.net/index.php?title=Help:Game_Patches).

## Encoding the usual instruction changes

| change | value |
|---|---|
| remove an instruction | `nop` = `0x60000000` |
| conditional branch → always | `b target` = `0x48000000 \| ((target - addr) & 0x03fffffc)`; `tools/ppc_branch.py addr target` computes it |
| conditional branch → never | `nop` |
| `li rX, imm` (change a constant) | `0x38000000 \| rX<<21 \| (imm & 0xffff)` |

Always check the original word first (`tools/elf_disasm.py EBOOT.elf addr addr+4`) and write it in a comment. That way you can verify your target, and others can check your patch against their EBOOT.

## Choosing *what* to patch

The safest patches **steer the game onto a code path it already has**, rather than inventing new behavior:
- Prefer a branch change over rewriting logic.
- Before jumping from A to B, check that no instruction between them sets registers B relies on. The crowd patch jumps from `0x9bd544` to `0x9bd7d8`, and the original route went `544 → 6f0 → 7d8` with nothing executed in between.
- Check the rendering consequences in a capture. Changing draw order or winding is only safe if blending and culling allow it (`tools/rd_cull_state.py`).

## Testing

1. Put the patch in `imported_patch.yml`, or drag the file onto **Manage → Game Patches**.
2. Tick it in **Manage → Game Patches** and save.
3. Boot the game. The log lists applied patches (`Applied patch …`) right after the PPU hash.
4. Reproduce every situation from your bug notes, not just the first one.
5. Capture the same shots and re-run your scanner to confirm the numbers, not just the look.

If RPCS3 asks "Update patches?" when you open the Patch Manager, it's fine to say yes. That only downloads the official `patch.yml`. Your `imported_patch.yml` isn't touched.
