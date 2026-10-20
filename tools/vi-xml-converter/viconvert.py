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
        out = argv[3] if len(argv) > 3 else os.path.splitext(src)[0] + "_out.vi"
        rc = run(["-c", "-m", src, "-i", out])
        if rc == 0: print("wrote", out)
        return rc
    print("unknown command:", cmd, "\n", __doc__); return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv))
