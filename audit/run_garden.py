"""Runs the corpus through Garden's fanout against every running origin and
records each server's parsed view and Garden's discrepancy category vs dusty."""
import base64, json, sys, os, time
GARDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(1, os.path.join(GARDEN, "tools"))
from targets import ORIGIN_DICT
from fanout import fanout
from diff import categorize_discrepancy, ErrorType
from http1 import HTTPRequest, HTTPResponse
import corpus

BAD = {ErrorType.TYPE_DISCREPANCY, ErrorType.REQUEST_DISCREPANCY, ErrorType.STREAM_DISCREPANCY, ErrorType.INVALID, ErrorType.DISCREPANCY}

def b64(b): return base64.b64encode(b).decode()

def view(items):
    out = []
    for r in items:
        if isinstance(r, HTTPRequest):
            out.append({"type": "request", "method": r.method.decode("latin1"), "uri": r.uri.decode("latin1"),
                        "version": r.version.decode("latin1"),
                        "headers": [[k.decode("latin1"), v.decode("latin1")] for k, v in r.headers],
                        "body_len": len(r.body), "body_b64": b64(r.body)})
        else:
            out.append({"type": "response", "code": r.code.decode("latin1"), "reason": r.reason.decode("latin1")})
    return out

def decode_cases():
    cases = []
    for cid, cat, rfc, pieces in corpus.CURATED:
        cases.append((cid, cat, rfc, [p.encode("latin1") for p in pieces]))
    tr = corpus.trophies(os.path.join(GARDEN, "TROPHIES.md"))
    for cid, cat, rfc, pieces in tr + corpus.with_host(tr):
        try:
            cases.append((cid, cat, rfc, [p.encode("latin1").decode("unicode-escape").encode("latin1") for p in pieces]))
        except Exception as e:
            print("skip", cid, e, file=sys.stderr)
    return cases

def run_case(names, stream):
    servers = [ORIGIN_DICT[n] for n in names]
    res = fanout(stream, servers)
    by = dict(zip(names, res))
    d = ORIGIN_DICT["dusty"]
    cmp = {}
    for n in names:
        if n == "dusty": continue
        cmp[n] = categorize_discrepancy(by["dusty"], by[n], d, ORIGIN_DICT[n]).name
    return by, cmp

def main():
    names = sorted(ORIGIN_DICT)
    assert "dusty" in names, names
    out = []
    for cid, cat, rfc, stream in decode_cases():
        by, cmp = run_case(names, stream)
        refs = [n for n in names if n != "dusty"]
        disagree = [n for n in refs if ErrorType[cmp[n]] in BAD]
        out.append({"id": cid, "category": cat, "rfc": rfc,
                    "stream_b64": [b64(p) for p in stream],
                    "stream_escaped": [repr(p)[2:-1] for p in stream],
                    "servers": {n: view(by[n]) for n in names},
                    "vs_dusty": cmp, "dusty_disagrees_with": disagree,
                    "dusty_disagrees_with_majority": len(disagree) * 2 > len(refs)})
        print(f"{cid:40s} dusty={summ(by['dusty'])} disagree={len(disagree)}/{len(refs)} {','.join(disagree)}", flush=True)
    json.dump({"servers": names, "cases": out}, open(sys.argv[1], "w"), indent=1)

def summ(items):
    return "|".join(("REQ" if isinstance(r, HTTPRequest) else r.code.decode()) for r in items) or "none"

if __name__ == "__main__":
    main()
