import os, random, json

random.seed(42)

BASE = "/home/claude/code_smell_project/projects"
PROJECTS = [
    "spring-sim", "guava-sim", "commons-sim", "picocli-sim",
    "gson-sim", "mybatis-sim", "hibernate-sim", "maven-sim",
    "log4j-sim", "tomcat-sim", "bc-java-sim", "commons-col-sim"
]

SMELL_DIST = {
    "GodClass": 0.12, "FeatureEnvy": 0.15, "LongMethod": 0.18,
    "DataClass": 0.15, "DeadCode": 0.10, "Clean": 0.30,
}

TYPES = ["int", "String", "boolean", "double", "long"]
DEFAULTS = ["0", "null", "false", "0.0", "\"\""]

def pick_smell():
    r = random.random()
    c = 0
    for s, p in SMELL_DIST.items():
        c += p
        if r < c:
            return s
    return "Clean"

def gen_god_class(pkg, name):
    nfields = random.randint(18, 28)
    lines = ["package " + pkg + ";", "", "import java.util.*;", "",
             "// [SMELL:GodClass]",
             "public class " + name + " {", ""]
    for i in range(nfields):
        t = random.choice(TYPES)
        d = random.choice(DEFAULTS)
        lines.append("    private " + t + " field" + str(i) + " = " + d + ";")
    lines.append("")
    for m in range(random.randint(14, 22)):
        lines.append("    public void process" + str(m) + "() {")
        for _ in range(random.randint(3, 7)):
            fi = random.randint(0, nfields - 1)
            lines.append("        field" + str(fi) + " = " + random.choice(DEFAULTS) + ";")
        lines.append("        return;")
        lines.append("    }")
        lines.append("")
    lines.append("}")
    return "\n".join(lines)

def gen_feature_envy(pkg, name):
    getters = ["getName", "getEmail", "getAge", "getAddress", "getPhone", "getCity", "getZip"]
    lines = ["package " + pkg + ";", "",
             "// [SMELL:FeatureEnvy]",
             "public class " + name + " {", "",
             "    private int localId;", "",
             "    public " + name + "(int id) { this.localId = id; }", "",
             "    public String buildReport(UserProfile other) {"]
    for i in range(random.randint(7, 12)):
        g = random.choice(getters)
        lines.append("        String val" + str(i) + " = other." + g + "();")
    lines.append("        return other.getName() + other.getEmail() + localId;")
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines)

def gen_long_method(pkg, name):
    nsteps = random.randint(58, 80)
    lines = ["package " + pkg + ";", "",
             "// [SMELL:LongMethod]",
             "public class " + name + " {", "",
             "    public int compute(int input) {",
             "        int step0 = input;"]
    for i in range(1, nsteps):
        prev = "step" + str(i - 1)
        cur = "step" + str(i)
        mult = random.randint(1, 9)
        add = random.randint(0, 50)
        lines.append("        int " + cur + " = " + prev + " * " + str(mult) + " + " + str(add) + ";")
    lines.append("        return step" + str(nsteps - 1) + ";")
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines)

def gen_data_class(pkg, name):
    nprops = random.randint(6, 13)
    lines = ["package " + pkg + ";", "",
             "// [SMELL:DataClass]",
             "public class " + name + " {", ""]
    props = []
    for i in range(nprops):
        t = random.choice(TYPES)
        pname = "prop" + str(i)
        props.append((t, pname))
        lines.append("    private " + t + " " + pname + ";")
    lines.append("")
    for t, pname in props:
        cap = pname[0].upper() + pname[1:]
        lines.append("    public " + t + " get" + cap + "() { return this." + pname + "; }")
        lines.append("    public void set" + cap + "(" + t + " val) { this." + pname + " = val; }")
        lines.append("")
    lines.append("}")
    return "\n".join(lines)

def gen_dead_code(pkg, name):
    lines = ["package " + pkg + ";", "",
             "// [SMELL:DeadCode]",
             "public class " + name + " {", "",
             "    public void liveMethod() {",
             "        System.out.println(\"alive\");",
             "    }", ""]
    for i in range(random.randint(3, 6)):
        lines.append("    // DEAD: never called")
        lines.append("    private void unusedHelper" + str(i) + "(int x) {")
        lines.append("        int y = x * " + str(random.randint(2, 9)) + ";")
        lines.append("        System.out.println(\"dead \" + y);")
        lines.append("    }")
        lines.append("")
    lines.append("}")
    return "\n".join(lines)

def gen_clean(pkg, name):
    lines = ["package " + pkg + ";", "",
             "import java.util.*;", "",
             "// [SMELL:Clean]",
             "public class " + name + " {", "",
             "    private final List<String> items;", "",
             "    public " + name + "() { this.items = new ArrayList<>(); }", "",
             "    public void add(String item) {",
             "        if (item != null && !item.isEmpty()) items.add(item);",
             "    }", "",
             "    public List<String> getItems() { return Collections.unmodifiableList(items); }",
             "    public int size() { return items.size(); }",
             "    public boolean contains(String item) { return items.contains(item); }",
             "}"]
    return "\n".join(lines)

GENS = {
    "GodClass": gen_god_class,
    "FeatureEnvy": gen_feature_envy,
    "LongMethod": gen_long_method,
    "DataClass": gen_data_class,
    "DeadCode": gen_dead_code,
    "Clean": gen_clean,
}

PREFIXES = [
    "Application","Service","Manager","Handler","Processor",
    "Controller","Engine","Executor","Validator","Builder",
    "Factory","Registry","Dispatcher","Resolver","Adapter",
    "Transformer","Converter","Calculator","Parser","Formatter",
    "Analyzer","Evaluator","Scheduler","Coordinator","Orchestrator",
]

metadata = []

for proj in PROJECTS:
    pkg_base = proj.replace("-sim", "").replace("-", ".")
    num_classes = random.randint(13, 18)
    used = set()
    proj_short = proj.replace("-sim", "").replace("-", "").title()

    for i in range(num_classes):
        smell = pick_smell()
        prefix = random.choice(PREFIXES)
        cname = prefix + proj_short + str(i)
        while cname in used:
            cname += "X"
        used.add(cname)

        pkg = pkg_base + ".v" + str(random.randint(1, 3))
        pkg_dir = os.path.join(BASE, proj, "src", "main", "java", *pkg.split("."))
        os.makedirs(pkg_dir, exist_ok=True)

        code = GENS[smell](pkg, cname)
        fpath = os.path.join(pkg_dir, cname + ".java")
        with open(fpath, "w") as f:
            f.write(code)

        metadata.append({
            "project": proj,
            "file_path": fpath,
            "class_name": cname,
            "package": pkg,
            "true_smell": smell,
        })

with open("/home/claude/code_smell_project/gold_set/ground_truth_meta.json", "w") as f:
    json.dump(metadata, f, indent=2)

print("Generated {} Java files across {} projects.".format(len(metadata), len(PROJECTS)))
for s in SMELL_DIST:
    count = sum(1 for m in metadata if m["true_smell"] == s)
    print("  {:15s}: {} files".format(s, count))
