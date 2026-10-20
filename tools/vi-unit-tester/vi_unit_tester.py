#!/usr/bin/env python3
"""VI Unit Tester - pick a .vi, set inputs, give expected outputs, get PASS/FAIL.

HOW IT WORKS
    It drives your installed LabVIEW through ActiveX automation (VI Server):
    open VI reference -> SetControlValue for each input -> Run -> GetControlValue
    for each indicator -> compare to expected.

REQUIREMENTS (Windows only)
    - LabVIEW installed (any edition that exposes the ActiveX server; default on).
    - pip install pywin32
    The VI runs in the real LabVIEW engine, so this only works where LabVIEW is
    installed. There is no way to execute a VI without LabVIEW.

VALUE SYNTAX (in the Value / Expected fields)
    number -> 42 or 3.14 ,  boolean -> true / false ,  text -> any other text,
    array / cluster -> JSON list, e.g.  [0, 1, 1, 2, 3]
"""
import os, sys, json, threading, queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# pylabview (optional) - only used by "Detect terminals" to prefill names
HERE = os.path.dirname(os.path.abspath(__file__))
PYL  = os.path.normpath(os.path.join(HERE, "..", "vi-xml-converter", "pylabview"))
RR   = os.path.join(PYL, "pylabview", "readRSRC.py")


def parse_val(s):
    s = s.strip()
    if s == "":
        return ""
    low = s.lower()
    if low == "true":  return True
    if low == "false": return False
    if s[0] in "[{":
        try: return json.loads(s)
        except Exception: pass
    try: return int(s)
    except Exception: pass
    try: return float(s)
    except Exception: pass
    return s


def approx(a, b, tol):
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(approx(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return str(a) == str(b)


class RowSet(ttk.Frame):
    """A growable set of rows. cols = list of (label, width)."""
    def __init__(self, master, cols, add_text):
        super().__init__(master)
        self.cols = cols
        hdr = ttk.Frame(self); hdr.pack(fill="x")
        for name, w in cols:
            ttk.Label(hdr, text=name, width=w, anchor="w",
                      font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=2)
        ttk.Label(hdr, text="", width=3).pack(side="left")
        self.body = ttk.Frame(self); self.body.pack(fill="x")
        ttk.Button(self, text=add_text, command=self.add_row).pack(anchor="w", pady=(4, 0))
        self.rows = []

    def add_row(self, values=None):
        r = ttk.Frame(self.body); r.pack(fill="x", pady=1)
        vars_ = []
        for i, (name, w) in enumerate(self.cols):
            v = tk.StringVar(value=(values[i] if values and i < len(values) else ""))
            ttk.Entry(r, textvariable=v, width=w).pack(side="left", padx=2)
            vars_.append(v)
        ttk.Button(r, text="✕", width=3,
                   command=lambda: self._remove(r, vars_)).pack(side="left")
        self.rows.append((r, vars_))

    def _remove(self, r, vars_):
        r.destroy()
        self.rows = [(rr, vv) for rr, vv in self.rows if vv is not vars_]

    def values(self):
        out = []
        for _, vars_ in self.rows:
            vals = [v.get().strip() for v in vars_]
            if any(vals):
                out.append(vals)
        return out


class App:
    def __init__(self, root):
        self.root = root
        root.title("VI Unit Tester")
        root.geometry("760x640"); root.minsize(620, 520)
        self.q = queue.Queue()

        pad = dict(padx=10, pady=6)
        ttk.Label(root, text="VI Unit Tester", font=("TkDefaultFont", 14, "bold")).pack(anchor="w", **pad)
        ttk.Label(root, text="Runs the VI in LabVIEW (ActiveX), compares indicators to expected values.",
                  foreground="#666").pack(anchor="w", padx=10)

        # VI picker
        f = ttk.Frame(root); f.pack(fill="x", **pad)
        self.vi_path = tk.StringVar()
        ttk.Entry(f, textvariable=self.vi_path).pack(side="left", fill="x", expand=True)
        ttk.Button(f, text="Choose .vi…", command=self.pick_vi).pack(side="left", padx=6)
        ttk.Button(f, text="Detect terminals", command=self.detect).pack(side="left")

        inf = ttk.LabelFrame(root, text="Inputs  (front-panel control name → value)")
        inf.pack(fill="x", **pad)
        self.inputs = RowSet(inf, [("Control name", 26), ("Value", 24)], "+ add input")
        self.inputs.pack(fill="x", padx=8, pady=6)

        outf = ttk.LabelFrame(root, text="Expected outputs  (indicator name → expected [→ tolerance])")
        outf.pack(fill="x", **pad)
        self.outputs = RowSet(outf, [("Indicator name", 26), ("Expected", 20), ("Tol", 8)], "+ add expected")
        self.outputs.pack(fill="x", padx=8, pady=6)

        br = ttk.Frame(root); br.pack(fill="x", **pad)
        ttk.Button(br, text="▶  Run Test", command=self.run_test).pack(side="left")
        self.verdict = ttk.Label(br, text="", font=("TkDefaultFont", 12, "bold"))
        self.verdict.pack(side="left", padx=12)

        ttk.Label(root, text="Results").pack(anchor="w", padx=10)
        self.log = scrolledtext.ScrolledText(root, height=12, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.inputs.add_row(); self.outputs.add_row()
        self.root.after(120, self.drain)

    # ---- helpers ----
    def pick_vi(self):
        p = filedialog.askopenfilename(title="Choose a .vi",
              filetypes=[("LabVIEW VI", "*.vi *.vit"), ("All files", "*.*")])
        if p: self.vi_path.set(p)

    def write(self, s): self.q.put(s)
    def set_verdict(self, text, color): self.q.put(("__verdict__", text, color))
    def drain(self):
        try:
            while True:
                item = self.q.get_nowait()
                if isinstance(item, tuple) and item and item[0] == "__verdict__":
                    self.verdict.configure(text=item[1], foreground=item[2]); continue
                self.log.configure(state="normal")
                self.log.insert("end", item + "\n"); self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(120, self.drain)

    def detect(self):
        """Prefill names from the VI's terminal labels (uses pylabview if present)."""
        path = self.vi_path.get().strip()
        if not path: return messagebox.showwarning("Pick a file", "Choose a .vi first.")
        if not os.path.exists(RR):
            return self.write("Detect needs pylabview (next to the converter). You can still type names by hand.")
        import subprocess, tempfile, re, glob
        tmp = tempfile.mkdtemp(prefix="videtect_")
        env = dict(os.environ); env["PYTHONPATH"] = PYL + os.pathsep + env.get("PYTHONPATH", "")
        subprocess.run([sys.executable, RR, "-x", "-i", os.path.abspath(path)],
                       cwd=tmp, env=env, capture_output=True, text=True)
        labels = []
        for xf in glob.glob(os.path.join(tmp, "*.xml")):
            txt = open(xf, encoding="utf-8", errors="replace").read()
            labels += re.findall(r'Label="([^"]+)"', txt)
        seen, uniq = set(), []
        for l in labels:
            if l not in seen and not l.startswith("'") and l not in ("Pane",):
                seen.add(l); uniq.append(l)
        self.write("Detected terminal labels: " + (", ".join(uniq) if uniq else "(none)"))
        self.write("  -> add the input controls under Inputs and the result indicators under Expected.\n")

    def run_test(self):
        path = self.vi_path.get().strip()
        if not path: return messagebox.showwarning("Pick a file", "Choose a .vi first.")
        ins  = self.inputs.values()
        outs = self.outputs.values()
        if not outs:
            return messagebox.showwarning("No expectations", "Add at least one expected output.")
        self.set_verdict("running…", "#888")
        threading.Thread(target=self._worker, args=(path, ins, outs), daemon=True).start()

    def _worker(self, path, ins, outs):
        try:
            import pythoncom, win32com.client
        except ImportError:
            self.write("✗ pywin32 not installed.  Run:  pip install pywin32")
            self.set_verdict("ERROR", "#c0392b"); return
        pythoncom.CoInitialize()
        try:
            from win32com.client import dynamic
            self.write("▶ Opening LabVIEW…")
            # late-binding dispatch is the robust pattern for the LabVIEW ActiveX server
            try:
                lv = dynamic.Dispatch("LabVIEW.Application")
            except Exception:
                lv = dynamic.Dispatch("Labview.Application")
            lv._FlagAsMethod("GetVIReference")
            vi = lv.GetVIReference(os.path.abspath(path))
            for m in ("SetControlValue", "GetControlValue", "Run"):
                vi._FlagAsMethod(m)
            self.write("  VI: %s" % path)
            for name, val in ins:
                v = parse_val(val)
                vi.SetControlValue(name, v)
                self.write("  set  %-20s = %r" % (name, v))
            self.write("  running…")
            vi.Run(True)   # run and wait until done
            allpass = True
            self.write("  results:")
            for row in outs:
                name = row[0]; exp = parse_val(row[1])
                tol = float(row[2]) if len(row) > 2 and row[2] else 1e-9
                act = vi.GetControlValue(name)
                try: act = list(act) if isinstance(act, tuple) else act
                except Exception: pass
                ok = approx(act, exp, tol)
                allpass = allpass and ok
                self.write("    %s  %-18s expected %r  got %r" %
                           ("PASS" if ok else "FAIL", name, exp, act))
            if allpass:
                self.write("✓ ALL PASS\n"); self.set_verdict("PASS", "#1e8449")
            else:
                self.write("✗ FAIL\n"); self.set_verdict("FAIL", "#c0392b")
        except Exception as e:
            self.write("✗ error: %s" % e)
            self.write("  (Is LabVIEW installed? Is the control/indicator name exact, case-sensitive?)")
            self.set_verdict("ERROR", "#c0392b")
        finally:
            pythoncom.CoUninitialize()


if __name__ == "__main__":
    root = tk.Tk(); App(root); root.mainloop()
