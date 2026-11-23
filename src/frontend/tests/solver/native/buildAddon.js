#!/usr/bin/env node
// Portable native test harness addon build: locate the headers belonging to
// the running Node installation, rather than assuming Linux /usr/include/node.
// This is independent of any circuit, component, or layout fixture.
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const candidates = [];
function add(base) {
  if (!base) return;
  candidates.push(base);
}
add(process.env.NODE_INCLUDE_DIR);
for (const prefix of [process.env.npm_config_nodedir, process.config.variables.nodedir]) {
  if (prefix) {
    add(path.join(prefix, "include", "node"));
    add(prefix);
  }
}
for (const executable of [process.execPath, fs.realpathSync(process.execPath)]) {
  add(path.resolve(path.dirname(executable), "..", "include", "node"));
}
add("/usr/include/node");
add("/usr/local/include/node");
add("/opt/homebrew/include/node");

const include = [...new Set(candidates)]
  .find((dir) => fs.existsSync(path.join(dir, "node_api.h")));
if (!include) {
  console.error("❌ Native addon: cannot locate node_api.h for " + process.execPath);
  console.error("Checked:\n" + [...new Set(candidates)].map((p) => "  " + p).join("\n"));
  console.error("Install your Node distribution's development headers or set NODE_INCLUDE_DIR.");
  process.exit(1);
}

const output = path.join(__dirname, "build", "v5native.node");
fs.mkdirSync(path.dirname(output), { recursive: true });
const platform = os.platform();
if (platform !== "darwin" && platform !== "linux") {
  console.error("❌ Native addon build is supported on macOS and Linux (got " + platform + ")");
  process.exit(1);
}
const args = ["-O2", "-fPIC",
  ...(platform === "darwin"
    ? ["-bundle", "-undefined", "dynamic_lookup"]
    : ["-shared"]),
  "-I" + include, "-o", output,
  path.join(__dirname, "addon.c"),
  ...(platform === "linux" ? ["-ldl"] : []),
];
console.log("🛠️ Native addon: " + platform + " | Node headers: " + include);
const result = spawnSync(process.env.CC || "clang", args, { stdio: "inherit" });
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
