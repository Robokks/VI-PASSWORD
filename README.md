# VI-PASSWORD

Tools for inspecting and manipulating National Instruments **LabVIEW `.vi`** files
(the RSRC container format), developed while reverse-engineering the format.

## What's here

| Path | What it does |
|------|--------------|
| `tools/vi-xml-converter/` | Convert `.vi` ⇄ `.xml` (GUI + CLI) — edit a VI as XML and rebuild it byte-for-byte. Wraps pylabview. |
| `tools/vi-decoder/vi_decoder.html` | Browser tool — drop a `.vi` to decode its RSRC blocks, version, password status, terminals and named primitive nodes, client-side. |
| `tools/vi-decoder/vi_flow.html` | Interactive dataflow diagram of a decoded "Add & Build Array" VI. |
| `tools/parse_vi.py` | Minimal, dependency-free RSRC parser — reads the block table, version, and the `BDPW` password hashes. |
| `docs/Fibonacci_VI_Scripting.md` | Complete VI Scripting program (and manual steps) to generate a Fibonacci VI. |

## Format notes

A `.vi` is an **RSRC** container: an `RSRC\r\n…LVIN LBVW` header at both the start and
before the resource info, a data section, and a directory of 4-char blocks
(`LVSR`, `vers`, `BDPW`, `BDHb`, `FPHb`, `VCTP`, …) referenced by absolute offsets.

- **Password**: the `BDPW` block stores `md5(password)` plus two salted hashes;
  `md5("")` = `d41d8cd98f00b204e9800998ecf8427e` means no password.
- **Primitives**: block-diagram nodes carry a `primResID` (e.g. `1050` = Add,
  `1052` = Multiply), resolvable via LabVIEW-sourced corpora.

The browser tools are standalone HTML — open them directly or view as artifacts.
