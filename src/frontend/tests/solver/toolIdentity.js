"use strict";

/**
 * Startup identity for the headless solver CLI.
 * Diagnostic only: never writes stdout or changes solver inputs/RNG.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

function findRepository(from) {
  for (let dir = path.resolve(from); ; dir = path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, "VERSION")) && fs.existsSync(path.join(dir, "src", "frontend"))) return dir;
    if (path.dirname(dir) === dir) return null;
  }
}
function repositorySha(root) {
  if (!root) return "unavailable";
  try {
    const dot = path.join(root, ".git");
    let gitdir = dot;
    if (fs.statSync(dot).isFile()) {
      const file = fs.readFileSync(dot, "utf8").trim();
      if (!file.startsWith("gitdir: ")) return "unavailable";
      gitdir = path.resolve(root, file.slice(8));
    }
    const head = fs.readFileSync(path.join(gitdir, "HEAD"), "utf8").trim();
    if (/^[a-f0-9]{40}$/i.test(head)) return head.slice(0, 12);
    if (!head.startsWith("ref: ")) return "unavailable";
    const ref = head.slice(5);
    const loose = path.join(gitdir, ref);
    if (fs.existsSync(loose)) return fs.readFileSync(loose, "utf8").trim().slice(0, 12);
    const packed = fs.readFileSync(path.join(gitdir, "packed-refs"), "utf8");
    const line = packed.split(/\r?\n/).find(s => s.endsWith(" " + ref));
    return line ? line.split(" ")[0].slice(0, 12) : "unavailable";
  } catch { return "unavailable"; }
}
function solverIdentity(entryFile) {
  const root = findRepository(path.dirname(entryFile));
  const release = root ? fs.readFileSync(path.join(root, "VERSION"), "utf8").trim() : "unavailable";
  const program = crypto.createHash("sha256").update(fs.readFileSync(entryFile)).digest("hex").slice(0, 12);
  return { release, git: repositorySha(root), program };
}
function printSolverSplash(entryFile) {
  const identity = solverIdentity(entryFile);
  // stderr is mandatory: many workflows parse exactly one JSON object on stdout.
  process.stderr.write(
    "\n" +
    "┏━━━━━━━━━━━━ STRIPBOARD · SOLVER ━━━━━━━━━━━━┓\n" +
    "┃ Release " + identity.release + "  |  Git " + identity.git + "\n" +
    "┃ Solver CLI sha256 " + identity.program + "\n" +
    "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n" +
    "[TOOL-REVISION] tool=SOLVER release=" + identity.release +
    " git=" + identity.git + " program_sha256=" + identity.program + "\n"
  );
  return identity;
}
module.exports = { printSolverSplash, solverIdentity };
