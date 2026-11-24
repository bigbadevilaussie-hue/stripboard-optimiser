"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.printRendererSplash = printRendererSplash;
/**
 * Runtime revision banner for the compiled headless SVG renderers.
 * Only logs to stderr. No SVG, output path, rendering data or solver behavior changes.
 */
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const crypto_1 = require("crypto");
function repositoryRoot(start) {
    for (let dir = path.resolve(start);; dir = path.dirname(dir)) {
        if (fs.existsSync(path.join(dir, "VERSION")) &&
            fs.existsSync(path.join(dir, "src", "frontend")))
            return dir;
        if (path.dirname(dir) === dir)
            return null;
    }
}
function gitSha(root) {
    if (!root)
        return "unavailable";
    try {
        const dot = path.join(root, ".git");
        let gitdir = dot;
        if (fs.statSync(dot).isFile()) {
            const file = fs.readFileSync(dot, "utf8").trim();
            if (!file.startsWith("gitdir: "))
                return "unavailable";
            gitdir = path.resolve(root, file.slice(8));
        }
        const head = fs.readFileSync(path.join(gitdir, "HEAD"), "utf8").trim();
        if (/^[a-f0-9]{40}$/i.test(head))
            return head.slice(0, 12);
        if (!head.startsWith("ref: "))
            return "unavailable";
        const ref = head.slice(5);
        const loose = path.join(gitdir, ref);
        if (fs.existsSync(loose))
            return fs.readFileSync(loose, "utf8").trim().slice(0, 12);
        const packed = fs.readFileSync(path.join(gitdir, "packed-refs"), "utf8");
        const line = packed.split(/\r?\n/).find(s => s.endsWith(" " + ref));
        return line ? line.split(" ")[0].slice(0, 12) : "unavailable";
    }
    catch {
        return "unavailable";
    }
}
// The compiled dist tree is the executable renderer, not the current TS source.
// Hashing it prevents a stale dist build from masquerading as a new revision.
// Both tools share library files and see the same dist build fingerprint.
function buildSha(dist) {
    const digest = (0, crypto_1.createHash)("sha256");
    function walk(dir) {
        const files = fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name));
        for (const file of files) {
            const absolute = path.join(dir, file.name);
            if (file.isDirectory())
                walk(absolute);
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
function printRendererSplash(tool) {
    const root = repositoryRoot(__dirname);
    const release = root ? fs.readFileSync(path.join(root, "VERSION"), "utf8").trim() : "bundled";
    const revision = gitSha(root);
    const dist = path.resolve(__dirname, ".."); // compiled dist/standalone-renderer -> dist
    const build = buildSha(dist);
    const title = tool === "RENDER" ? "BOARD RENDER" : "SCHEMATIC";
    process.stderr.write("\n" +
        "┏━━━━━━━━━━━━ STRIPBOARD · " + title + " ━━━━━━━━━━━━┓\n" +
        "┃ Release " + release + "  |  Git " + revision + "\n" +
        "┃ Compiled renderer sha256 " + build + "\n" +
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n" +
        "[TOOL-REVISION] tool=" + tool + " release=" + release +
        " git=" + revision + " build_sha256=" + build + "\n");
}
