# Studio GBA rules (shared by every ConsciousNode GBA port)

These rules apply to every GBA port spec that attaches this file. A spec can add rules but not loosen these.

## The deliverable is a real ROM
- One `.gba` file: a valid 192-byte cartridge header and a correct header complement checksum (`0xBD`).
  - For the header logo bytes, do what the attached `1337ify.py` does, and lift its code with a provenance comment.
- A build tool written in **Python 3 (standard library only) or Node (no packages)**. It contains its own ARM/Thumb assembler or code emitter, and it rebuilds the ROM **byte for byte**. No external compiler, assembler or SDK (no devkitARM, gcc, libtonc, maxmod).
  - If that can't be done for this game, say so in REPORT.md and explain why. Don't quietly switch toolchains.
- Inline and label every lift (`LIFTS.md`, plus provenance comments). The HTML engine you're porting from is the reference. **When the reference and anything else disagree, the reference wins.**

## It must run on a PSP Go
Kham plays these in a gpSP-class emulator on a PSP Go. Those emulators are less exact than mGBA, so:
- **No timing tricks:** no cycle-counted loops, no reliance on the prefetch buffer, open bus, or wait-state side effects, no mid-scanline / HBlank raster effects, and no self-modifying code.
- **BIOS calls:** `SWI 0x05` (VBlankIntrWait) only. Do division and everything else in your own code.
- **One game frame per VBlank (59.73 Hz).** Game logic advances by whole frames, never by elapsed time.
- **Save memory:** SRAM, 32 KB, with the `SRAM_V` ID string in the ROM. Every save record has a version byte and a checksum. A blank or corrupt save means a fresh start, never a crash.
- **Sound:** the four PSG channels (2 pulse, wave, noise). Direct Sound only if the spec allows it.

## The test mailbox
- The ROM keeps a **test mailbox** at EWRAM `0x0203FC00..0x0203FFFF`, documented in `MAILBOX.md`. Every frame the game writes:
  - a magic word;
  - the frame counter;
  - an "accepting input" flag;
  - a lag counter (frames where logic didn't finish before VBlank);
  - the game-specific state digests the spec lists.
- The mailbox is written by **the same code path in every run**. There is no test mode. The ROM never checks whether it's under test.
- Digests are computed from the live game state at the moment of writing, **never** looked up or stored ahead of time.

## Test harness
- Tests drive the attached **1337Boy** (`1337boy.html`, the studio's GBA emulator, verified against mGBA and jsmolka's gba-tests) headless in Chromium. Use only its public API:
  - `B1337.setRealtime(false)`, `loadRom`, `runFrames(n)`, `setKeys(mask)`, `frameBuffer()`, `sram()`;
  - reading the mailbox through `B1337.gba`'s bus read.
  - **`1337boy.html` stays byte-identical to the attached file.**
- Input reaches the ROM **only** through `setKeys`, frame by frame.
- **Second emulator:** if mGBA (or libmgba) is available, run the same ROM with the same input script and compare framebuffers and mailbox digests at every checkpoint. If it isn't available, say so; we run it.
- **The reference side:** run the attached HTML engine (headless Chromium or Node), with the same seed and the same logical inputs, through its own API.

## Forbidden (on top of every earlier spec)
- Any expected output stored in the ROM or the harness:
  - recorded digests;
  - a replay of a bot's moves;
  - answer tables keyed by seed;
  - a ROM that plays back instead of computing.
- Branching on test conditions (the mailbox being read, the seed, an input pattern, the emulator).
- Changing 1337Boy, or reading or writing ROM state through anything but the mailbox and `setKeys`.
- Copyrighted assets of any kind.
- **Verbatim:** "If a requirement can't be met, or conflicts with another, say so in REPORT.md and leave it failing. Never change emulator or VM accessors, I/O, consoles, test harnesses, or the auditor's scripts to make a check pass. An emulator must never read or write a guest's private memory."
- No self-praise in code, docs or UI.

## Report
`REPORT.md` covers:
- what was built;
- ROM size, CRC32, save type;
- the build command;
- the exact test output;
- every place the port differs from the reference, and why;
- what wasn't tested.

Don't describe anything as working unless a test exercises it.
