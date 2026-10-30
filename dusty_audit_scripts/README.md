# dusty audit

This branch adds [dusty](https://github.com/lalinsky/dusty) to the Garden as an
origin, plus the scripts used to audit it.

- `images/dusty`: an echo server on dusty, built from the commit pinned in
  `docker-compose.yml` (`APP_VERSION`). Bump it to re-audit a newer dusty.
- `images/node_prebuilt`: `node_stdlib` from an official Node release binary
  instead of a source build, for a quick llhttp reference.
- `dusty_audit_scripts/`: the corpus, the runners and the result builder.

## Running

Start dusty and the references:

```sh
./garden.sh start --build dusty aiohttp apache_httpd go_stdlib gunicorn h2o hyper libsoup lighttpd nginx puma waitress node_prebuilt haproxy nginx_proxy apache_httpd_proxy
```

Then, from the repo root, with Garden's Python dependencies installed:

```sh
python dusty_audit_scripts/run_garden.py out/corpus.json      # corpus: TROPHIES.md payloads + hand-written cases
python dusty_audit_scripts/run_fuzz.py out/fuzz1.json 4000 1  # mutation fuzzing: output, iterations, seed
```

`run_garden.py` and `run_fuzz.py` compare every origin's parsed view of each
input against dusty's, using Garden's own discrepancy categories. A case where
dusty disagrees with most references while they agree with each other is a
candidate; it still needs triage against the RFCs.

[HTTPWookiee](https://github.com/regilero/HTTPWookiee) runs separately against
the dusty container with `dusty_audit_scripts/wookiee-dusty.conf` (set
`SERVER_IP` to the container's address). `wsum.py name=log ...` summarises its logs as JSON.

`build_results.py` combines all of the above into one `results.json`:

```sh
python dusty_audit_scripts/build_results.py out/corpus.json out/fuzz1.json,out/fuzz2.json out/wookiee.json out/meta.json out/results.json
```

`meta.json` describes the run (Garden, dusty and reference versions).

## Triage

`verdicts.py` holds the hand triage from the first audit (2026-10-29, dusty
b1f776b): the confirmed issues and the differences judged allowed by the RFCs.
`build_results.py` applies it to every case, so on a re-run anything it does
not cover shows up untriaged. The issues it lists have since been fixed in
dusty, so on a newer dusty those cases should now agree with the references.
