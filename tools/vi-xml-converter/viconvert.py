#!/usr/bin/env python3
"""viconvert.py - LabVIEW .vi <-> .xml converter (wraps pylabview readRSRC).

Usage:
  python3 viconvert.py vi2zip  input.vi  [out.vixml.zip]  # .vi  -> ONE self-contained zip  (recommended)
  python3 viconvert.py zip2vi  in.zip    [output.vi]      # that zip -> rebuilt .vi
  python3 viconvert.py vi2xml  input.vi                   # .vi  -> loose .xml + block files
  python3 viconvert.py xml2vi  input.xml [output.vi]      # loose .xml (needs its sidecars) -> .vi

The XML round-trip is lossless for every block pylabview can parse; a block it
cannot (e.g. some VITS sections) is kept as raw .bin and copied back untouched.
Requires Python 3.8+, numpy and lxml.
"""
import sys, os, subprocess, tempfile, zipfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PYL  = os.path.join(HERE, "pylabview")                 # repo root (holds the pylabview package)
RR   = os.path.join(PYL, "pylabview", "readRSRC.py")
PYLABVIEW_URL = "https://github.com/mefistotelis/pylabview"

def ensure_engine():
    """Clone pylabview next to this script if it isn't there yet."""
    if os.path.exists(RR):
        return True
    print("pylabview not found - cloning it from", PYLABVIEW_URL, "...")
    rc = subprocess.call(["git", "clone", "--depth", "1", PYLABVIEW_URL, PYL])
    if rc == 0 and os.path.exists(RR):
        print("pylabview ready."); return True
    print("Could not fetch pylabview automatically. Clone it manually:\n"
          "  cd %s\n  git clone %s" % (HERE, PYLABVIEW_URL))
    return False

def missing_sidecars(xml_path):
    """Return companion files referenced by the master XML that aren't next to it.
    vi2xml emits the .xml plus block files (*_BDHb.xml, *_LVSR_Field90.bin, ...);
    all must sit in the same folder to rebuild."""
    import re
    d = os.path.dirname(os.path.abspath(xml_path))
    try:
        text = open(xml_path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return []
    refs = re.findall(r'File="([^"]+)"', text)
    return [r for r in refs if not os.path.exists(os.path.join(d, r))]

def run(args, cwd=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = PYL + os.pathsep + env.get("PYTHONPATH", "")
    # capture output so callers (incl. the GUI) can SEE pylabview's messages
    res = subprocess.run([sys.executable, RR] + args, env=env, cwd=cwd,
                         capture_output=True, text=True, errors="replace")
    out = (res.stdout or "") + (res.stderr or "")
    if out.strip():
        print(out.rstrip())
    return res.returncode

def _find_master_xml(folder):
    """The master .xml is the one whose stem prefixes the block sidecar files."""
    names = os.listdir(folder)
    xmls = [f for f in names if f.lower().endswith(".xml")]
    for x in xmls:
        stem = x[:-4]
        if any(fn != x and fn.startswith(stem + "_") for fn in names):
            return os.path.join(folder, x)
    return os.path.join(folder, xmls[0]) if xmls else None

def vi2zip(vi, outzip):
    """.vi -> one self-contained .zip holding the master XML + all sidecars."""
    if not os.path.isfile(vi):
        print("ERROR: no such file:", vi); return 2
    tmp = tempfile.mkdtemp(prefix="vi2xml_")
    try:
        rc = run(["-x", "-i", os.path.abspath(vi)], cwd=tmp)
        produced = sorted(os.listdir(tmp))
        # pylabview can exit non-zero on a mere block warning (e.g. VITS) while
        # still writing a complete, valid XML set - so proceed if the master XML exists.
        if not _find_master_xml(tmp):
            print("ERROR: extraction produced no XML (pylabview exit %s)." % rc)
            print("       See the message above for the cause.")
            return rc or 1
        if rc != 0:
            print("note: pylabview reported a warning (exit %s) but the XML set is complete; continuing." % rc)
        with zipfile.ZipFile(outzip, "w", zipfile.ZIP_DEFLATED) as z:
            for fn in produced:
                z.write(os.path.join(tmp, fn), fn)
        print("wrote", outzip, "(%d files)" % len(produced))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def zip2vi(inzip, outvi):
    """A .zip made by vi2zip -> rebuilt .vi (all sidecars travel together)."""
    tmp = tempfile.mkdtemp(prefix="zip2vi_")
    try:
        with zipfile.ZipFile(inzip) as z:
            z.extractall(tmp)
        base = tmp
        entries = os.listdir(tmp)
        if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])):
            base = os.path.join(tmp, entries[0])   # zip had a single top folder
        master = _find_master_xml(base)
        if not master:
            print("ERROR: no master .xml found inside the zip"); return 4
        rc = run(["-c", "-m", master, "-i", os.path.abspath(outvi)], cwd=base)
        if os.path.isfile(outvi) and os.path.getsize(outvi) > 0:
            if rc != 0:
                print("note: pylabview warning (exit %s) but the .vi was written." % rc)
            print("wrote", outvi)
            return 0
        print("ERROR: rebuild produced no .vi (pylabview exit %s). See message above." % rc)
        return rc or 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def main(argv):
    if len(argv) < 3:
        print(__doc__); return 2
    if not ensure_engine():
        return 3
    cmd, src = argv[1], argv[2]
    if cmd == "vi2zip":
        out = argv[3] if len(argv) > 3 else os.path.splitext(src)[0] + ".vixml.zip"
        return vi2zip(src, out)
    if cmd == "zip2vi":
        out = argv[3] if len(argv) > 3 else os.path.splitext(src)[0].replace(".vixml", "") + "_out.vi"
        return zip2vi(src, out)
    if cmd == "vi2xml":
        return run(["-x", "-i", src])
    if cmd == "xml2vi":
        miss = missing_sidecars(src)
        if miss:
            print("ERROR: the master XML needs its companion files in the SAME folder,\n"
                  "       but these are missing next to %s:" % os.path.basename(src))
            for m in miss[:12]: print("         -", m)
            print("       Rebuild only from a folder that holds the full set that\n"
                  "       'vi2xml' produced (the .xml plus all *_*.xml / *.bin files).")
            return 4
        out = argv[3] if len(argv) > 3 else os.path.splitext(src)[0] + "_out.vi"
        rc = run(["-c", "-m", src, "-i", out])
        if rc == 0: print("wrote", out)
        return rc
    print("unknown command:", cmd, "\n", __doc__); return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv))
