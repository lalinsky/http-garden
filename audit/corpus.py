"""Test corpus: Garden TROPHIES.md payloads plus hand-written cases.
Each case: (id, category, rfc, [stream pieces as escaped str])."""
import re

H = "Host: a\r\n"

CURATED = [
    # request line
    ("rl-basic", "request line", "RFC 9112 3", ["GET / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-http10-nohost", "request line", "RFC 9112 3.2", ["GET / HTTP/1.0\r\n\r\n"]),
    ("rl-http12", "request line", "RFC 9112 2.3", ["GET / HTTP/1.2\r\nHost: a\r\n\r\n"]),
    ("rl-http20", "request line", "RFC 9112 2.3", ["GET / HTTP/2.0\r\nHost: a\r\n\r\n"]),
    ("rl-http09", "request line", "RFC 9112 2.3", ["GET /\r\n\r\n"]),
    ("rl-lower-proto", "request line", "RFC 9112 2.3", ["GET / http/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-version-2digit", "request line", "RFC 9112 2.3", ["GET / HTTP/1.10\r\nHost: a\r\n\r\n"]),
    ("rl-version-leading0", "request line", "RFC 9112 2.3", ["GET / HTTP/01.1\r\nHost: a\r\n\r\n"]),
    ("rl-double-sp", "request line", "RFC 9112 3", ["GET  / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-sp-before-version", "request line", "RFC 9112 3", ["GET /  HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-tab-sep", "request line", "RFC 9112 3", ["GET\t/\tHTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-trailing-sp", "request line", "RFC 9112 3", ["GET / HTTP/1.1 \r\nHost: a\r\n\r\n"]),
    ("rl-leading-crlf", "request line", "RFC 9112 2.2", ["\r\nGET / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-leading-crlf-x2", "request line", "RFC 9112 2.2", ["\r\n\r\nGET / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-leading-lf", "request line", "RFC 9112 2.2", ["\nGET / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-lower-method", "request line", "RFC 9110 9.1", ["get / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-unknown-method", "request line", "RFC 9110 9.1", ["SLUDGE / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-method-tchar", "request line", "RFC 9110 9.1", ["GET! / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-method-digit", "request line", "RFC 9110 9.1", ["0 / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-fragment", "request line", "RFC 9112 3.2", ["GET /a#frag HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-ctl", "request line", "RFC 9112 3.2", ["GET /a\x01b HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-del", "request line", "RFC 9112 3.2", ["GET /a\x7fb HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-high", "request line", "RFC 9112 3.2", ["GET /a\xffb HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-backslash", "request line", "RFC 9112 3.2", ["GET /a\\b HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-brace", "request line", "RFC 9112 3.2", ["GET /a{b}|c^ HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-quote", "request line", "RFC 9112 3.2", ["GET /a\"b<c> HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-noslash", "request line", "RFC 9112 3.2", ["GET a HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-star-get", "request line", "RFC 9112 3.2.4", ["GET * HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-star-options", "request line", "RFC 9112 3.2.4", ["OPTIONS * HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-uri-starx", "request line", "RFC 9112 3.2.4", ["OPTIONS *x HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-absolute", "request line", "RFC 9112 3.2.2", ["GET http://b/c?d HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-absolute-userinfo", "request line", "RFC 9110 4.2.4", ["GET http://u@b/ HTTP/1.1\r\nHost: b\r\n\r\n"]),
    ("rl-absolute-noauth", "request line", "RFC 9112 3.2.2", ["GET http:/// HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-absolute-ftp", "request line", "RFC 9112 3.2.2", ["GET ftp://b/ HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-authority-get", "request line", "RFC 9112 3.2.3", ["GET a:80 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-connect-origin", "request line", "RFC 9112 3.2.3", ["CONNECT / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-bare-cr", "line endings", "RFC 9112 2.2", ["GET / HTTP/1.1\rHost: a\r\n\r\n"]),
    ("rl-bare-lf", "line endings", "RFC 9112 2.2", ["GET / HTTP/1.1\nHost: a\r\n\r\n"]),
    ("all-bare-lf", "line endings", "RFC 9112 2.2", ["GET / HTTP/1.1\nHost: a\n\n"]),
    ("hdr-end-lf-lf", "line endings", "RFC 9112 2.2", ["GET / HTTP/1.1\r\nHost: a\n\n"]),
    ("hdr-bare-cr-end", "line endings", "RFC 9112 2.2", ["GET / HTTP/1.1\r\nHost: a\r\r\n\r\n"]),
    ("hdr-crcr", "line endings", "RFC 9112 2.2", ["GET / HTTP/1.1\r\nHost: a\r\nX: y\r\r\n\r\n"]),
    # header syntax
    ("hdr-space-before-colon", "header syntax", "RFC 9112 5.1", ["GET / HTTP/1.1\r\nHost: a\r\nX : y\r\n\r\n"]),
    ("hdr-tab-before-colon", "header syntax", "RFC 9112 5.1", ["GET / HTTP/1.1\r\nHost: a\r\nX\t: y\r\n\r\n"]),
    ("hdr-empty-name", "header syntax", "RFC 9110 5.1", ["GET / HTTP/1.1\r\nHost: a\r\n: y\r\n\r\n"]),
    ("hdr-no-colon", "header syntax", "RFC 9112 5", ["GET / HTTP/1.1\r\nHost: a\r\nXy\r\n\r\n"]),
    ("hdr-name-sp", "header syntax", "RFC 9110 5.1", ["GET / HTTP/1.1\r\nHost: a\r\nX Y: z\r\n\r\n"]),
    ("hdr-name-at", "header syntax", "RFC 9110 5.1", ["GET / HTTP/1.1\r\nHost: a\r\nX@Y: z\r\n\r\n"]),
    ("hdr-name-high", "header syntax", "RFC 9110 5.1", ["GET / HTTP/1.1\r\nHost: a\r\nX\xffY: z\r\n\r\n"]),
    ("hdr-name-underscore", "header syntax", "RFC 9110 5.1", ["GET / HTTP/1.1\r\nHost: a\r\nX_Y: z\r\n\r\n"]),
    ("hdr-value-trailing-sp", "whitespace", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX: y \r\n\r\n"]),
    ("hdr-value-trailing-tab", "whitespace", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX: y\t\r\n\r\n"]),
    ("hdr-value-leading-tab", "whitespace", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX:\ty\r\n\r\n"]),
    ("hdr-value-empty", "whitespace", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX:\r\n\r\n"]),
    ("hdr-value-only-sp", "whitespace", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX:   \r\n\r\n"]),
    ("hdr-value-inner-sp", "whitespace", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX: a  b\r\n\r\n"]),
    ("hdr-value-vt", "NUL/control", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX: a\x0bb\r\n\r\n"]),
    ("hdr-value-ff", "NUL/control", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX: a\x0cb\r\n\r\n"]),
    ("hdr-value-nul", "NUL/control", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX: a\x00b\r\n\r\n"]),
    ("hdr-value-ctl01", "NUL/control", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX: a\x01b\r\n\r\n"]),
    ("hdr-value-del", "NUL/control", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX: a\x7fb\r\n\r\n"]),
    ("hdr-value-obstext", "NUL/control", "RFC 9110 5.5", ["GET / HTTP/1.1\r\nHost: a\r\nX: a\x80\xffb\r\n\r\n"]),
    ("hdr-value-bare-cr", "line endings", "RFC 9112 2.2", ["GET / HTTP/1.1\r\nHost: a\r\nX: a\rb\r\n\r\n"]),
    ("obs-fold-sp", "obs-fold", "RFC 9112 5.2", ["GET / HTTP/1.1\r\nHost: a\r\nX: a\r\n b\r\n\r\n"]),
    ("obs-fold-tab", "obs-fold", "RFC 9112 5.2", ["GET / HTTP/1.1\r\nHost: a\r\nX: a\r\n\tb\r\n\r\n"]),
    ("obs-fold-first-line", "obs-fold", "RFC 9112 5.2", ["GET / HTTP/1.1\r\n X: a\r\nHost: a\r\n\r\n"]),
    ("obs-fold-cl", "obs-fold", "RFC 9112 5.2", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length:\r\n 3\r\n\r\nabc"]),
    ("obs-fold-te", "obs-fold", "RFC 9112 5.2", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding:\r\n chunked\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    # Host
    ("host-missing-11", "Host", "RFC 9112 3.2", ["GET / HTTP/1.1\r\n\r\n"]),
    ("host-dup", "Host", "RFC 9112 3.2", ["GET / HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n"]),
    ("host-dup-same", "Host", "RFC 9112 3.2", ["GET / HTTP/1.1\r\nHost: a\r\nHost: a\r\n\r\n"]),
    ("host-empty", "Host", "RFC 9112 3.2", ["GET / HTTP/1.1\r\nHost:\r\n\r\n"]),
    ("host-comma", "Host", "RFC 9112 3.2", ["GET / HTTP/1.1\r\nHost: a,b\r\n\r\n"]),
    ("host-userinfo", "Host", "RFC 9110 7.2", ["GET / HTTP/1.1\r\nHost: u@a\r\n\r\n"]),
    ("host-space", "Host", "RFC 9110 7.2", ["GET / HTTP/1.1\r\nHost: a b\r\n\r\n"]),
    ("host-port-bad", "Host", "RFC 9110 7.2", ["GET / HTTP/1.1\r\nHost: a:b\r\n\r\n"]),
    ("host-ipv6", "Host", "RFC 9110 7.2", ["GET / HTTP/1.1\r\nHost: [::1]:80\r\n\r\n"]),
    ("host-slash", "Host", "RFC 9110 7.2", ["GET / HTTP/1.1\r\nHost: a/b\r\n\r\n"]),
    ("host-nul", "Host", "RFC 9110 7.2", ["GET / HTTP/1.1\r\nHost: a\x00b\r\n\r\n"]),
    ("host-absolute-mismatch", "Host", "RFC 9112 3.2.2", ["GET http://b/ HTTP/1.1\r\nHost: a\r\n\r\n"]),
    # framing CL
    ("cl-basic", "framing/CL", "RFC 9112 6.2", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 3\r\n\r\nabc"]),
    ("cl-dup-same", "framing/CL", "RFC 9112 6.3", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 3\r\nContent-Length: 3\r\n\r\nabc"]),
    ("cl-dup-diff", "framing/CL", "RFC 9112 6.3", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 3\r\nContent-Length: 4\r\n\r\nabcd"]),
    ("cl-list-same", "framing/CL", "RFC 9110 8.6", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 3, 3\r\n\r\nabc"]),
    ("cl-list-diff", "framing/CL", "RFC 9110 8.6", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 3, 4\r\n\r\nabcd"]),
    ("cl-plus", "framing/CL", "RFC 9110 8.6", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: +3\r\n\r\nabc"]),
    ("cl-neg", "framing/CL", "RFC 9110 8.6", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: -3\r\n\r\nabc"]),
    ("cl-hex", "framing/CL", "RFC 9110 8.6", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 0x3\r\n\r\nabc"]),
    ("cl-leading-zero", "framing/CL", "RFC 9110 8.6", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 003\r\n\r\nabc"]),
    ("cl-trailing-sp", "framing/CL", "RFC 9110 5.5", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 3 \r\n\r\nabc"]),
    ("cl-inner-sp", "framing/CL", "RFC 9110 8.6", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 1 2\r\n\r\nabcdefghijkl"]),
    ("cl-empty", "framing/CL", "RFC 9110 8.6", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length:\r\n\r\n"]),
    ("cl-overflow", "framing/CL", "RFC 9110 8.6", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 18446744073709551617\r\n\r\nabc"]),
    ("cl-get-body", "framing/CL", "RFC 9110 9.3.1", ["GET / HTTP/1.1\r\nHost: a\r\nContent-Length: 3\r\n\r\nabc"]),
    ("cl-short-then-close", "framing/CL", "RFC 9112 6.3", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 10\r\n\r\nabc"]),
    ("post-no-length", "framing/CL", "RFC 9112 6.3", ["POST / HTTP/1.1\r\nHost: a\r\n\r\nabc"]),
    ("cl-name-case", "framing/CL", "RFC 9110 5.1", ["POST / HTTP/1.1\r\nHost: a\r\ncOnTeNt-LeNgTh: 3\r\n\r\nabc"]),
    # framing CL-TE
    ("clte-both", "framing/CL-TE", "RFC 9112 6.1", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 5\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n"]),
    ("tecl-both", "framing/CL-TE", "RFC 9112 6.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\nContent-Length: 5\r\n\r\n0\r\n\r\n"]),
    ("te-http10", "framing/CL-TE", "RFC 9112 6.1", ["POST / HTTP/1.0\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-identity", "framing/TE", "RFC 9112 6.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: identity\r\nContent-Length: 3\r\n\r\nabc"]),
    ("te-gzip-chunked", "framing/TE", "RFC 9112 6.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: gzip, chunked\r\n\r\n0\r\n\r\n"]),
    ("te-chunked-gzip", "framing/TE", "RFC 9112 6.3", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked, gzip\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-chunked-x2-list", "framing/TE", "RFC 9112 7", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked, chunked\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-chunked-x2-hdr", "framing/TE", "RFC 9112 7", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-unknown", "framing/TE", "RFC 9112 6.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: foo\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-case", "framing/TE", "RFC 9112 7", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: ChUnKeD\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-chunked-trailing-sp", "framing/TE", "RFC 9110 5.5", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked \r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-chunked-comma", "framing/TE", "RFC 9110 5.6.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked,\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-xchunked", "framing/TE", "RFC 9112 7", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: xchunked\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-chunked-param", "framing/TE", "RFC 9112 7", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked;a=b\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-vtab", "framing/TE", "RFC 9110 5.5", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: \x0bchunked\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-empty", "framing/TE", "RFC 9112 6.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding:\r\nContent-Length: 3\r\n\r\nabc"]),
    ("te-chunked-then-identity", "framing/TE", "RFC 9112 6.3", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\nTransfer-Encoding: identity\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    # chunked
    ("ch-basic", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n0\r\n\r\n"]),
    ("ch-ext", "chunked", "RFC 9112 7.1.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3;a=b\r\nabc\r\n0\r\n\r\n"]),
    ("ch-ext-quoted", "chunked", "RFC 9112 7.1.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3;a=\"b;c\"\r\nabc\r\n0\r\n\r\n"]),
    ("ch-ext-bws", "chunked", "RFC 9112 7.1.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3 ; a = b\r\nabc\r\n0\r\n\r\n"]),
    ("ch-ext-bad-char", "chunked", "RFC 9112 7.1.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3;a\x00\r\nabc\r\n0\r\n\r\n"]),
    ("ch-ext-bare-cr", "chunked", "RFC 9112 7.1.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3;a\rb\r\nabc\r\n0\r\n\r\n"]),
    ("ch-ext-no-name", "chunked", "RFC 9112 7.1.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3;\r\nabc\r\n0\r\n\r\n"]),
    ("ch-size-upper", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\nA\r\n0123456789\r\n0\r\n\r\n"]),
    ("ch-size-0x", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n0x3\r\nabc\r\n0\r\n\r\n"]),
    ("ch-size-leading-sp", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n 3\r\nabc\r\n0\r\n\r\n"]),
    ("ch-size-trailing-sp", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3 \r\nabc\r\n0\r\n\r\n"]),
    ("ch-size-trailing-tab", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3\t\r\nabc\r\n0\r\n\r\n"]),
    ("ch-size-leading-zeros", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n0003\r\nabc\r\n0\r\n\r\n"]),
    ("ch-size-overflow", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n10000000000000003\r\nabc\r\n0\r\n\r\n"]),
    ("ch-size-neg", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n-3\r\nabc\r\n0\r\n\r\n"]),
    ("ch-size-lf", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3\nabc\r\n0\r\n\r\n"]),
    ("ch-data-lf", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\n0\r\n\r\n"]),
    ("ch-data-nocrlf", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabcX\r\n0\r\n\r\n"]),
    ("ch-data-too-long", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabcd\r\n0\r\n\r\n"]),
    ("ch-last-lf", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n0\n\r\n"]),
    ("ch-final-lf", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\n"]),
    ("ch-trailer", "chunked", "RFC 9112 7.1.2", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nZ\r\n0\r\nX: y\r\n\r\n"]),
    ("ch-trailer-cl", "chunked", "RFC 9110 6.5.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nZ\r\n0\r\nContent-Length: 5\r\n\r\n"]),
    ("ch-trailer-bad", "chunked", "RFC 9112 7.1.2", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nZ\r\n0\r\nX y\r\n\r\n"]),
    ("ch-trailer-bare-lf", "chunked", "RFC 9112 7.1.2", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nZ\r\n0\r\nX: y\n\r\n"]),
    ("ch-missing-last", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nZ\r\n"]),
    ("ch-empty-size", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("ch-many-small", "chunked", "RFC 9112 7.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n" + "1\r\nZ\r\n" * 200 + "0\r\n\r\n"]),
    ("ch-ext-long", "chunked", "RFC 9112 7.1.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n1;" + "a" * 20000 + "\r\nZ\r\n0\r\n\r\n"]),
    # pipelining / persistence
    ("pipe-2get", "pipelining", "RFC 9112 9.3.2", ["GET /1 HTTP/1.1\r\nHost: a\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("pipe-split", "pipelining", "RFC 9112 9.3.2", ["GET /1 HTTP/1.1\r\nHo", "st: a\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("pipe-cl-then-get", "pipelining", "RFC 9112 6.3", ["POST /1 HTTP/1.1\r\nHost: a\r\nContent-Length: 3\r\n\r\nabcGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("pipe-chunked-then-get", "pipelining", "RFC 9112 6.3", ["POST /1 HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n0\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("pipe-close-then-get", "pipelining", "RFC 9112 9.6", ["GET /1 HTTP/1.1\r\nHost: a\r\nConnection: close\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("pipe-http10-then-get", "pipelining", "RFC 9112 9.3", ["GET /1 HTTP/1.0\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("pipe-http10-ka", "pipelining", "RFC 9112 9.3", ["GET /1 HTTP/1.0\r\nConnection: keep-alive\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("pipe-crlf-between", "pipelining", "RFC 9112 2.2", ["GET /1 HTTP/1.1\r\nHost: a\r\n\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("pipe-bad-after-good", "pipelining", "RFC 9112 2.2", ["GET /1 HTTP/1.1\r\nHost: a\r\n\r\nGARBAGE\r\n\r\n"]),
    ("pipe-connection-close-case", "pipelining", "RFC 9112 9.6", ["GET /1 HTTP/1.1\r\nHost: a\r\nConnection: CLOSE\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("pipe-connection-list-close", "pipelining", "RFC 9112 9.6", ["GET /1 HTTP/1.1\r\nHost: a\r\nConnection: foo, close\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("expect-100", "misc", "RFC 9110 10.1.1", ["POST / HTTP/1.1\r\nHost: a\r\nExpect: 100-continue\r\nContent-Length: 3\r\n\r\n", "abc"]),
    ("expect-unknown", "misc", "RFC 9110 10.1.1", ["POST / HTTP/1.1\r\nHost: a\r\nExpect: foo\r\nContent-Length: 3\r\n\r\nabc"]),
    ("upgrade-h2c", "misc", "RFC 9110 7.8", ["GET / HTTP/1.1\r\nHost: a\r\nConnection: Upgrade\r\nUpgrade: foo\r\n\r\n"]),
    ("dup-hdr-order", "header syntax", "RFC 9110 5.3", ["GET / HTTP/1.1\r\nHost: a\r\nX: 1\r\nY: 2\r\nX: 3\r\n\r\n"]),
    ("many-headers-40", "limits", "RFC 9110 5.4", ["GET / HTTP/1.1\r\nHost: a\r\n" + "".join("X%d: y\r\n" % i for i in range(40)) + "\r\n"]),
    ("long-uri-20k", "limits", "RFC 9112 3", ["GET /" + "a" * 20000 + " HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("long-header-20k", "limits", "RFC 9110 5.4", ["GET / HTTP/1.1\r\nHost: a\r\nX: " + "a" * 20000 + "\r\n\r\n"]),
    ("gzip-body", "misc", "RFC 9110 8.4", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Encoding: gzip\r\nContent-Length: 25\r\n\r\n\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\xcb\x48\xcd\xc9\xc9\x07\x00\x86\xa6\x10\x36\x05\x00\x00\x00"]),
    ("ce-unknown", "misc", "RFC 9110 8.4", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Encoding: foo\r\nContent-Length: 3\r\n\r\nabc"]),
    ("conn-close-tab-pipe", "pipelining", "RFC 9112 9.6", ["GET /1 HTTP/1.1\r\nHost: a\r\nConnection: close\t\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("conn-close-sp-pipe", "pipelining", "RFC 9112 9.6", ["GET /1 HTTP/1.1\r\nHost: a\r\nConnection: close \r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("cl-tab-after", "framing/CL", "RFC 9110 5.5", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 3\t\r\n\r\nabc"]),
    ("cl-tab-before", "framing/CL", "RFC 9110 5.5", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length:\t3\r\n\r\nabc"]),
    ("te-chunked-tab", "framing/TE", "RFC 9110 5.5", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\t\r\n\r\n1\r\nZ\r\n0\r\n\r\n"]),
    ("te-http10-ka-pipe", "framing/CL-TE", "RFC 9112 6.1", ["POST /1 HTTP/1.0\r\nHost: a\r\nConnection: keep-alive\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nZ\r\n0\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("te-empty-pipe", "framing/CL-TE", "RFC 9112 6.3", ["POST /1 HTTP/1.1\r\nHost: a\r\nTransfer-Encoding:\r\nContent-Length: 5\r\n\r\n0\r\n\r\nGET /2 HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("te-empty-cl-first", "framing/CL-TE", "RFC 9112 6.3", ["POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 5\r\nTransfer-Encoding:\r\n\r\n0\r\n\r\n"]),
    ("te-empty-nocl", "framing/CL-TE", "RFC 9112 6.3", ["POST /1 HTTP/1.1\r\nHost: a\r\nTransfer-Encoding:\r\n\r\n0\r\n\r\n"]),
    ("te-spaces-only", "framing/CL-TE", "RFC 9112 6.3", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding:   \r\nContent-Length: 3\r\n\r\nabc"]),
    ("te-foo-chunked", "framing/TE", "RFC 9112 6.1", ["POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: foo, chunked\r\n\r\n3\r\nabc\r\n0\r\n\r\n"]),
    ("rl-cr-prefix", "line endings", "RFC 9112 2.2", ["\r\r\rGET / HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("rl-star-colon", "request line", "RFC 9112 3.2.4", ["OPTIONS *:x HTTP/1.1\r\nHost: a\r\n\r\n"]),
    ("connect-te", "request line", "RFC 9112 3.2.3", ["CONNECT / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n"]),

]


def trophies(path):
    out = []
    section = "server"
    for n, line in enumerate(open(path, encoding="latin1"), 1):
        if line.startswith("## Transducer"):
            section = "transducer"
        elif line.startswith("## Bonus"):
            section = "bonus"
        if "- Payload:" not in line:
            continue
        pieces = re.findall(r"`([^`]*)`", line)
        if not pieces or any(p.startswith("PRI ") for p in pieces):
            continue
        # The payloads are written as Python escapes.
        out.append((f"trophy-{section}-L{n}", f"garden-trophy/{section}", "", pieces))
    return out


def with_host(cases):
    """Variant of each HTTP/1.1 payload lacking Host, with Host added, since
    dusty (rightly) rejects a Host-less 1.1 request and would hide the rest."""
    res = []
    for cid, cat, rfc, pieces in cases:
        if "HTTP/1.1" in pieces[0] and not re.search(r"(?i)host:", "".join(pieces)):
            p0 = re.sub(r"HTTP/1\.1\\r\\n", r"HTTP/1.1\\r\\nHost: a\\r\\n", pieces[0])
            if p0 != pieces[0]:
                res.append((cid + "+host", cat, rfc, [p0] + pieces[1:]))
    return res
