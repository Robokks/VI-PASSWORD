#!/usr/bin/env python3
"""viconvert.py - LabVIEW .vi <-> .xml converter (wraps pylabview readRSRC).

Usage:
  python3 viconvert.py vi2xml  input.vi                 # .vi  -> .xml (+ block files)
  python3 viconvert.py xml2vi  input.xml [output.vi]    # .xml -> .vi

The XML round-trip is lossless for every block pylabview can parse; a block it
cannot (e.g. some VITS sections) is kept as raw .bin and copied back untouched.
Requires Python 3.8+, numpy and lxml.
"""
import sys, os, subprocess

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

def run(args):
    env = dict(os.environ)
    env["PYTHONPATH"] = PYL + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.call([sys.executable, RR] + args, env=env)

def main(argv):
    if len(argv) < 3:
        print(__doc__); return 2
    if not ensure_engine():
        return 3
    cmd, src = argv[1], argv[2]
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
