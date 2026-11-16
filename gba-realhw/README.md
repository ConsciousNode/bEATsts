# bEATsts GBA on real hardware: PSP Go

- Round-2 ROM `f90141f0…` on Kham's PSP Go (2026-11-15). It boots, plays, and Baker Vera talks.
- **Title screen:** the "unscaled" photo looks garbled at the top and bottom. **Kham checked in person: it's only the camera.** The screen draws cleanly. That matches mGBA, where the title is pixel-stable from frame 3.
- **Found on hardware:** long dialogue overflowed the box and closed before it could all be read. That was a bug in the HTML reference, ported faithfully; it's fixed in the HTML (`c29912f`) and queued for the GBA in round 3.
