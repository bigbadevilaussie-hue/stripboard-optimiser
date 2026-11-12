#!/usr/bin/env node
// Standalone stripboard renderer CLI.
// Usage: node dist/cli.js project.json --output ./rendered
// Writes board-top.svg and board-copper.svg.

import * as fs from "fs";
import * as path from "path";
import { renderStripboard } from "./render";

function usage(): never {
  console.error("Usage: node dist/cli.js <project.json> [--output <dir>]");
  process.exit(1);
}

function main(): void {
  const args = process.argv.slice(2);
  if (args.length === 0) usage();

  let inputPath: string | null = null;
  let outputDir = ".";
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--output" || a === "-o") {
      if (i + 1 >= args.length) {
        console.error("Error: --output requires a directory");
        process.exit(1);
      }
      outputDir = args[++i];
    } else if (a.startsWith("--output=")) {
      outputDir = a.slice("--output=".length);
    } else if (a.startsWith("-")) {
      console.error(`Error: unknown option ${a}`);
      process.exit(1);
    } else {
      if (inputPath !== null) {
        console.error("Error: only one input project JSON may be given");
        process.exit(1);
      }
      inputPath = a;
    }
  }

  if (!inputPath) usage();

  if (!fs.existsSync(inputPath)) {
    console.error(`Error: file not found: ${inputPath}`);
    process.exit(1);
  }

  let projectData: any;
  try {
    projectData = JSON.parse(fs.readFileSync(inputPath, "utf8"));
  } catch (e) {
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
    result = renderStripboard(projectData, { color: true, showLabels: true, showPinLabels: true });
  } catch (e) {
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
