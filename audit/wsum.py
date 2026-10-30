import re, sys, json
def parse(path):
    lines = open(path, errors="replace").read().splitlines()
    res = {}
    for i, l in enumerate(lines):
        m = re.match(r"^\[(test_\w+)\] \(httpwookiee\.client\.(\w+)\.(\w+)\)", l)
        if m and i + 1 < len(lines):
            nxt = lines[i + 1]
            st = re.search(r"\.\.\. (.*)$", nxt)
            key = f"{m.group(2)}.{m.group(3)}.{m.group(1)}"
            if key in res: continue
            res[key] = st.group(1).strip() if st else nxt.strip()
    return res
out = {name: parse(p) for name, p in (a.split("=") for a in sys.argv[1:])}
json.dump(out, sys.stdout, indent=1)
