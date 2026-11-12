#!/usr/bin/env node
import * as fs from "fs";
import * as path from "path";
import { renderSchematic } from "./render";

const args = process.argv.slice(2);
if (args.length === 0) { console.error("Usage: node cli.js <project.json> --output <dir>"); process.exit(1); }

let inputPath = null, outDir = ".";
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--output" || args[i] === "-o") {
    outDir = args[++i];
  } else if (!args[i].startsWith("-")) {
    inputPath = args[i];
  }
}

if (!inputPath) { process.exit(1); }
const data = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const svg = renderSchematic(data);

fs.mkdirSync(outDir, { recursive: true });
const outPath = path.join(outDir, "schematic.svg");
fs.writeFileSync(outPath, svg);
console.log(`Saved ${outPath}`);
