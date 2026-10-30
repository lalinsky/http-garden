"""Assemble results.json from the Garden corpus run, the fuzz runs and the
HTTPWookiee runs. Verdicts for cases where dusty disagrees with the majority
come from verdicts.py (hand triage)."""
import json, sys, base64, datetime
import verdicts

def load(p):
    return json.load(open(p))

def server_entry(items):
    reqs = [r for r in items if r["type"] == "request"]
    resps = [r for r in items if r["type"] == "response"]
    first = items[0] if items else None
    return {
        "accepted": bool(first and first["type"] == "request"),
        "status": (first["code"] if first and first["type"] == "response" else ("200" if first else None)),
        "no_response": not items,
        "request_count": len(reqs),
        "items": [
            ({"type": "request", "method": r["method"], "uri": r["uri"], "version": r["version"],
              "headers": r["headers"], "body_len": r["body_len"]} if r["type"] == "request"
             else {"type": "response", "status": r["code"]})
            for r in items],
    }

def case_entry(c, source):
    v = verdicts.fuzz(c) if source == "garden-fuzz" else verdicts.lookup(c["id"], c)
    return {
        "id": c["id"], "source": source, "category": c["category"],
        "rfc": v.get("rfc") or c.get("rfc") or "",
        "request_b64": c["stream_b64"], "request_escaped": c["stream_escaped"],
        "servers": {n: server_entry(items) for n, items in c["servers"].items()},
        "garden_category_vs_dusty": c["vs_dusty"],
        "dusty_disagrees_with": c["dusty_disagrees_with"],
        "dusty_disagrees_with_majority": c["dusty_disagrees_with_majority"],
        "verdict": v["verdict"], "note": v["note"],
    }

def main(corpus_json, fuzz_jsons, wookiee_json, meta_json, out):
    corpus = load(corpus_json)
    cases = [case_entry(c, "garden-corpus") for c in corpus["cases"]]
    fuzz = []
    for fj in fuzz_jsons:
        f = load(fj)
        for r in f["found"]:
            c = {"id": f"fuzz-s{f['seed']}-i{r['iter']}", "category": "fuzz", "rfc": "",
                 "stream_b64": r["stream_b64"], "stream_escaped": r["stream_escaped"],
                 "servers": r["servers"], "vs_dusty": r["vs_dusty"],
                 "dusty_disagrees_with": r["dusty_disagrees_with"],
                 "dusty_disagrees_with_majority": True}
            e = case_entry(c, "garden-fuzz")
            e["ref_pair_agreement"] = r["ref_pair_agreement"]
            fuzz.append(e)
    w = load(wookiee_json)
    wcases = []
    for key in sorted(w["dusty"]):
        per = {s: w[s].get(key) for s in w}
        v = verdicts.wookiee(key, per)
        wcases.append({"id": "wookiee:" + key, "source": "httpwookiee", "category": "httpwookiee/" + key.split(".")[0],
                       "test": key, "results": per, "verdict": v["verdict"], "note": v["note"], "rfc": v.get("rfc", "")})
    meta = load(meta_json)
    meta["generated"] = datetime.date.today().isoformat()
    meta["counts"] = {"garden_corpus_cases": len(cases), "garden_fuzz_kept": len(fuzz),
                      "fuzz_iterations": [load(fj)["iters"] for fj in fuzz_jsons], "wookiee_tests": len(wcases)}
    json.dump({"metadata": meta, "confirmed_dusty_issues": verdicts.ISSUES,
               "garden_cases": cases, "garden_fuzz": fuzz, "httpwookiee": wcases},
              open(out, "w"), indent=1)

if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1].split(","), a[2], a[3], a[4])
