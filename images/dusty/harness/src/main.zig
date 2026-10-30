const std = @import("std");
const http = @import("dusty");

const Echo = struct {
    pub fn notFound(_: *Echo, req: *http.Request, res: *http.Response) !void {
        const body = try req.body() orelse "";
        const a = res.arena;
        var out: std.ArrayList(u8) = .empty;
        try out.appendSlice(a, "{\"headers\":[");
        var it = req.headers.iterator();
        var first = true;
        while (it.next()) |h| {
            if (!first) try out.append(a, ',');
            first = false;
            try out.appendSlice(a, "[\"");
            try b64(a, &out, h.key);
            try out.appendSlice(a, "\",\"");
            try b64(a, &out, h.value);
            try out.appendSlice(a, "\"]");
        }
        try out.appendSlice(a, "],\"body\":\"");
        try b64(a, &out, body);
        try out.appendSlice(a, "\",\"method\":\"");
        try b64(a, &out, req.method.name());
        try out.appendSlice(a, "\",\"version\":\"");
        const ver = try std.fmt.allocPrint(a, "{d}.{d}", .{ req.version_major, req.version_minor });
        try b64(a, &out, ver);
        try out.appendSlice(a, "\",\"uri\":\"");
        try b64(a, &out, req.url);
        try out.appendSlice(a, "\"}");
        res.status = .ok;
        res.body = out.items;
    }
};

fn b64(a: std.mem.Allocator, out: *std.ArrayList(u8), s: []const u8) !void {
    const enc = std.base64.standard.Encoder;
    const dst = try out.addManyAsSlice(a, enc.calcSize(s.len));
    _ = enc.encode(dst, s);
}

pub fn main(init: std.process.Init) !void {
    const port: u16 = 80;
    const addr: http.Address = .{ .ip = try std.Io.net.IpAddress.parse("0.0.0.0", port) };
    var ctx: Echo = .{};
    var server = http.Server(Echo).init(init.gpa, init.io, .{
        .listeners = &.{.{ .address = addr }},
        .request = .{ .max_body_size = 64 * 1024 * 1024 },
    }, &ctx);
    defer server.deinit();
    try server.run();
}
