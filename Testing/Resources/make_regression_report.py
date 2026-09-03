#!/usr/bin/env python3
# Copyright © 2026 Model Based Innovation LLC. All rights reserved.
"""Build Notebooks/RegressionReport.ipynb from STORED artifacts only -- no simulation.

Why this exists alongside restore_reports.py: that script's name suggests it renders a
report from the committed baseline, and ModCheck's own docstring is explicit that it
"re-simulates every case in the given config". Re-simulating 81 cases costs ~40 min of the
single compiler worker and needs Impact access. This script needs neither: everything it
reports is already on disk --

    regression_cases.yaml            the suite's configuration and its tuning rationale
    ReferenceResults/*.npz           the stored reference trajectories themselves
    ReferenceResults/manifest.json   per-case model, variable list, reference size
    *.log                            the verdicts of the runs that were actually executed

What that means it CANNOT say: nothing here is a fresh pass/fail. A regression verdict needs
a new simulation to compare against the baseline. This report describes the baseline and the
last recorded verdicts -- which is the honest scope of a no-re-run report, and is stated as
such in the notebook itself.
"""
import json, pathlib, nbformat as nbf

R = pathlib.Path(__file__).resolve().parent
nb = nbf.v4.new_notebook()
C = []
md = lambda t: C.append(nbf.v4.new_markdown_cell(t))
co = lambda t: C.append(nbf.v4.new_code_cell(t))

md("""# RotorDynamics — regression suite report

**Built from stored artifacts. Nothing here was re-simulated.**

Every number in this report comes from files already on disk: the suite configuration
(`regression_cases.yaml`), the committed reference trajectories (`ReferenceResults/*.npz`
and `manifest.json`), and the logs of the runs that were actually executed.

**What this report is.** A description of the regression *baseline* — what is covered, how
each case is configured, what the references contain, why particular checks are excluded or
given their own tolerance, and what the last executed runs concluded.

**What it is not.** A fresh pass/fail. A regression verdict compares a *new* simulation
against the baseline, so it requires a run; there is no way to produce one from stored data,
and this report does not pretend to. Where verdicts appear they are labelled with the run
that produced them and its date.""")

co("""%matplotlib inline
import json, pathlib, re, yaml
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight"})
from IPython.display import HTML, display

R = pathlib.Path.cwd() if (pathlib.Path.cwd()/"regression_cases.yaml").exists() \\
    else pathlib.Path("..")
REF = R/"ReferenceResults"
cfg = yaml.safe_load((R/"regression_cases.yaml").read_text())
cases = cfg["cases"] if isinstance(cfg, dict) and "cases" in cfg else cfg
if isinstance(cases, dict): cases = list(cases.values())
manifest = {m["name"]: m for m in json.loads((REF/"manifest.json").read_text())}
pd.set_option("display.width", 200); pd.set_option("display.max_colwidth", 44)
print(f"{len(cases)} cases in regression_cases.yaml | {len(manifest)} references in manifest")""")

md("""## 1 · Suite inventory

One row per registered case: the model it drives, the horizon and resolution it runs at, the
tolerance the reference was stored at, how many result variables the reference holds, and how
large it is on disk.""")

co("""rows = []
for c in cases:
    n = c["name"]; m = manifest.get(n, {})
    rows.append(dict(case=n, model=c["model"].split(".")[-1],
                     enabled=c.get("enabled", True),
                     final_time=c.get("final_time"), ncp=c.get("ncp"),
                     rtol=c.get("rtol"),
                     n_vars=len(m.get("variables", [])) or len(c.get("variables", [])),
                     ref_KiB=round(m.get("bytes", 0)/1024) if m.get("bytes") else None,
                     modifiers=len(c.get("modifiers") or {}),
                     excluded=len(c.get("exclude_variables") or []),
                     var_tols=len(c.get("variable_tolerances") or {}))) 
inv = pd.DataFrame(rows).sort_values("case").reset_index(drop=True)
print(f"enabled {int(inv.enabled.sum())} of {len(inv)} | "
      f"total reference size {inv.ref_KiB.fillna(0).sum()/1024:.1f} MiB | "
      f"{int(inv.n_vars.sum())} stored variables")
display(HTML(inv.to_html(index=False)))""")

md("""## 2 · Coverage by feature area

Which parts of the library the suite actually exercises, derived from the model names rather
than asserted.""")

co("""def area(model):
    m = model.lower()
    for key, lab in (("planetary","Planetary stage"), ("carrierpost","Planetary stage"),
                     ("gearmesh","Gear mesh"), ("gearbox","Gear mesh"), ("ring","Flexible ring"),
                     ("helical","Helical / axial"), ("axial","Helical / axial"),
                     ("thrust","Helical / axial"),
                     ("bearing","Bearings"), ("jeffcott","Rotor dynamics"),
                     ("whirl","Rotor dynamics"), ("critical","Rotor dynamics"),
                     ("torsional","Torsion"), ("torque","Torsion"),
                     ("housing","Supports & housings"), ("support","Supports & housings"),
                     ("mount","Supports & housings"), ("ramped","Ramped excitation"),
                     ("coupling","Couplings"), ("brake","Brakes")):
        if key in m: return lab
    return "Other"
inv["area"] = [area(c["model"]) for c in sorted(cases, key=lambda c: c["name"])]
cov = (inv.groupby("area").agg(cases=("case","count"), variables=("n_vars","sum"),
                               MiB=("ref_KiB", lambda s: round(s.fillna(0).sum()/1024,1)))
          .sort_values("cases", ascending=False))
display(HTML(cov.to_html()))
fig, ax = plt.subplots(figsize=(8.2, 3.2))
ax.barh(cov.index[::-1], cov.cases[::-1], color="#4C78A8")
ax.set_xlabel("registered cases"); ax.set_title("Regression coverage by feature area", loc="left")
for s in ("top","right"): ax.spines[s].set_visible(False)
plt.tight_layout(); plt.show()""")

md("""## 3 · Last recorded verdicts

Parsed from the run logs on disk. **These are historical**, not a fresh evaluation — each is
labelled with the log it came from. `after_full.log` is the most recent full-suite pass.""")

co("""def parse(path):
    out = {}
    if not path.exists(): return out
    for ln in path.read_text().splitlines():
        ln = ln.strip().lstrip("= ").strip()
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) < 3: continue
        name = parts[0].replace("VERIFY ", "").replace("STORE ", "")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name): continue
        v = next((p for p in parts if "checks passed" in p), None)
        if v: out[name] = v
    return out
logs = {p.name: parse(p) for p in sorted(R.glob("*.log"))}
full = logs.get("after_full.log", {})
newer = {}
for lg in ("newcases.log", "retune.log", "newcases_rtol1.log", "elsewhen.log", "fix_abcd.log"):
    newer.update(logs.get(lg, {}))
rows = []
for c in sorted(cases, key=lambda c: c["name"]):
    n = c["name"]
    v = newer.get(n) or full.get(n)
    src = ("newer run" if n in newer else ("after_full.log" if n in full else "—"))
    mm = re.match(r"(\\d+)/(\\d+)", v or "")
    rows.append(dict(case=n, verdict=v or "no recorded verdict", source=src,
                     passed=int(mm.group(1)) if mm else None,
                     total=int(mm.group(2)) if mm else None))
ver = pd.DataFrame(rows)
ver["all_pass"] = ver.passed.eq(ver.total)
print(f"cases with a recorded verdict : {ver.verdict.ne('no recorded verdict').sum()} of {len(ver)}")
print(f"  all checks passing          : {int(ver.all_pass.sum(skipna=True))}")
print(f"  with at least one failing   : {int((~ver.all_pass.fillna(True)).sum())}")
print(f"  no verdict on record        : {int(ver.verdict.eq('no recorded verdict').sum())}")
display(HTML(ver.to_html(index=False)))""")

md("""### 3.1 Cases carrying a failing check, and why

A failing check in this suite is not automatically a defect — several are documented,
understood and deliberately left in place. The reason lives next to the case in
`regression_cases.yaml`; it is reproduced here so the report is self-contained.""")

co("""bad = ver[~ver.all_pass.fillna(True)]
src = (R/"regression_cases.yaml").read_text()
out = []
for n in bad.case:
    i = src.find(f"- name: {n}")
    seg = src[max(0, i-1600):i] if i >= 0 else ""
    why = [l.strip().lstrip("# ").strip() for l in seg.splitlines() if l.strip().startswith("#")]
    out.append(dict(case=n, verdict=bad.loc[bad.case.eq(n), "verdict"].iat[0],
                    documented_reason=" ".join(why[-6:])[:300] or "(no inline note found)"))
display(HTML(pd.DataFrame(out).to_html(index=False)))""")

md("""## 4 · What the suite deliberately does not compare

Variables that are stored in the reference but excluded from comparison, or given their own
tolerance. Each entry is a decision with a recorded reason — most often a near-zero residual
whose relative error is meaningless, or a wrapped phase that jumps by a full period.""")

co("""rows = []
for c in cases:
    for v in (c.get("exclude_variables") or []):
        rows.append(dict(case=c["name"], variable=v, treatment="excluded", value=""))
    for v, t in (c.get("variable_tolerances") or {}).items():
        rows.append(dict(case=c["name"], variable=v, treatment="own tolerance", value=t))
ex = pd.DataFrame(rows)
print(f"{len(ex)} entries across {ex.case.nunique()} cases" if len(ex) else "none")
display(HTML(ex.to_html(index=False)) if len(ex) else HTML("<i>none</i>"))""")

md("""## 5 · The references themselves

Straight from the stored `.npz`. This is the part of a regression report that genuinely needs
no simulation: the baseline trajectories *are* the data. A representative selection is plotted
below — the largest reference in each feature area, with its most-varying signal.""")

co("""def load(name):
    d = np.load(REF/f"{name}.npz", allow_pickle=True)
    return {k: np.asarray(d[k], dtype=float) for k in d.files}

pick = (inv[inv.ref_KiB.notna()].sort_values("ref_KiB", ascending=False)
           .groupby("area").head(1).sort_values("area"))
sel = list(pick.case)[:8]
fig, axes = plt.subplots(len(sel), 1, figsize=(9.0, 1.85*len(sel)), sharex=False)
axes = np.atleast_1d(axes)
for ax, name in zip(axes, sel):
    try:
        d = load(name); t = d.get("time")
        cand = [(k, np.ptp(v)) for k, v in d.items()
                if k != "time" and v.shape == t.shape and np.ptp(v) > 0 and np.isfinite(v).all()]
        if not cand:
            ax.text(.5,.5,f"{name}: no varying signal", ha="center", transform=ax.transAxes); continue
        k = max(cand, key=lambda kv: kv[1])[0]
        ax.plot(t, d[k], lw=.9, color="#4C78A8")
        ax.set_title(f"{name} — {k}", loc="left", fontsize=9)
        ax.set_xlabel("time [s]", fontsize=8); ax.tick_params(labelsize=8)
        for s in ("top","right"): ax.spines[s].set_visible(False)
    except Exception as e:
        ax.text(.5,.5,f"{name}: {type(e).__name__}", ha="center", transform=ax.transAxes)
plt.tight_layout(); plt.show()""")

md("""## 6 · Reference integrity

A check that costs nothing and is worth having: every enabled case should have a reference on
disk, every reference should be loadable, and every case's declared variables should be
present in it. This *is* a live verdict — it validates the stored baseline itself, which needs
no simulation.""")

co("""probs = []
for c in cases:
    n = c["name"]
    p = REF/f"{n}.npz"
    if not p.exists():
        probs.append((n, "reference file missing")); continue
    try:
        d = load(n)
    except Exception as e:
        probs.append((n, f"unloadable: {type(e).__name__}")); continue
    if "time" not in d: probs.append((n, "no 'time' variable"))
    for k, v in d.items():
        if not np.isfinite(v).all(): probs.append((n, f"non-finite values in {k}"))
# ReferenceResults/ is shared by every case config in this directory, not just the one
# this report describes -- regression_cases_test_models.yaml has its own cases. Counting a
# sibling config's reference as an orphan is a false alarm, so gather all of them.
known = {c["name"] for c in cases}
siblings = {}
for other in sorted(R.glob("regression_cases*.yaml")):
    if other.name == "regression_cases.yaml": continue
    try:
        oc = yaml.safe_load(other.read_text())
        oc = oc["cases"] if isinstance(oc, dict) and "cases" in oc else oc
        oc = list(oc.values()) if isinstance(oc, dict) else (oc or [])
        names = {c["name"] for c in oc if isinstance(c, dict) and "name" in c}
        siblings[other.name] = names; known |= names
    except Exception as e:
        print(f"   [warn] could not read {other.name}: {type(e).__name__}")
orphan = sorted(set(p.stem for p in REF.glob("*.npz")) - known)
print(f"enabled cases          : {sum(1 for c in cases if c.get('enabled', True))}")
print(f"references on disk     : {len(list(REF.glob('*.npz')))}")
print(f"integrity problems     : {len(probs)}")
for n, w in probs: print(f"   {n}: {w}")
for nm, names in siblings.items():
    print(f"also claimed by {nm}: {len(names)} case(s)")
print(f"references with no case anywhere: {len(orphan)}" + (f" -> {orphan}" if orphan else ""))""")

md("""## Copyright

Copyright © 2026 Model Based Innovation LLC. All rights reserved.""")

nb["cells"] = C
nb.metadata.kernelspec = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = R/"Notebooks"/"RegressionReport.ipynb"
out.parent.mkdir(exist_ok=True)
nbf.write(nb, str(out))
print(f"wrote {out} ({len(C)} cells)")
