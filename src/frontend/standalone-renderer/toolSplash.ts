/**
 * Runtime revision banner for the compiled headless SVG renderers.
 * Only logs to stderr. No SVG, output path, rendering data or solver behavior changes.
 */
import * as fs from "fs";
import * as path from "path";
import { createHash } from "crypto";

type RendererTool = "RENDER" | "SCHEMATIC";

function repositoryRoot(start: string): string | null {
  for (let dir = path.resolve(start); ; dir = path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, "VERSION")) &&
        fs.existsSync(path.join(dir, "src", "frontend"))) return dir;
    if (path.dirname(dir) === dir) return null;
  }
}
function gitSha(root: string | null): string {
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

// The compiled dist tree is the executable renderer, not the current TS source.
// Hashing it prevents a stale dist build from masquerading as a new revision.
// Both tools share library files and see the same dist build fingerprint.
function buildSha(dist: string): string {
  const digest = createHash("sha256");
  function walk(dir: string): void {
    const files = fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name));
    for (const file of files) {
      const absolute = path.join(dir, file.name);
      if (file.isDirectory()) walk(absolute);
      else if (file.isFile() && file.name.endsWith(".js")) {
        digest.update(path.relative(dist, absolute).split(path.sep).join("/"));
        digest.update("\0");
        digest.update(fs.readFileSync(absolute));
        digest.update("\0");
      }
    }
  }
  walk(dist);
  return digest.digest("hex").slice(0, 12);
}

export function printRendererSplash(tool: RendererTool): void {
  const root = repositoryRoot(__dirname);
  const release = root ? fs.readFileSync(path.join(root, "VERSION"), "utf8").trim() : "bundled";
  const revision = gitSha(root);
  const dist = path.resolve(__dirname, ".."); // compiled dist/standalone-renderer -> dist
  const build = buildSha(dist);
  const title = tool === "RENDER" ? "BOARD RENDER" : "SCHEMATIC";
  process.stderr.write(
    "\n" +
    "┏━━━━━━━━━━━━ STRIPBOARD · " + title + " ━━━━━━━━━━━━┓\n" +
    "┃ Release " + release + "  |  Git " + revision + "\n" +
    "┃ Compiled renderer sha256 " + build + "\n" +
    "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n" +
    "[TOOL-REVISION] tool=" + tool + " release=" + release +
    " git=" + revision + " build_sha256=" + build + "\n"
  );
}
