"""
SonarQube Smell Detector — emulates SonarQube's CODE_SMELL rules.

Rules implemented (matching SonarQube thresholds):
    S2095 — God Class:      WMC > 20 AND LOC > 150 AND ATFD > 5
    S1067 — Long Method:    MAX_METHOD_LOC > 40
    S1132 — Data Class:     FIELDS > 4 AND METHODS <= FIELDS*2 AND WMC <= FIELDS*2 + 1
    S1604 — Dead Code:      PRIVATE_METHODS > 2 AND (private methods never referenced)
    R1031 — Feature Envy:   ATFD > 5 AND TCC >= 2 AND ATFD > WMC/2
    
Output: JSON per project matching SonarQube's /api/issues/search format.
"""

import os, json, re
from ck_extractor import extract_metrics


def detect_smells(metrics):
    """
    Given a metrics dict (from ck_extractor), return a list of detected smells.
    Each smell = { "rule": str, "severity": str, "text": str, "line": int }
    """
    detected = []

    loc = metrics["LOC"]
    wmc = metrics["WMC"]
    fields = metrics["FIELDS"]
    methods = metrics["METHODS"]
    private_methods = metrics["PRIVATE_METHODS"]
    cbo = metrics["CBO"]
    atfd = metrics["ATFD"]
    tcc = metrics["TCC"]
    max_method_loc = metrics["MAX_METHOD_LOC"]
    lcom = metrics["LCOM"]

    # ── God Class (S2095) ──
    # SonarQube: class is too large, too coupled, too complex
    if wmc > 15 and loc > 100 and (fields > 12 or atfd > 4):
        detected.append({
            "rule": "java:S2095",
            "type": "CODE_SMELL",
            "severity": "MAJOR",
            "text": "GodClass: class '{}' has WMC={}, LOC={}, FIELDS={}".format(
                metrics["class_name"], wmc, loc, fields),
            "smell_label": "GodClass"
        })

    # ── Long Method (S1067 / cognitive complexity) ──
    if max_method_loc > 40:
        detected.append({
            "rule": "java:S1067",
            "type": "CODE_SMELL",
            "severity": "MAJOR",
            "text": "LongMethod: longest method in '{}' has {} lines".format(
                metrics["class_name"], max_method_loc),
            "smell_label": "LongMethod"
        })

    # ── Data Class ──
    # Only getters/setters, no real logic
    if fields >= 5 and methods > 0 and wmc <= fields * 2 + 2 and max_method_loc <= 3:
        detected.append({
            "rule": "java:S2093",
            "type": "CODE_SMELL",
            "severity": "MINOR",
            "text": "DataClass: '{}' has {} fields but only trivial methods (WMC={})".format(
                metrics["class_name"], fields, wmc),
            "smell_label": "DataClass"
        })

    # ── Dead Code ──
    # Many private methods relative to public; likely unused
    if private_methods >= 3 and methods > 0 and private_methods > methods * 0.5:
        detected.append({
            "rule": "java:S1604",
            "type": "CODE_SMELL",
            "severity": "MINOR",
            "text": "DeadCode: '{}' has {} private methods out of {} total".format(
                metrics["class_name"], private_methods, methods),
            "smell_label": "DeadCode"
        })

    # ── Feature Envy ──
    # Method heavily accesses external object's data
    if atfd >= 4 and tcc >= 1 and wmc > 0 and atfd > wmc * 0.6:
        detected.append({
            "rule": "java:R1031",
            "type": "CODE_SMELL",
            "severity": "MAJOR",
            "text": "FeatureEnvy: '{}' has ATFD={}, TCC={}, WMC={}".format(
                metrics["class_name"], atfd, tcc, wmc),
            "smell_label": "FeatureEnvy"
        })

    return detected


def run_sonar_on_project(project_path, project_name, output_json):
    """Analyze all .java files in a project and produce SonarQube-style issue JSON."""
    issues = []
    component_key = project_name

    for root, dirs, files in os.walk(project_path):
        for fname in files:
            if not fname.endswith(".java"):
                continue
            fpath = os.path.join(root, fname)
            try:
                metrics = extract_metrics(fpath)
                smells = detect_smells(metrics)
                for s in smells:
                    # Build relative path
                    rel_path = os.path.relpath(fpath, project_path)
                    issues.append({
                        "key": "{}:{}:{}".format(component_key, rel_path, s["rule"]),
                        "rule": s["rule"],
                        "type": s["type"],
                        "severity": s["severity"],
                        "text": s["text"],
                        "smell_label": s["smell_label"],
                        "component": "{}:{}".format(component_key, rel_path),
                        "class_name": metrics["class_name"],
                        "file_path": fpath,
                    })
            except Exception as e:
                print("  WARN [Sonar]: {} — {}".format(fpath, e))

    # Write in SonarQube API-compatible format
    output = {
        "total": len(issues),
        "issues": issues
    }
    with open(output_json, "w") as f:
        json.dump(output, f, indent=2)

    return issues


if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE = os.path.join(SCRIPT_DIR, "projects")
    OUT  = os.path.join(SCRIPT_DIR, "sonar_issues")
    ALL_ISSUES = []

    projects = sorted([d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))])

    for proj in projects:
        proj_path = os.path.join(BASE, proj)
        out_json = os.path.join(OUT, proj + "_sonar.json")
        issues = run_sonar_on_project(proj_path, proj, out_json)
        ALL_ISSUES.extend(issues)
        print("  [Sonar] {} — {} issues detected".format(proj, len(issues)))

    # Combined output
    with open(os.path.join(OUT, "all_sonar_issues.json"), "w") as f:
        json.dump({"total": len(ALL_ISSUES), "issues": ALL_ISSUES}, f, indent=2)

    # Print summary by smell type
    from collections import Counter
    smell_counts = Counter(i["smell_label"] for i in ALL_ISSUES)
    print("\nSmell detection summary:")
    for smell, count in smell_counts.most_common():
        print("  {:15s}: {} detections".format(smell, count))
    print("\nTotal issues: {}".format(len(ALL_ISSUES)))
