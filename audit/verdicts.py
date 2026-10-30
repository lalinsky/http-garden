"""Hand triage of every case where dusty disagrees with a majority of the
reference servers. Anything not listed here and in agreement is 'agree'."""
import re

ISSUES_UNSORTED = [
    {"id": "D2", "title": "HTTP/1.0 request with Transfer-Encoding: chunked is decoded as chunked and the connection kept alive",
     "severity": "low-medium",
     "request": "POST /a HTTP/1.0\\r\\nConnection: keep-alive\\r\\nTransfer-Encoding: chunked\\r\\n\\r\\n1\\r\\nZ\\r\\n0\\r\\n\\r\\nGET /b HTTP/1.1\\r\\nHost: a\\r\\n\\r\\n",
     "dusty": "200 for /a with body 'Z', then 200 for the pipelined /b on the same connection",
     "rfc": "RFC 9112 6.1 (HTTP/1.0 message with Transfer-Encoding MUST be treated as faulty framing and the connection closed after it)",
     "references": "Pipelined variant (te-http10-ka-pipe): gunicorn, hyper, lighttpd, nginx -> 400; go_stdlib and waitress ignore TE (empty body) and then 400 on the chunk bytes; apache_httpd, libsoup, node (llhttp 9.4.3) decode and close; aiohttp, h2o, puma decode and keep going like dusty. Proxies: haproxy forwards it as HTTP/1.0+chunked without keep-alive, apache_httpd_proxy rewrites to Content-Length, nginx_proxy rejects - so none of the three tested proxies sets up the desync.",
     "smuggling": "TE.0-style desync: a front end that ignores Transfer-Encoding on an HTTP/1.0 request (or forwards it as length-0) and reuses the upstream connection sees the chunked body as the next request, while dusty consumes it as body (or vice versa). Needs a front end that forwards HTTP/1.0 keep-alive requests verbatim.",
     "root_cause": "llhttp accepts Transfer-Encoding in HTTP/1.0 and llhttp_should_keep_alive() honours 'Connection: keep-alive'; dusty's wrapper does not check the combination",
     "code": ["src/parser.zig:346 (RequestParser.onHeadersComplete: no 1.0+TE check)", "src/server.zig:1291 (keep-alive taken from llhttp_should_keep_alive)", "src/llhttp/http.c:70 (F_CHUNKED framing used regardless of HTTP version)"],
     "layer": "llhttp behaviour, fixable in dusty's wrapper"},
    {"id": "D1", "title": "Empty Transfer-Encoding value is ignored; body framed by Content-Length (or as zero-length)",
     "severity": "medium",
     "request": "POST /a HTTP/1.1\\r\\nHost: a\\r\\nTransfer-Encoding:\\r\\nContent-Length: 5\\r\\n\\r\\n0\\r\\n\\r\\nGET /b HTTP/1.1\\r\\nHost: a\\r\\n\\r\\n",
     "dusty": "200 for /a with body '0\\r\\n\\r\\n' (CL framing), then 200 for /b. Without Content-Length the body is taken as empty. With the headers in the other order (Content-Length first) dusty answers 400, so the result depends on header order.",
     "rfc": "RFC 9112 6.1 / 6.3 rule 4 (TE present and chunked not final in a request: 400 and close); RFC 9112 6.1 (TE with CL: ought to be an error); RFC 9110 5.6.1 (1#transfer-coding needs one element)",
     "references": "10 of 12 reject (400/501), including node with llhttp 9.4.3; lighttpd and waitress also take CL. Proxies haproxy, nginx_proxy, apache_httpd_proxy all reject, so none of them forwards it.",
     "smuggling": "CL.TE-family desync: a front end that treats the presence of a Transfer-Encoding header as 'not CL framed' (or rejects/strips CL because of it) disagrees with dusty about where the body ends. Also lets a client sneak TE+CL past the TE/CL conflict check by leaving the TE value empty.",
     "root_cause": "llhttp only sets F_TRANSFER_ENCODING when the TE value has a first non-whitespace byte, so an empty or all-whitespace value never reaches the TE/CL conflict check or the 'chunked not final' check",
     "code": ["src/llhttp/llhttp.c:2811-2832 (header_value_discard_ws: an empty value goes CR -> discard_lws and never reaches the span start at :2808 that leads to load_header_state_3 / test_flags_3 at :8526 / c_or_flags_18 at :1065, which set F_TRANSFER_ENCODING)", "src/llhttp/http.c:73 (F_TRANSFER_ENCODING check never fires)", "src/parser.zig:318-344 (onHeaderValueComplete could catch an empty TE value)"],
     "layer": "llhttp bug, fixed upstream in llhttp 9.4.3 (nodejs/llhttp#874, 'Do not allow empty transfer-encoding'); dusty vendors 9.3.1"},
    {"id": "D4", "title": "Header values keep trailing whitespace (OWS)",
     "severity": "low",
     "request": "GET / HTTP/1.1\\r\\nHost: a\\r\\nX: y \\r\\n\\r\\n",
     "dusty": "header X = 'y ' (also 'chunked ' for Transfer-Encoding, '3 ' for Content-Length, 'close ' for Connection as seen by handlers)",
     "rfc": "RFC 9110 5.5 (field value excludes leading and trailing OWS); RFC 9112 5.1",
     "references": "all 12 references strip it, including node (llhttp + JS layer); haproxy, nginx_proxy and apache_httpd_proxy strip it when forwarding",
     "smuggling": "none at the framing level (llhttp interprets TE/CL/Connection itself and tolerates the whitespace). App-level: handlers comparing header values (auth tokens, Content-Type, custom routing headers, Upgrade/Connection checks in middleware) see a different value than a proxy that trimmed it; Request.content_length is null for 'Content-Length: 3 ' because parseInt fails.",
     "root_cause": "llhttp's on_header_value span includes trailing whitespace by design; dusty trims only Host",
     "code": ["src/parser.zig:327 (trimEnd applied only to Host)", "src/parser.zig:337 (headers.add with untrimmed value)", "src/parser.zig:363-364 (content_length parse of untrimmed value)"],
     "layer": "dusty wrapper"},
    {"id": "D3", "title": "'Connection: close' followed by HTAB is not recognised; the connection stays open",
     "severity": "low",
     "request": "GET /1 HTTP/1.1\\r\\nHost: a\\r\\nConnection: close\\t\\r\\n\\r\\nGET /2 HTTP/1.1\\r\\nHost: a\\r\\n\\r\\n",
     "dusty": "200 for /1 and 200 for /2 on the same connection (with a trailing SP instead of HTAB dusty closes after /1)",
     "rfc": "RFC 9112 9.6 (close connection option); RFC 9110 5.5/5.6.1 (OWS includes HTAB)",
     "references": "all 12 references either close after /1 or reject (aiohttp, node 400)",
     "smuggling": "connection-persistence disagreement: a peer that relies on 'close' to end the exchange sees dusty parse whatever follows as a new request. Low on its own; front ends normally rewrite Connection.",
     "root_cause": "llhttp 9.3.1 Connection-token matcher does not accept a trailing HTAB; fixed upstream in llhttp 9.4.2 (nodejs/llhttp#866)",
     "code": ["src/llhttp/llhttp.c (header_value_connection states)", "src/server.zig:1291 (keep-alive decision from llhttp_should_keep_alive)"],
     "layer": "llhttp bug, fixed upstream"},
    {"id": "D5", "title": "Unknown transfer codings before chunked are accepted and left undecoded",
     "severity": "low",
     "request": "POST /a HTTP/1.1\\r\\nHost: a\\r\\nTransfer-Encoding: gzip, chunked\\r\\n\\r\\n3\\r\\nabc\\r\\n0\\r\\n\\r\\n",
     "dusty": "200, body 'abc' handed to the handler as if identity (same for 'foo, chunked' and 'identity, chunked')",
     "rfc": "RFC 9112 6.1 (server receiving a transfer coding it does not understand SHOULD respond 501); RFC 9112 7 (registered codings)",
     "references": "'gzip, chunked': go_stdlib, h2o, libsoup, nginx, waitress reject (501/400); others accept. 'foo, chunked': 7 of 12 reject. node (llhttp 9.4.3) accepts like dusty.",
     "smuggling": "none (chunked is final, so framing is unambiguous); data integrity: the handler receives still-coded bytes with no indication",
     "root_cause": "llhttp only checks that chunked is the final coding; dusty decodes Content-Encoding but never inspects Transfer-Encoding",
     "code": ["src/parser.zig:346-371 (onHeadersComplete reads Content-Encoding only)"],
     "layer": "dusty wrapper (llhttp by design)"},
    {"id": "D6", "title": "Request-target leniencies: 'OPTIONS *x', 'GET *', fragment in target, CONNECT with origin-form",
     "severity": "low",
     "request": "OPTIONS *x HTTP/1.1\\r\\nHost: a\\r\\n\\r\\n",
     "dusty": "200 with url '*x'; 'GET *' -> url '*'; 'GET /a#frag' -> url '/a#frag'; 'CONNECT /x' -> accepted, url '/x'",
     "rfc": "RFC 9112 3.2 (request-target forms; no fragment), 3.2.3 (authority-form only for CONNECT), 3.2.4 (asterisk-form only for OPTIONS, exactly '*')",
     "references": "'*x' rejected by 7 of 12 (node accepts, same llhttp); fragment rejected/stripped by 7 of 12 (node keeps it); CONNECT origin-form rejected by 7 of 12 incl. node",
     "smuggling": "none at the framing level; routing/ACL confusion only if an app or front end treats these targets differently",
     "root_cause": "llhttp's URL parser is lenient for these; dusty's checkTarget lets anything starting with '/' or '*' through",
     "code": ["src/parser.zig:380-385 (checkTarget: CONNECT and '*' targets not validated)"],
     "layer": "llhttp leniency, fixable in dusty's wrapper"},
    {"id": "D7", "title": "BWS in chunk extensions rejected",
     "severity": "info",
     "request": "POST / HTTP/1.1\\r\\nHost: a\\r\\nTransfer-Encoding: chunked\\r\\n\\r\\n3 ; a = b\\r\\nabc\\r\\n0\\r\\n\\r\\n",
     "dusty": "400",
     "rfc": "RFC 9112 7.1.1 (chunk-ext allows BWS); RFC 9110 5.6.3 (recipient MUST parse and remove BWS)",
     "references": "6 of 12 accept (apache_httpd, gunicorn, h2o, hyper, lighttpd, nginx); node rejects like dusty",
     "smuggling": "none (fails closed)",
     "root_cause": "llhttp strict mode rejects whitespace after chunk size and around '=' on purpose",
     "code": ["src/llhttp (strict chunk-size/extension parsing; lenient flag llhttp_set_lenient_spaces_after_chunk_size not set)"],
     "layer": "llhttp (deliberate hardening)"},
    {"id": "D8", "title": "Bare CR bytes before the request line are skipped",
     "severity": "info",
     "request": "\\r\\r\\r\\r\\rGET /a HTTP/1.1\\r\\nHost: a\\r\\n\\r\\n",
     "dusty": "200 (also between pipelined requests: 'GET /a ...\\r\\n\\r\\n\\rGET /b ...' -> two requests)",
     "rfc": "RFC 9112 2.2 (only empty lines, i.e. CRLF, may be ignored before the request-line; a bare CR MUST be treated as invalid or replaced by SP)",
     "references": "'\\r\\r\\rGET' accepted by dusty, nginx, libsoup, node; rejected by 8 of 12. HTTPWookiee 3020 fails for dusty and nginx, passes for hyper.",
     "smuggling": "low: needs a front end that forwards a bare-CR-prefixed request instead of rejecting it",
     "root_cause": "llhttp skips any CR/LF in the start state",
     "code": ["src/llhttp/llhttp.c (start-state CR/LF skipping)"],
     "layer": "llhttp"},
]

ISSUES = sorted(ISSUES_UNSORTED, key=lambda i: int(i['id'][1:]))

def _st(c, n):
    items = c["servers"].get(n, [])
    return items

def lookup(cid, c):
    base = re.sub(r"\+host$", "", cid)
    if base in MANUAL:
        verdict, note, *rfc = MANUAL[base]
        return {"verdict": verdict, "note": note, "rfc": rfc[0] if rfc else ""}
    if not c.get("dusty_disagrees_with_majority"):
        if c["dusty_disagrees_with"]:
            return {"verdict": "agree", "note": "dusty matches the majority; minority: " + ", ".join(c["dusty_disagrees_with"])}
        return {"verdict": "agree", "note": "all servers agree with dusty"}
    d = c["servers"].get("dusty", [])
    if d and d[0]["type"] == "response":
        return {"verdict": "allowed-difference", "note": "dusty rejects (" + d[0]["code"] + ") where most references accept; failing closed, not a framing disagreement"}
    return {"verdict": "UNTRIAGED", "note": "dusty accepts where most references reject or parse differently"}

MANUAL = {
    "conn-close-tab-pipe": ("dusty-bug", "D3: 'close\\t' not recognised, /2 served on the same connection", "RFC 9112 9.6"),
    "conn-close-sp-pipe": ("dusty-bug", "D4 only: connection handling right, value kept as 'close '", "RFC 9110 5.5"),
    "cl-tab-after": ("allowed-difference", "llhttp 9.3.1 rejects HTAB after the CL value (fixed in llhttp 9.4.0, #810); fails closed", "RFC 9110 5.5"),
    "te-chunked-tab": ("allowed-difference", "HTAB after 'chunked' rejected; fails closed (node and nginx reject too)", "RFC 9110 5.5"),
    "te-http10-ka-pipe": ("dusty-bug", "D2: HTTP/1.0+TE keep-alive connection reused for /2", "RFC 9112 6.1"),
    "te-empty-pipe": ("dusty-bug", "D1: empty TE ignored, CL frames the body, /2 parsed", "RFC 9112 6.3"),
    "te-empty-nocl": ("dusty-bug", "D1: empty TE without CL -> zero-length body, '0\\r\\n\\r\\n' then parsed as the next request (400)", "RFC 9112 6.3"),
    "te-spaces-only": ("dusty-bug", "D1: whitespace-only TE ignored like an empty one", "RFC 9112 6.3"),
    "te-empty-cl-first": ("agree", "with CL first llhttp rejects; shows D1 is header-order dependent", "RFC 9112 6.1"),
    "te-foo-chunked": ("dusty-bug", "D5: unknown coding before chunked accepted", "RFC 9112 6.1"),
    "rl-cr-prefix": ("dusty-bug", "D8: bare CRs before the request-line skipped", "RFC 9112 2.2"),
    "rl-star-colon": ("dusty-bug", "D6: asterisk-form must be exactly '*'", "RFC 9112 3.2.4"),
    "connect-te": ("dusty-bug", "D6: CONNECT with origin-form accepted (body not read, connection closed)", "RFC 9112 3.2.3"),
    "rl-http12": ("allowed-difference", "HTTP/1.2 served as 1.1 (RFC 9112 2.3); req.version_minor reports 2", "RFC 9112 2.3"),

    "te-http10": ("dusty-bug", "D2: HTTP/1.0 + TE chunked decoded as chunked; with keep-alive the connection is reused", "RFC 9112 6.1"),
    "te-empty": ("dusty-bug", "D1: empty TE ignored, CL used; references reject", "RFC 9112 6.1, 6.3"),
    "hdr-value-trailing-sp": ("dusty-bug", "D4: trailing SP kept in field value", "RFC 9110 5.5"),
    "hdr-value-trailing-tab": ("dusty-bug", "D4: trailing HTAB kept in field value", "RFC 9110 5.5"),
    "cl-trailing-sp": ("dusty-bug", "D4: framing right, but handler sees 'Content-Length: 3 ' and Request.content_length is null", "RFC 9110 5.5"),
    "te-gzip-chunked": ("dusty-bug", "D5: unsupported transfer coding before chunked accepted, body left coded", "RFC 9112 6.1"),
    "te-identity": ("allowed-difference", "TE identity (no chunked) rejected with 400; 501 would be the SHOULD", "RFC 9112 6.1"),
    "rl-uri-starx": ("dusty-bug", "D6: asterisk-form must be exactly '*'", "RFC 9112 3.2.4"),
    "rl-uri-star-get": ("dusty-bug", "D6: asterisk-form only valid for OPTIONS", "RFC 9112 3.2.4"),
    "rl-uri-fragment": ("dusty-bug", "D6: fragment passed through in req.url", "RFC 9112 3.2"),
    "rl-connect-origin": ("dusty-bug", "D6: CONNECT requires authority-form", "RFC 9112 3.2.3"),
    "ch-ext-bws": ("dusty-bug", "D7: valid BWS in chunk-ext rejected (fails closed, interop only)", "RFC 9112 7.1.1"),
    "ch-ext-no-name": ("allowed-difference", "dusty right: chunk-ext-name is a token, ';' alone is invalid; references are lenient", "RFC 9112 7.1.1"),
    "ch-ext-bad-char": ("allowed-difference", "dusty right: NUL is not allowed in chunk-ext", "RFC 9112 7.1.1"),
    "ch-ext-long": ("allowed-difference", "dusty enforces its 16 KiB chunk-framing budget", "RFC 9112 7.1.1"),
    "ch-size-trailing-sp": ("allowed-difference", "whitespace after chunk-size without an extension is not in the grammar; rejecting is safe", "RFC 9112 7.1"),
    "ch-size-trailing-tab": ("allowed-difference", "as ch-size-trailing-sp", "RFC 9112 7.1"),
    "ch-trailer-cl": ("allowed-difference", "Content-Length in trailer section rejected; RFC lets a recipient discard or reject framing fields in trailers", "RFC 9110 6.5.1"),
    "ch-trailer-bad": ("allowed-difference", "malformed trailer line rejected", "RFC 9112 7.1.2"),
    "clte-both": ("allowed-difference", "CL+TE rejected; RFC allows rejecting (and recommends treating as an error)", "RFC 9112 6.1"),
    "tecl-both": ("allowed-difference", "TE+CL rejected", "RFC 9112 6.1"),
    "cl-dup-same": ("allowed-difference", "identical duplicate CL rejected; RFC allows rejecting", "RFC 9110 8.6"),
    "trophy-transducer-L632": ("allowed-difference", "dusty right: ',chunked' has an empty list element that recipients MUST ignore; references reject (safe)", "RFC 9110 5.6.1"),
    "rl-double-sp": ("allowed-difference", "MAY parse on whitespace boundaries", "RFC 9112 3"),
    "rl-sp-before-version": ("allowed-difference", "MAY parse on whitespace boundaries", "RFC 9112 3"),
    "rl-leading-crlf": ("allowed-difference", "SHOULD ignore at least one empty line before request-line", "RFC 9112 2.2"),
    "rl-leading-crlf-x2": ("allowed-difference", "ignoring more than one empty line is allowed", "RFC 9112 2.2"),
    "rl-leading-lf": ("allowed-difference", "bare LF empty line before request-line skipped (LF-only line endings MAY be accepted)", "RFC 9112 2.2"),
    "rl-absolute": ("allowed-difference", "absolute-form normalised to path and Host replaced by the target authority, as RFC 9112 3.2.2 requires", "RFC 9112 3.2.2"),
    "rl-absolute-ftp": ("allowed-difference", "non-http absolute-form accepted and normalised; server MAY reject", "RFC 9112 3.2.2"),
    "host-absolute-mismatch": ("allowed-difference", "Host replaced by target authority (required by RFC)", "RFC 9112 3.2.2"),
    "rl-absolute-userinfo": ("allowed-difference", "dusty right: userinfo forbidden in http(s) URI", "RFC 9110 4.2.4"),
    "rl-absolute-noauth": ("allowed-difference", "dusty right: http URI needs a host", "RFC 9110 4.2.1"),
    "rl-authority-get": ("allowed-difference", "authority-form for GET rejected (dusty right)", "RFC 9112 3.2.3"),
    "rl-uri-high": ("allowed-difference", "dusty right: raw 0xFF not allowed in request-target", "RFC 9112 3.2"),
    "rl-uri-ctl": ("allowed-difference", "dusty right", "RFC 9112 3.2"),
    "rl-uri-del": ("allowed-difference", "dusty right", "RFC 9112 3.2"),
    "rl-unknown-method": ("allowed-difference", "llhttp method whitelist; 400 instead of the 501 SHOULD", "RFC 9110 9.1"),
    "rl-method-tchar": ("allowed-difference", "llhttp method whitelist", "RFC 9110 9.1"),
    "rl-version-2digit": ("allowed-difference", "dusty right: HTTP-version is DIGIT.DIGIT", "RFC 9112 2.3"),
    "rl-trailing-sp": ("allowed-difference", "dusty right: SP before CRLF not in grammar", "RFC 9112 3"),
    "rl-bare-lf": ("allowed-difference", "bare LF line endings rejected; RFC says MAY accept", "RFC 9112 2.2"),
    "all-bare-lf": ("allowed-difference", "bare LF line endings rejected; RFC says MAY accept", "RFC 9112 2.2"),
    "hdr-end-lf-lf": ("allowed-difference", "bare LF line endings rejected; RFC says MAY accept", "RFC 9112 2.2"),
    "host-empty": ("allowed-difference", "empty Host on origin-form accepted; RFC 9112 3.3 leaves rejecting or applying a default to the server", "RFC 9112 3.3"),
    "host-dup": ("allowed-difference", "dusty right: more than one Host MUST be 400", "RFC 9112 3.2"),
    "host-dup-same": ("allowed-difference", "dusty right: more than one Host MUST be 400", "RFC 9112 3.2"),
    "host-userinfo": ("allowed-difference", "dusty right: invalid Host MUST be 400", "RFC 9112 3.2"),
    "host-space": ("allowed-difference", "dusty right", "RFC 9112 3.2"),
    "host-port-bad": ("allowed-difference", "dusty right", "RFC 9112 3.2"),
    "host-slash": ("allowed-difference", "dusty right", "RFC 9112 3.2"),
    "many-headers-40": ("allowed-difference", "default max_header_count (32) exceeded -> 431", "RFC 9110 5.4"),
    "long-uri-20k": ("allowed-difference", "16 KiB head buffer -> 414", "RFC 9112 3"),
    "long-header-20k": ("allowed-difference", "16 KiB head buffer -> 431", "RFC 9110 5.4"),
    "gzip-body": ("allowed-difference", "dusty decodes Content-Encoding by default (documented feature) and drops Content-Encoding/Content-Length from the header list", "RFC 9110 8.4"),
    "ce-unknown": ("allowed-difference", "415 for a content coding dusty cannot undo (documented)", "RFC 9110 15.5.16"),
    "expect-unknown": ("allowed-difference", "417 for unknown expectation", "RFC 9110 10.1.1"),
    "hdr-name-underscore": ("allowed-difference", "references drop or translate underscore names; dusty keeps them", "RFC 9110 5.1"),
    "pipe-crlf-between": ("allowed-difference", "empty line between pipelined requests ignored", "RFC 9112 2.2"),
    "pipe-connection-list-close": ("reference-bug", "gunicorn ignores 'close' inside a Connection list; dusty right", "RFC 9112 9.6"),
}

def wookiee(key, per):
    d = per.get("dusty") or ""
    if "regular_09" in key:
        return {"verdict": "allowed-difference", "note": "dusty answers HTTP/0.9 with 505; Wookiee only lists 400/0.9/reject as OK", "rfc": "RFC 9112 2.3"}
    if "3020_multiple_cr" in key:
        return {"verdict": "dusty-bug", "note": "D8: bare CRs before the request line skipped (nginx same)", "rfc": "RFC 9112 2.2"}
    if "[FAIL]" in d:
        return {"verdict": "UNTRIAGED", "note": d}
    others = [v for k, v in per.items() if k != "dusty" and v]
    if any("[FAIL]" in v for v in others):
        return {"verdict": "reference-bug", "note": "dusty passes; " + "; ".join(f"{k}: {v}" for k, v in per.items() if k != 'dusty' and v and '[FAIL]' in v)}
    return {"verdict": "agree", "note": "dusty passes: " + d.replace("...", "").strip()}


def fuzz(c):
    """Classify a fuzz finding by the known behaviour it exercises."""
    import base64
    raw = b"".join(base64.b64decode(x) for x in c["stream_b64"])
    if c["id"] in FUZZ_MANUAL:
        v, n = FUZZ_MANUAL[c["id"]]
        return {"verdict": v, "note": n}
    d = c["servers"].get("dusty", [])
    kinds = [r["type"] for r in d]
    if not d or d[0]["type"] == "response":
        return {"verdict": "allowed-difference", "note": "dusty rejects (" + (d[0]["code"] if d else "no response") + ") where most references accept or differ; fails closed"}
    checks = [
        (re.search(rb"HTTP/1\.0\r\n(?:(?!\r\n\r\n)[\s\S])*Transfer-Encoding", raw, re.I), "dusty-bug", "D2: HTTP/1.0 with Transfer-Encoding"),
        (re.search(rb"Transfer-Encoding:[ \t]*\r\n", raw, re.I), "dusty-bug", "D1: empty Transfer-Encoding"),
        (re.search(rb"Connection: close\t", raw), "dusty-bug", "D3: 'close' followed by HTAB"),
        (re.match(rb"\r+[^\n]", raw) or re.search(rb"\n\r[A-Z]", raw), "dusty-bug", "D8: bare CR before the request-line"),
        (re.search(rb"^[A-Z-]+ \*\S", raw, re.M) or re.search(rb"^(?!OPTIONS)[A-Z-]+ \* ", raw, re.M), "dusty-bug", "D6: asterisk-form leniency"),
        (re.search(rb"^CONNECT /", raw, re.M), "dusty-bug", "D6: CONNECT with origin-form"),
        (re.search(rb"^[A-Z-]+ [^ \r\n]*#", raw, re.M), "dusty-bug", "D6: fragment in request-target"),
        (re.search(rb"^[A-Z-]+ [^ \r\n]*[\"<>]", raw, re.M), "dusty-bug", "D6: '\"', '<' or '>' accepted in request-target"),
        (re.search(rb"[ \t]\r\n", raw.split(b"\r\n\r\n")[0] + b"\r\n"), "dusty-bug", "D4: trailing whitespace kept in a field value"),
        (re.search(rb"Transfer-Encoding: [^\r\n]*,[^\r\n]*chunked", raw, re.I), "dusty-bug", "D5: coding before chunked"),
        (re.search(rb"^[A-Z-]+ [a-z]+://", raw, re.M), "allowed-difference", "absolute-form normalised to path, Host replaced (RFC 9112 3.2.2)"),
        (re.search(rb"^[A-Z-]+  |^[A-Z-]+ \S+  HTTP", raw, re.M), "allowed-difference", "extra SP in request-line; RFC 9112 3 lets recipients split on whitespace"),
        (re.match(rb"(\r?\n)+[A-Z]", raw), "allowed-difference", "empty line(s) before the request-line ignored (RFC 9112 2.2)"),
        (re.search(rb"Host:[ \t]*\r\n", raw), "allowed-difference", "empty Host accepted (RFC 9112 3.3 leaves it to the server)"),
        (re.search(rb"HTTP/1\.[2-9]\r\n", raw), "allowed-difference", "HTTP/1.x>1 served as 1.1 (RFC 9112 2.3)"),
    ]
    for hit, verdict, note in checks:
        if hit:
            return {"verdict": verdict, "note": note}
    if "response" in kinds:
        return {"verdict": "allowed-difference", "note": "dusty serves the valid request(s) and answers the trailing garbage with 400 immediately; references wait for more bytes"}
    return {"verdict": "UNTRIAGED", "note": "dusty accepts; see per-server views"}


FUZZ_MANUAL = {
    "fuzz-s2-i102": ("allowed-difference", "'X_Y' is a valid token and 0xD5 is obs-text (RFC 9110 5.5); dusty is right to accept, references that drop/reject underscore names or obs-text are being strict"),
}
