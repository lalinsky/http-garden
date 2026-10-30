"""Garden-style differential fuzzing: mutate seeds with Garden's mutations.py,
fan out to all origins, and keep inputs where dusty disagrees with most of the
reference servers while those references largely agree with each other."""
import json, os, random, sys, time
GARDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(1, os.path.join(GARDEN, "tools"))
from targets import ORIGIN_DICT
from fanout import fanout
from diff import categorize_discrepancy, ErrorType
from mutations import mutate
import run_garden

BAD = run_garden.BAD

def main():
    out_path, iters, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    random.seed(seed)
    names = sorted(ORIGIN_DICT)
    refs = [n for n in names if n != "dusty"]
    seeds = [c[3] for c in run_garden.decode_cases() if c[1] in ("framing/CL", "framing/CL-TE", "chunked", "pipelining", "request line", "header syntax")][:80]
    found, sigs = [], set()
    t0 = time.time()
    for i in range(iters):
        s = list(random.choice(seeds))
        for _ in range(random.randint(1, 4)):
            try:
                s = mutate(s)
            except Exception:
                break
        if not s or sum(map(len, s)) > 4000:
            continue
        servers = [ORIGIN_DICT[n] for n in names]
        try:
            res = fanout(s, servers)
        except Exception as e:
            continue
        by = dict(zip(names, res))
        d = ORIGIN_DICT["dusty"]
        cmp = {n: categorize_discrepancy(by["dusty"], by[n], d, ORIGIN_DICT[n]) for n in refs}
        dis = [n for n in refs if cmp[n] in BAD]
        if len(dis) * 2 <= len(refs):
            continue
        # How much do the references agree with each other?
        agree = sum(1 for a in refs for b in refs if a < b and categorize_discrepancy(by[a], by[b], ORIGIN_DICT[a], ORIGIN_DICT[b]) not in BAD)
        pairs = len(refs) * (len(refs) - 1) // 2
        sig = (run_garden.summ(by["dusty"]), tuple(sorted(dis)))
        rec = {"iter": i, "stream_b64": [run_garden.b64(p) for p in s], "stream_escaped": [repr(p)[2:-1] for p in s],
               "servers": {n: run_garden.view(by[n]) for n in names},
               "vs_dusty": {n: cmp[n].name for n in refs}, "dusty_disagrees_with": dis,
               "ref_pair_agreement": agree / pairs, "new_signature": sig not in sigs}
        sigs.add(sig)
        found.append(rec)
        print(f"[{i}] dis={len(dis)} refagree={agree/pairs:.2f} dusty={sig[0]} {s!r}"[:400], flush=True)
    json.dump({"iters": iters, "seed": seed, "elapsed": time.time() - t0, "found": found}, open(out_path, "w"), indent=1)

if __name__ == "__main__":
    main()
