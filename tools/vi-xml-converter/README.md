# VI ⇄ XML Converter

Convert a LabVIEW `.vi` to editable XML and rebuild it byte-for-byte, via a GUI or CLI.
Built on **pylabview** (`readRSRC.py`).

## Setup
> **First run fetches the engine automatically** (if `git` is on your PATH): the
> GUI and CLI clone pylabview into this folder when `pylabview/` is missing. The
> manual `git clone` below is the fallback if auto-fetch can't run.

```
pip install -r requirements.txt             # deps (numpy, lxml)
git clone https://github.com/mefistotelis/pylabview   # the engine (run inside this folder)
```
Layout expected by the scripts: `pylabview/pylabview/readRSRC.py` beside `viconvert.py`.
(On Debian/Ubuntu also `sudo apt install python3-tk` for the GUI.)


## Easiest: single-file mode (recommended)
Avoids the loose-companion-files problem entirely.
GUI: **VI → .zip**, then later **Rebuild VI from .zip**.
CLI:
```
python3 viconvert.py vi2zip  "My VI.vi"          # -> My VI.vixml.zip  (self-contained)
python3 viconvert.py zip2vi  "My VI.vixml.zip"   # -> rebuilt .vi
```
Edit files inside the .zip (or extract, edit, re-zip) and rebuild.

## GUI
```
python3 viconvert_gui.py
```
Pick a `.vi` → **Convert to XML**, or pick the master `.xml` → **Rebuild VI**.

## CLI
```
python3 viconvert.py vi2xml  "My VI.vi"
python3 viconvert.py xml2vi  "My VI.xml"  "My VI (edited).vi"
```

## Notes
- Round-trip is **lossless** for every block pylabview parses; an unparsed block
  (some `VITS` sections) is kept raw and copied back unchanged.
- pylabview recomputes all RSRC offsets + both headers on rebuild, so output stays
  internally consistent.
- pylabview is third-party (GPL) — not vendored here; clone it as above.
