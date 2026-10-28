# MLB The Show 16 crowd fix for RPCS3

On RPCS3, *MLB The Show 16* has broken crowds:
- whole sections of seats are empty
- a clump of fans stands on the pitcher's mound
- huge stretched fans show up as black bars across the screen
- rows of fans float in the sky

This repo has a one-line RPCS3 game patch that fixes this, and a full write-up of how the bug was found. It also has an [optional face patch](#optional-face-patch-for-resolution-scaling) for resolution scaling and [RPCS3 settings](#rpcs3-settings-for-mlb-16) for MLB 16.

| Before | After (patch v1.1) |
|---|---|
| ![fans on the mound](screenshots/before_replay_fans_on_mound.png) | ![full crowd, empty mound](screenshots/after_replay_mound.png) |
| ![black bars and smeared crowd](screenshots/before_better_moundclump.png) | ![clean stands](screenshots/after_behind_third.png) |
| ![a fan sitting on top of the crown scoreboard, empty outfield seats](screenshots/before_crown.png) | ![outfield crowd](screenshots/after_outfield_crown.png) |

**The short version:**
- The game is fine. The bug is in how RPCS3 replays the crowd's draw calls: two separate bugs in `rsx::draw_clause`, both explained in the [write-up](writeup/crowd-fix.md).
- Each fan reads its seat and its picture from the wrong slice of memory, so it lands at the origin (the mound), behind the camera (the black bars), or in the sky.
- The patch makes the game draw each crowd section the simplest way it knows. That way never triggers either RPCS3 bug.

## What you need

- **RPCS3**: [rpcs3.net](https://rpcs3.net/download).
- **PS3 system firmware**: download `PS3UPDAT.PUP` straight from Sony's [PS3 system software page](https://www.playstation.com/en-us/support/hardware/ps3/system-software/), then install it with **File → Install Firmware**.
- **Your own copy of the game**, legally obtained:
  - **Disc (BCUS01089):** any of these works.
    - A **decrypted ISO** (recommended): add it with **File → Add ISO Games**.
    - A raw 1:1 disc image with your disc's key next to it (same name, ending in `.dkey`): RPCS3 decrypts it as it reads (builds from April 2026 on). Also File → Add ISO Games.
    - A folder dump made on your own PS3 (e.g. with multiMAN or ManaGunZ): add it with File → Add Games.
  - **Digital (NPUA81353):** you need your own license files from your PSN account.
- **The v01.10 game update**: download it straight from Sony's update servers, then install it with **File → Install Packages/Raps/Edats**:
  - Disc version (BCUS01089): [UP9000-BCUS01089_00-MLB16THESHOWBDPA-A0110-V0100-PE.pkg](http://b0.ww.np.dl.playstation.net/tppkg/np/BCUS01089/BCUS01089_T10/07a5f28c76691db4/UP9000-BCUS01089_00-MLB16THESHOWBDPA-A0110-V0100-PE.pkg)
  - Digital version (NPUA81353): [UP9000-NPUA81353_00-MLB16THESHOWHDDM-A0110-V0100-PE.pkg](http://b0.ww.np.dl.playstation.net/tppkg/np/NPUA81353/NPUA81353_T10/e1af3ed6c162654b/UP9000-NPUA81353_00-MLB16THESHOWHDDM-A0110-V0100-PE.pkg)

## Install the patch

Works with: **MLB The Show 16, BCUS01089, game update v01.10** (PPU hash `PPU-395faa2b9c12c400d03343cad62ce7aad8ec985b`).

1. Download [`patches/MLB16_crowd_fix.yml`](patches/MLB16_crowd_fix.yml).
2. Add it to RPCS3 in one of two ways:
   - **Drag and drop:** open **Manage → Game Patches** and drop the file onto the window. RPCS3 merges it into `patches/imported_patch.yml`.
   - **By hand:** copy everything below the `Version: 1.2` line into your own `imported_patch.yml`. It lives in RPCS3's config folder, under `patches/`.
3. In **Manage → Game Patches**, expand *MLB The Show 16* and tick **"Crowd fix (single-draw crowd batches)"**. Then save.
4. Start the game.

If the patch doesn't appear under the game, you're on a different version or region. The fix idea still applies, but the address will differ. [docs/workflow.md](docs/workflow.md) shows how to find it.

The patch has only been verified on the disc version (BCUS01089). The digital version's update may have a different PPU hash. If you boot NPUA81353 and the log shows a different hash, open an issue with the hash and it can be added. Nothing in this repo contains game files.

## Optional: face patch for resolution scaling

![pin-holes in a pitcher's face and cap without the patch](screenshots/before_face_holes.jpg)

Only needed with **Resolution Scale above 100%**. At higher resolutions, player faces, ears and caps show pin-holes: the game skips triangles too small to cover a pixel at 720p, and when scaled up those triangles do cover pixels. [`patches/MLB16_triangle_fix.yml`](patches/MLB16_triangle_fix.yml) stops the skipping. Install it the same way as above and tick **"Fix holes in player faces"**. The write-up is [docs/ice-mesh.md](https://github.com/MatRanc/mlb16-revival-server/blob/main/docs/ice-mesh.md) in the revival server repo.

The master copy of this patch lives in the [revival server repo](https://github.com/MatRanc/mlb16-revival-server/blob/main/patches/MLB16_triangle_fix.yml), whose launcher installs it. The copy here keeps the RPCS3-specific fixes in one place; if the two ever differ, use the server repo's.

## RPCS3 settings for MLB 16

Found while testing online play (Oct 2026, RPCS3 v0.0.43-20394/20397, Windows, Linux and an M1 Mac):

| Setting | What we saw |
|---|---|
| **Write Color Buffers** on | Fixes the dark crowd sections and the black background in picture-in-picture windows (like the runner's lead-off). This is the one that matters. It also matters for coaches' and created players' faces: the game builds those once and saves them to `dev_hdd0/game/BCUS01089_R/USRDIR/HeadFaceCacheFile`. Faces built while it was off are saved blank and show up white. If you see white faces after turning it on, delete (or rename) that file and the game rebuilds them. |
| Read Color Buffers, Read Depth Buffer, Write Depth Buffer, Disable Vertex Cache | Keep off (the defaults). They fixed nothing visible and made RPCS3's RSX thread the bottleneck. Turning them off took dugout close-ups from 7–11 FPS to 30–40 (Ryzen 5 2600X, 1080p at 300%). |
| Strict Rendering Mode | Not needed for the above. Costs performance (an M1 Mac ran about 35 FPS in a match with it on), blocks Resolution Scale and makes RPCS3 ignore the anisotropic filter. Keep it off. |
| Resolution Scale above 100% | Sharper picture (needs Strict Rendering off). Side effects: thin see-through seams between some surfaces, like the outfield wall and the field (fewer at 150%), and pin-holes in player faces, which the [face patch](#optional-face-patch-for-resolution-scaling) fixes. 800% froze the game on an RTX 3060 Ti, likely out of video memory. |
| Default Resolution | *720p*, or *1080p* with Resolution Scale *150%* for a sharper picture. *1440×1080* is not 1440p: it's a stretched PS3 output mode, and the game still renders at 720p. |
| CPU, SPU and RSX accuracy settings | Keep RPCS3's defaults. Every freeze traced so far came from one changed away from its default. SPU Block Size *Mega* with Accurate SPU Reservations off froze two online matches (one silent hang, one fatal error inside `cellSpursRemoveWorkload`). RSX FIFO Accuracy *Fast* logged "FIFO error: possible desync event" every few seconds, then froze or crashed. Online, one player freezing stops both games, since they run in lockstep. |

The [revival server's launcher](https://github.com/MatRanc/mlb16-revival-server) applies these for the game automatically.

## What's in here

| | |
|---|---|
| [patches/](patches/) | The crowd patch and the face patch. |
| [writeup/crowd-fix.md](writeup/crowd-fix.md) | The full story: symptoms, how the bad draws were found in RenderDoc, how the game code was found in Ghidra, both RPCS3 bugs, the patch and how it was verified. Dead ends included. |
| [docs/setup.md](docs/setup.md) | Setting up the tools: RPCS3 + RenderDoc capture, Ghidra 12.1.2 + PS3 scripts, GhidraMCP, RenderDoc MCP. |
| [docs/workflow.md](docs/workflow.md) | The general method for chasing *any* RPCS3 graphics bug in these games, from glitch to patch. |
| [docs/rpcs3-internals.md](docs/rpcs3-internals.md) | Cheat sheet: the RSX/GCM commands that matter, how RPCS3 lays out vertex data in a RenderDoc capture, and how `draw_clause` works. |
| [docs/patching.md](docs/patching.md) | Writing RPCS3 patches: finding the PPU hash, encoding branches, testing. |
| [AGENTS.md](AGENTS.md) | Instructions for an AI coding agent (Claude Code, etc.) driving Ghidra and RenderDoc through MCP to hunt the next bug. |
| [tools/](tools/) | The Python scripts used here: RenderDoc replay helpers, EBOOT search and disassembly, a model of RPCS3's draw clause. |

## Status

- Crowd: **fixed** with patch v1.1, first tested at Kauffman Stadium (gameplay, batting view, replays), since then at other parks and in online matches.
- Still open: a handful of small crowd batches that may still misbehave in rare shots, and a crowd flicker seen once that a new game (new crowd layout) cleared (see the write-up), the post-game freeze, black flashes on some camera pans, one mid-game RPCS3 crash (`rsx::surface_color_format` verification failed, seen once in an online game), and players in the dugout flickering once on a quick camera pan (no capture yet).
- Upstream: a proposed fix for both RPCS3 bugs is on [my RPCS3 fork](https://github.com/MatRanc/rpcs3/commits/fix-mlb-crowd-draw-clause) (not built or tested, not a PR). A fix inside RPCS3 would cover every MLB title that draws crowds this way, without per-game patches.

## Related

- The revival server's [better depth of field](https://github.com/MatRanc/mlb16-revival-server/blob/main/TECHNICAL.md#the-patches) patch rewrites the game's close-up blur shader.

## Fun fact

The whole investigation was done with Claude Code driving Ghidra and RenderDoc through MCP servers. From "the crowd is broken" to a working patch, it cost about **$30 in API usage**.

## License

GNU General Public License v2.0 for the scripts and docs (see [LICENSE](LICENSE)). MLB The Show is © Sony Interactive Entertainment. This repo contains no game code or assets beyond short, explanatory excerpts.
