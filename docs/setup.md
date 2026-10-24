# Tool setup

This assumes you already have **RPCS3**, a legal dump of the game, and its update (v01.10 for MLB 16) installed. It was done on Fedora 44 (GNOME Wayland). The notes on other platforms are untested.

What you'll set up:

| tool | why |
|---|---|
| RenderDoc | Capture one frame of RPCS3's Vulkan output and inspect every draw call. |
| Ghidra 12.1.2 + Ps3GhidraScripts | Decompile the game's PowerPC code. |
| GhidraMCP | Lets an AI agent query Ghidra (decompile, xrefs, rename). |
| RenderDoc MCP | Lets an AI agent query a `.rdc` capture headless. |
| Python 3 + capstone | The scripts in [`../tools`](../tools). |

You can do everything without the AI parts. The MCP servers just let an agent do the tedious digging (thousands of draws, hundreds of functions) while you steer.

---

## Decrypting the EBOOT

In RPCS3: **Utilities → Decrypt PS3 Binaries**, then pick the *update's* `EBOOT.BIN`: `dev_hdd0/game/BCUS01089/USRDIR/EBOOT.BIN`. That's the code that actually runs. RPCS3 writes `EBOOT.elf` next to it.

To check that you have the right one: the RPCS3 log prints `PPU executable hash: PPU-…` at boot. Patches are keyed to that hash.

## Capturing RPCS3 with RenderDoc

1. Install RenderDoc (`dnf install renderdoc`, or from renderdoc.org).
2. **Extract the RPCS3 AppImage.** RenderDoc can't inject into the AppImage wrapper:
   ```sh
   mkdir -p ~/opt/rpcs3-extracted && cd ~/opt/rpcs3-extracted
   /path/to/rpcs3.AppImage --appimage-extract
   # binary: ~/opt/rpcs3-extracted/squashfs-root/usr/bin/rpcs3
   ```
3. In RPCS3, set the renderer to **Vulkan**.
4. In RenderDoc: **File → Launch Application**:
   - Executable: the extracted `usr/bin/rpcs3`
   - Environment: `QT_QPA_PLATFORM=xcb`. Fedora's RenderDoc has no Wayland hooks, and without this RPCS3 crashes with *"Segfault executing location 0000000000000000"*. Windows doesn't need it.
   - Launch, boot the game and get to the glitch.
5. Capture with RenderDoc's **Capture Frame(s) Immediately** button (F12 may not reach the game window). Use **1 frame**. These frames are 1–1.7 GB and ~10,000 draws each, and a 10-frame capture ran a 32 GB machine out of memory.
6. Save the capture right away (**File → Save**). Unsaved captures live in `/tmp` and disappear on reboot.

Tips:
- Take captures of *specific* symptoms and name them for it, e.g. `replay_fans_on_mound.rdc`, `replay_no_fans.rdc`.
- Pausing the game (or a replay) and then capturing gets you a stable frame.
- After a fix, take the same shots again to verify.

## RenderDoc Python module (for the tools and RenderDoc MCP)

The headless scripts need RenderDoc's Python module (`renderdoc.so`, or `renderdoc.pyd` on Windows). Windows builds ship it. Fedora's package doesn't, so build it from source, using the same version as your RenderDoc (v1.45 here):

```sh
sudo dnf install cmake gcc-c++ python3-devel libX11-devel libxcb-devel xcb-util-keysyms-devel \
                 mesa-libGL-devel wayland-devel autoconf automake bison pcre2-devel libtool
git clone --depth 1 --branch v1.45 https://github.com/baldurk/renderdoc ~/opt/renderdoc-src
cd ~/opt/renderdoc-src
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DENABLE_QRENDERDOC=OFF -DENABLE_PYRENDERDOC=ON \
      -DENABLE_GL=ON -DENABLE_GLES=ON -DENABLE_VULKAN=ON
cmake --build build -j$(nproc)
# result: build/lib/renderdoc.so
```

If the bundled PCRE step fails asking for `aclocal-1.16`, the autotools timestamps are off. In `build/qrenderdoc/local_pcre-prefix/src/local_pcre`, touch `aclocal.m4`, then `configure Makefile.in config.h.in`, then `config.status`, then `Makefile config.h`, in that order, and rebuild.

Then point the scripts at it: `export RENDERDOC_MODULE_PATH=~/opt/renderdoc-src/build/lib`. Run them with a Python whose version matches the one the module was built against.

## RenderDoc MCP

[Linkingooo/renderdoc-mcp](https://github.com/Linkingooo/renderdoc-mcp) is a headless MCP server that opens `.rdc` files directly. You don't need the RenderDoc GUI open.

```sh
git clone https://github.com/Linkingooo/renderdoc-mcp ~/renderdoc-mcp
cd ~/renderdoc-mcp && python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/pip install 'mcp[cli]<2'      # it uses the FastMCP API from mcp 1.x
claude mcp add renderdoc -s user -e RENDERDOC_MODULE_PATH=$HOME/opt/renderdoc-src/build/lib \
      -- $HOME/renderdoc-mcp/.venv/bin/renderdoc-mcp
```

Useful tools: `open_capture`, `get_frame_overview`, `pixel_history`, `get_draw_call_state`, `disassemble_shader`, `get_post_vs_data`, `save_render_target`.

Two gotchas:
- Don't open the same capture in the MCP server and in a script at the same time. Two replays of a 1.5 GB capture ran the GPU out of memory. Call `close_capture` first.
- The generic tools don't understand RPCS3's vertex pulling (see [rpcs3-internals.md](rpcs3-internals.md)). For vertex data, use [`tools/rpcs3_drawparams.py`](../tools/rpcs3_drawparams.py).

## Ghidra

**Use Ghidra 12.1.2.** That's the newest version the community build of the PS3 scripts used here works with. Newer Ghidra breaks the extension, and the GhidraMCP build has to match the Ghidra version too.

1. Install Ghidra 12.1.2 (needs a JDK 21+; JDK 25 works) to e.g. `~/opt/ghidra_12.1.2_PUBLIC`.
2. **Ps3GhidraScripts** ([clienthax/Ps3GhidraScripts](https://github.com/clienthax/Ps3GhidraScripts)). Use a build for 12.1.2. Building it yourself from the repo needs Ghidra's own Gradle wrapper, because the repo's wrapper is too old for modern JDKs:
   ```sh
   cd Ps3GhidraScripts
   GHIDRA_INSTALL_DIR=~/opt/ghidra_12.1.2_PUBLIC sh ~/opt/ghidra_12.1.2_PUBLIC/support/gradle/gradlew buildExtension
   ```
   Install the zip via **File → Install Extensions**, or unzip it into `~/.config/ghidra/ghidra_12.1.2_PUBLIC/Extensions`.
3. **TOC register fix.** PS3 code keeps the table-of-contents pointer in `r2`. Make the decompiler treat `r2` as preserved across calls: in `Ghidra/Processors/PowerPC/data/languages/ppc_64_32.cspec`, add `<register name="r2"/>` inside `<unaffected>`. Back the file up first.
4. **Import the EBOOT:**
   - New project → Import `EBOOT.elf`.
   - Untick **"Show only recommended languages"** and pick **`PowerISA-Altivec-64-32addr`** (big-endian). The default `A2ALT` language uses 64-bit pointers and gives garbage.
   - Open it in CodeBrowser and answer **No** to "Analyze now?".
   - Run the PS3 scripts from the Script Manager as their README says (e.g. the ELF/syscall/NID scripts).
   - Then run **Analysis → Auto Analyze**. The first analysis takes a while.

## GhidraMCP

[LaurieWired/GhidraMCP](https://github.com/LaurieWired/GhidraMCP) has two halves: a Ghidra plugin (an HTTP server on port 8080) and a Python MCP bridge. Release zips target one Ghidra version, so build the plugin against 12.1.2:

```sh
git clone --depth 1 --branch 2.0 https://github.com/LaurieWired/GhidraMCP ~/opt/ghidra-ext/mcpsrc
cd ~/opt/ghidra-ext/mcpsrc/extension
export GHIDRA_INSTALL_DIR=~/opt/ghidra_12.1.2_PUBLIC
sh $GHIDRA_INSTALL_DIR/support/gradle/gradlew buildExtension
# install dist/ghidra_12.1.2_PUBLIC_*_GhidraMCP.zip like the PS3 extension
claude mcp add ghidra -s user -- uvx --from ~/opt/ghidra-ext/mcpsrc ghidra-mcp --ghidra-server http://127.0.0.1:8080/
```

In Ghidra, enable the plugin in **CodeBrowser → File → Configure → Developer → GhidraMCPPlugin**. It only runs while the program is open in CodeBrowser; enabling it in the project window does nothing. Check it's up: `curl http://127.0.0.1:8080/methods`.

Save the Ghidra project (Ctrl+S) after the agent renames things, or the names are lost.

## Python tools

```sh
python3 -m venv ~/venvs/ps3re && ~/venvs/ps3re/bin/pip install capstone
```

The RenderDoc scripts run with whatever Python matches your `renderdoc.so`. The RenderDoc MCP venv works.

Don't name a script `dis.py`. It shadows the standard library module that capstone imports.
