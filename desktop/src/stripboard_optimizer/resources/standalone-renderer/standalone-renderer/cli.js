#!/usr/bin/env node
"use strict";
// Standalone stripboard renderer CLI.
// Usage: node dist/cli.js project.json --output ./rendered
// Writes board-top.svg and board-copper.svg.
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
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const render_1 = require("./render");
function usage() {
    console.error("Usage: node dist/cli.js <project.json> [--output <dir>]");
    process.exit(1);
}
function main() {
    const args = process.argv.slice(2);
    if (args.length === 0)
        usage();
    let inputPath = null;
    let outputDir = ".";
    for (let i = 0; i < args.length; i++) {
        const a = args[i];
        if (a === "--output" || a === "-o") {
            if (i + 1 >= args.length) {
                console.error("Error: --output requires a directory");
                process.exit(1);
            }
            outputDir = args[++i];
        }
        else if (a.startsWith("--output=")) {
            outputDir = a.slice("--output=".length);
        }
        else if (a.startsWith("-")) {
            console.error(`Error: unknown option ${a}`);
            process.exit(1);
        }
        else {
            if (inputPath !== null) {
                console.error("Error: only one input project JSON may be given");
                process.exit(1);
            }
            inputPath = a;
        }
    }
    if (!inputPath)
        usage();
    if (!fs.existsSync(inputPath)) {
        console.error(`Error: file not found: ${inputPath}`);
        process.exit(1);
    }
    let projectData;
    try {
        projectData = JSON.parse(fs.readFileSync(inputPath, "utf8"));
    }
    catch (e) {
        console.error(`Error: could not parse JSON: ${e instanceof Error ? e.message : String(e)}`);
        process.exit(1);
    }
    if (!projectData || typeof projectData !== "object") {
        console.error("Error: project JSON must be an object");
        process.exit(1);
    }
    if (!projectData.board || typeof projectData.board !== "object") {
        console.error("Error: project JSON has no 'board' object");
        process.exit(1);
    }
    if (!Array.isArray(projectData.components)) {
        console.error("Error: project JSON has no 'components' array");
        process.exit(1);
    }
    let result;
    try {
        result = (0, render_1.renderStripboard)(projectData, { color: true, showLabels: true, showPinLabels: true });
    }
    catch (e) {
        console.error(`Error: rendering failed: ${e instanceof Error ? e.message : String(e)}`);
        process.exit(1);
    }
    fs.mkdirSync(outputDir, { recursive: true });
    const topPath = path.join(outputDir, "board-top.svg");
    const copperPath = path.join(outputDir, "board-copper.svg");
    fs.writeFileSync(topPath, result.top);
    fs.writeFileSync(copperPath, result.copper);
    const board = projectData.board;
    const comps = projectData.components.length;
    const wires = Array.isArray(board.wires) ? board.wires.length : 0;
    const cuts = Array.isArray(board.cuts) ? board.cuts.length : 0;
    console.log(`Board:     ${board.rows} rows x ${board.cols} cols`);
    console.log(`Components: ${comps}`);
    console.log(`Wires:     ${wires}`);
    console.log(`Cuts:      ${cuts}`);
    console.log(`Wrote:     ${topPath}`);
    console.log(`Wrote:     ${copperPath}`);
}
main();
