"""
CK Metrics Extractor — pure-Python replacement for the mauricioaniche/ck JAR.
Computes per-class metrics by parsing .java files with regex + AST-style logic.

Metrics extracted:
    LOC          — Lines of Code (non-blank, non-comment)
    WMC          — Weighted Methods per Class (count of methods; simplified: 1 per method)
    NOC          — Number of Classes in file (usually 1)
    CBO          — Coupling Between Objects (number of distinct external types referenced)
    LCOM         — Lack of Cohesion of Methods (simplified: methods - shared fields ratio)
    DIT          — Depth of Inheritance Tree (0 if no extends, 1 if extends something)
    TCC          — Technical Coupling Complexity (distinct external classes used in methods)
    ATFD         — Access to Foreign Data (number of get/set calls on other objects)
    FIELDS       — Number of fields declared
    METHODS      — Number of methods declared
    MAX_METHOD_LOC — LOC of the longest method
    PRIVATE_METHODS— Number of private methods (dead code indicator)
"""

import re, os, json, csv
from collections import defaultdict

def extract_metrics(filepath):
    """Parse one .java file and return a dict of metrics."""
    with open(filepath, "r", errors="ignore") as f:
        raw = f.read()

    lines = raw.split("\n")

    # ── LOC: non-blank, non-comment lines ──
    loc = 0
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            continue
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        loc += 1

    # ── Extract class name ──
    class_match = re.search(r"public\s+class\s+(\w+)", raw)
    classname = class_match.group(1) if class_match else os.path.basename(filepath).replace(".java", "")

    # ── Package ──
    pkg_match = re.search(r"package\s+([\w.]+)", raw)
    package = pkg_match.group(1) if pkg_match else ""

    # ── Fields ──
    field_pattern = re.compile(r"^\s+private\s+\w+[\w<>\[\],\s]*\s+(\w+)\s*[=;]", re.MULTILINE)
    fields = field_pattern.findall(raw)
    num_fields = len(fields)

    # ── Methods ──
    # Match method declarations (public/private/protected + return type + name + parens)
    method_pattern = re.compile(
        r"^\s+(public|private|protected)\s+[\w<>\[\]]+\s+(\w+)\s*\(", re.MULTILINE
    )
    method_matches = method_pattern.findall(raw)
    num_methods = len(method_matches)
    private_methods = sum(1 for vis, _ in method_matches if vis == "private")

    # ── WMC (simplified: 1 per method) ──
    wmc = num_methods

    # ── Method bodies & MAX_METHOD_LOC ──
    # Find each method block by scanning for opening braces
    method_locs = []
    method_body_pattern = re.compile(
        r"(public|private|protected)\s+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{", re.MULTILINE
    )
    for match in method_body_pattern.finditer(raw):
        start = match.end() - 1  # position of opening {
        depth = 0
        end = start
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        body = raw[start:end+1]
        body_loc = sum(1 for l in body.split("\n")
                       if l.strip() and not l.strip().startswith("//")
                       and not l.strip().startswith("*"))
        method_locs.append(body_loc)

    max_method_loc = max(method_locs) if method_locs else 0

    # ── CBO: distinct external types referenced ──
    # Look for Type references that aren't java.lang basics
    builtin = {"int","long","double","float","boolean","char","byte","short","void",
               "String","Object","System","Math","Integer","Long","Double","Float",
               "Boolean","Comparable","Iterable","Exception","RuntimeException"}
    type_pattern = re.compile(r"\b([A-Z]\w+)\b")
    referenced_types = set(type_pattern.findall(raw)) - builtin - {classname}
    cbo = len(referenced_types)

    # ── DIT ──
    dit = 1 if re.search(r"extends\s+\w+", raw) else 0

    # ── LCOM (simplified) ──
    # Count how many methods use each field
    field_usage = defaultdict(int)
    for match in method_body_pattern.finditer(raw):
        start = match.end() - 1
        depth = 0
        end = start
        for i in range(start, len(raw)):
            if raw[i] == "{": depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        body = raw[start:end+1]
        for f in fields:
            if f in body:
                field_usage[f] += 1

    if num_methods > 1 and num_fields > 0:
        # LCOM = pairs of methods that DON'T share a field
        shared = sum(1 for f in fields if field_usage[f] > 1)
        lcom = max(0, num_methods - shared)
    else:
        lcom = 0

    # ── TCC: technical coupling (external method calls) ──
    # Count calls like obj.method() where obj isn't 'this'
    call_pattern = re.compile(r"(\w+)\.\w+\(")
    calls = call_pattern.findall(raw)
    external_calls = [c for c in calls if c not in ("this", "System", "Math", "super", classname)]
    tcc = len(set(external_calls))

    # ── ATFD: access to foreign data ──
    # Count getter/setter calls on other objects
    atfd_pattern = re.compile(r"(?!this)\b\w+\.(?:get|set)\w+\(")
    atfd = len(atfd_pattern.findall(raw))

    return {
        "file_path": filepath,
        "class_name": classname,
        "package": package,
        "LOC": loc,
        "WMC": wmc,
        "METHODS": num_methods,
        "FIELDS": num_fields,
        "PRIVATE_METHODS": private_methods,
        "CBO": cbo,
        "DIT": dit,
        "LCOM": lcom,
        "TCC": tcc,
        "ATFD": atfd,
        "MAX_METHOD_LOC": max_method_loc,
        "NOC": 1,
        "raw_code": raw,
    }


def run_on_project(project_path, project_name, output_csv):
    """Walk a project directory, extract metrics for every .java file."""
    results = []
    for root, dirs, files in os.walk(project_path):
        for fname in files:
            if fname.endswith(".java"):
                fpath = os.path.join(root, fname)
                try:
                    m = extract_metrics(fpath)
                    m["project"] = project_name
                    results.append(m)
                except Exception as e:
                    print("  WARN: {} — {}".format(fpath, e))
    # Write CSV (exclude raw_code for CSV)
    if results:
        keys = [k for k in results[0].keys() if k != "raw_code"]
        with open(output_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in results:
                row = {k: r[k] for k in keys}
                w.writerow(row)
    return results


if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE = os.path.join(SCRIPT_DIR, "projects")
    OUT  = os.path.join(SCRIPT_DIR, "ck_metrics")
    ALL  = []

    projects = [d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))]
    projects.sort()

    for proj in projects:
        proj_path = os.path.join(BASE, proj)
        out_csv = os.path.join(OUT, proj + "_ck.csv")
        results = run_on_project(proj_path, proj, out_csv)
        ALL.extend(results)
        print("  [CK] {} — {} classes extracted".format(proj, len(results)))

    # Also save combined JSON (with raw_code for later use)
    with open(os.path.join(OUT, "all_ck_metrics.json"), "w") as f:
        json.dump(ALL, f, indent=2)

    print("\nTotal: {} classes across {} projects".format(len(ALL), len(projects)))
    print("Saved to: ck_metrics/")
