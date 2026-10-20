#!/usr/bin/env python3
"""VI <-> XML Converter - desktop GUI (Tkinter, stdlib only).

Wraps pylabview's readRSRC.py to convert LabVIEW .vi <-> .xml.
Run:  python3 viconvert_gui.py
Requires: Python 3.8+ with Tkinter, plus  pip install numpy lxml
"""
import os, sys, threading, subprocess, queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

HERE = os.path.dirname(os.path.abspath(__file__))
PYL  = os.path.join(HERE, "pylabview")
RR   = os.path.join(PYL, "pylabview", "readRSRC.py")
PYLABVIEW_URL = "https://github.com/mefistotelis/pylabview"

def readrsrc(args, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = PYL + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, RR] + args, cwd=cwd, env=env,
                          capture_output=True, text=True)

class App:
    def __init__(self, root):
        self.root = root
        root.title("VI ⇄ XML Converter")
        root.geometry("680x460")
        root.minsize(560, 380)
        self.q = queue.Queue()

        pad = dict(padx=10, pady=6)
        head = ttk.Label(root, text="LabVIEW  VI ⇄ XML", font=("TkDefaultFont", 14, "bold"))
        head.pack(anchor="w", **pad)
        ttk.Label(root, text="Powered by pylabview · round-trip is lossless for parsed blocks",
                  foreground="#666").pack(anchor="w", padx=10)

        # --- VI -> XML ---
        f1 = ttk.LabelFrame(root, text="VI  →  XML")
        f1.pack(fill="x", **pad)
        self.vi_path = tk.StringVar()
        r = ttk.Frame(f1); r.pack(fill="x", padx=8, pady=6)
        ttk.Entry(r, textvariable=self.vi_path).pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="Choose .vi…", command=self.pick_vi).pack(side="left", padx=6)
        ttk.Button(f1, text="Convert to XML", command=self.run_vi2xml).pack(anchor="e", padx=8, pady=(0,8))

        # --- XML -> VI ---
        f2 = ttk.LabelFrame(root, text="XML  →  VI")
        f2.pack(fill="x", **pad)
        self.xml_path = tk.StringVar()
        r2 = ttk.Frame(f2); r2.pack(fill="x", padx=8, pady=6)
        ttk.Entry(r2, textvariable=self.xml_path).pack(side="left", fill="x", expand=True)
        ttk.Button(r2, text="Choose .xml…", command=self.pick_xml).pack(side="left", padx=6)
        ttk.Button(f2, text="Rebuild VI", command=self.run_xml2vi).pack(anchor="e", padx=8, pady=(0,8))

        # --- log ---
        ttk.Label(root, text="Log").pack(anchor="w", padx=10)
        self.log = scrolledtext.ScrolledText(root, height=10, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0,10))

        self.root.after(120, self.drain)
        if not os.path.exists(RR):
            self.write("pylabview engine not found - fetching it automatically…")
            self.fetch_engine()

    def fetch_engine(self):
        """Clone pylabview next to this script (needs git on PATH)."""
        def work():
            try:
                res = subprocess.run(["git", "clone", "--depth", "1", PYLABVIEW_URL, PYL],
                                     capture_output=True, text=True)
                for line in (res.stdout + res.stderr).splitlines(): self.write("  " + line)
                if os.path.exists(RR):
                    self.write("✓ pylabview ready - you can convert now.\n")
                else:
                    self.write("✗ auto-fetch failed. Install git, or clone manually:\n"
                               "   cd %s\n   git clone %s\n" % (HERE, PYLABVIEW_URL))
            except FileNotFoundError:
                self.write("✗ git not found on PATH. Clone pylabview manually:\n"
                           "   cd %s\n   git clone %s\n" % (HERE, PYLABVIEW_URL))
        threading.Thread(target=work, daemon=True).start()

    # pickers
    def pick_vi(self):
        p = filedialog.askopenfilename(title="Choose a .vi",
              filetypes=[("LabVIEW VI", "*.vi *.ctl *.vit"), ("All files", "*.*")])
        if p: self.vi_path.set(p)
    def pick_xml(self):
        p = filedialog.askopenfilename(title="Choose the master .xml",
              filetypes=[("XML", "*.xml"), ("All files", "*.*")])
        if p: self.xml_path.set(p)

    # logging (thread-safe via queue)
    def write(self, s): self.q.put(s)
    def drain(self):
        try:
            while True:
                s = self.q.get_nowait()
                self.log.configure(state="normal")
                self.log.insert("end", s + "\n"); self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(120, self.drain)

    # actions
    def run_vi2xml(self):
        src = self.vi_path.get().strip()
        if not src: return messagebox.showwarning("Pick a file", "Choose a .vi first.")
        outdir = filedialog.askdirectory(title="Where to write the XML files?")
        if not outdir: return
        self._go(["-x", "-i", os.path.abspath(src)], outdir,
                 "VI → XML  (%s)" % os.path.basename(src))

    def _missing_sidecars(self, xml_path):
        import re
        d = os.path.dirname(os.path.abspath(xml_path))
        try:
            text = open(xml_path, "r", encoding="utf-8", errors="replace").read()
        except OSError:
            return []
        return [r for r in re.findall(r'File="([^"]+)"', text)
                if not os.path.exists(os.path.join(d, r))]

    def run_xml2vi(self):
        src = self.xml_path.get().strip()
        if not src: return messagebox.showwarning("Pick a file", "Choose the master .xml first.")
        miss = self._missing_sidecars(src)
        if miss:
            self.write("✗ Missing companion files next to this XML (they must be in the "
                       "same folder as the .xml):")
            for m in miss[:12]: self.write("     - " + m)
            self.write("   Rebuild only from a folder holding the full set 'VI → XML' "
                       "produced.\n")
            return messagebox.showerror("Missing files",
                "This .xml references %d companion file(s) that aren't in its folder.\n\n"
                "Rebuild from a folder that has the complete set that 'VI → XML' "
                "created (the .xml plus all *_*.xml / *.bin files)." % len(miss))
        out = filedialog.asksaveasfilename(title="Save rebuilt VI as…",
                defaultextension=".vi", filetypes=[("LabVIEW VI", "*.vi")],
                initialfile=os.path.splitext(os.path.basename(src))[0] + "_out.vi")
        if not out: return
        self._go(["-c", "-m", os.path.abspath(src), "-i", os.path.abspath(out)],
                 os.path.dirname(os.path.abspath(src)),
                 "XML → VI  → %s" % os.path.basename(out))

    def _go(self, args, cwd, title):
        if not os.path.exists(RR):
            self.write("pylabview engine still missing - fetching… try again when ready.")
            self.fetch_engine(); return
        self.write("▶ " + title)
        def work():
            try:
                res = readrsrc(args, cwd)
                for line in (res.stdout or "").splitlines(): self.write("  " + line)
                for line in (res.stderr or "").splitlines(): self.write("  " + line)
                self.write("✓ done (exit %d)\n" % res.returncode if res.returncode == 0
                           else "✗ exit %d\n" % res.returncode)
            except Exception as e:
                self.write("✗ error: %s\n" % e)
        threading.Thread(target=work, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
