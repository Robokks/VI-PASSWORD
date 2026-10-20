# VI Unit Tester

Pick a `.vi`, set front-panel **inputs**, give **expected outputs**, click Run →
**PASS/FAIL**. The VI is executed in your installed LabVIEW via **ActiveX** (VI
Server): `GetVIReference` → `SetControlValue` → `Run` → `GetControlValue` → compare.

## Requirements (Windows)
- **LabVIEW installed** (its ActiveX server is on by default). There is no way to
  run a VI without LabVIEW — Python/pylabview only *read* the file format.
- `pip install -r requirements.txt`  (pywin32)

## Run
```
python vi_unit_tester.py
```
1. **Choose .vi** (optionally **Detect terminals** to list the control/indicator names).
2. Add **Inputs**: each front-panel control name → value.
3. Add **Expected outputs**: each indicator name → expected value (+ optional tolerance).
4. **Run Test** → per-indicator PASS/FAIL and an overall verdict.

### Value syntax
`42` / `3.14` (number) · `true` / `false` (boolean) · any other text (string) ·
`[0, 1, 1, 2, 3]` (array/cluster, JSON).
Names are the exact front-panel labels, **case-sensitive**.

## Notes & alternatives
- Standard pattern — many projects drive LabVIEW from Python exactly this way
  (`win32com` + `GetVIReference`/`SetControlValue`/`Run`).
- **[autolv](https://github.com/l-johnston/autolv)** (`pip install autolv`) is a
  maintained Pythonic wrapper over the same ActiveX API — a cleaner backend if you
  want to script many tests.
- If you'd rather write tests **inside LabVIEW**, mature native frameworks exist:
  **[Caraya](https://github.com/vipm-io/caraya)**, **[astemes-lunit](https://github.com/astemes/astemes-lunit)**,
  **[TestLite](https://github.com/Tom-Lu/TestLite)**, and NI's built-in **Unit Test Framework**.
- "Detect terminals" reuses the pylabview clone from `../vi-xml-converter/` if present;
  otherwise just type the names.
