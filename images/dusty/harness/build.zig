const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});
    const dusty_dep = b.dependency("dusty", .{ .target = target, .optimize = optimize, .use_tls = false });
    const exe = b.addExecutable(.{
        .name = "dusty-garden",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    exe.root_module.addImport("dusty", dusty_dep.module("dusty"));
    b.installArtifact(exe);
}
