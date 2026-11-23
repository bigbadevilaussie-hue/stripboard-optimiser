// One v5 solve of one corpus project for one seed; prints a JSON line.
//   node tests/solver/v5Solve.js --data <dir> --id <n> --seed <k> --moves <m> [--out <compiled dir>]
//        [--movelog <dir>]   one gzipped CSV of every anneal proposal per id/seed
//                            (last column: the leaf of a stacked solve, empty for a joint one)
//        [--time <ms>]       wall-time budget per seed instead of --moves
//        [--speedprobe <n>]  only time n decodes of random genomes (prints probeMs)
//        [--progress 1]      print the anneal's progress reports with their time (stderr)
//        [--effort <x>]      moves = the pin-count formula times x (the editor's effort; --time then only guards)
//        [--routing-preference wires|cuts] favour fewer wires or fewer cuts
//        [--drilled 1]       drilled cuts only
//        [--drill-domain 0|1]  opt-in native drilled rotation domain toggle; 0 restores baseline rotation search
//        [--wire-polish 0|1]  verified fixed-board wire-column and drill-hole local search (default OFF)
//        [--nostack 1]       no wire stacking
//        [--strict 1]        reject invalid/physically noncompliant layouts (exit 2; retain --save for diagnosis)
//        [--move-summary 1]  count anneal outcomes in memory (no massive per-move gzip file)
//        [--finish-trace 1]  print both repair/router candidate scores and violations (stderr)
//        [--protect 1]       strip groups are never dissolved by the decoder (contradicting proposals refused)
//        [--wasm <file>]     the decoder module (default components/stripboard/v5wasm/v5decode.wasm)
//        [--routewasm <file>] the wire router module (default components/stripboard/v5wasm/v5route.wasm)
//        [--native 1]        decoder and router as native code (npm run build:native; see nativeInstance.js)
//        [--exact 1]         finish every new best of the walk exactly and keep the cheapest
//        [--dump <dir>]      store the seed's skeleton (the anneal's placement and wiring) as <dir>/<id>_s<seed>.json
//        [--stack <pins>]    the stacked solve: leaves under this pin cap, one above the other
//        [--stackfree 1]     with --stack: leaves at their own width instead of one locked width
//        [--stackmin <pins>] with --stack: stack only from this many placeable pins, as the editor does (joint below)
//        [--macro <pins>]    the macro solve: leaves under this pin cap become parts of a top-level anneal
//        [--toptime <ms>]    with --macro: the top-level anneal's own time budget
//        [--topmoves <n>]    with --macro: the top-level anneal's own move count (repeatable under load)
//        [--levels <n>]      with --macro: cluster the clusters, n times in all (default 1)
//        [--upperparts <n>]  with --levels: parts per cluster above the first level (default 3)
//        [--portcap <n>]     with --macro: cap clusters by shared nets, --macro is then the pin ceiling
//        [--mincompress <x>] with --portcap: a group with ports*x > pins stays loose (default 2)
//        [--macrogap <n>]    with --macro: free lines a cluster keeps around itself (default 1)
//        [--save <file>]     write the solved board as a project JSON (see tests/solver/saveToDev.js)
//        [--skeleton <file>] skip the anneal: run the finish alone on a stored skeleton
//        [--repair 0|1|2]    with --skeleton: router only (0), the decoder's board routed again when not clean (1)
//                            or as is (2); without the flag both finishes run and the cheaper board wins, as the editor does
//        [--mix <json>]      another move mix: {"early":[13 entries],"late":[13 entries],"lateFrom":0.5} (decode.c mixEarly;
//                            a table of 12, as before 2026-09-27, has no pull and tie; joint solves only)
//        [--hint <ms/move>]  decode speed of an earlier run: the time budget becomes a fixed count
const timingProcessStart = performance.now();
const timingCpuStart = process.cpuUsage();
const timingEnabled = process.env.STRIPBOARD_TIMING === "1";
const fs = require("fs");
const path = require("path");
const { metrics } = require("./metricsLib.js");
const { auditKnifeCuts } = require("./knifeCutAudit.js");
const { DEFAULT_COMPONENTS, checkGeometry, verify, computeStripSegments, computeConnectivity,
  flexGeometry, partGeometry, boardLayout, resolveComponentDef } = require("./helpers.js");

const args = process.argv.slice(2);
const argVal = (name) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : undefined;
};
const CLI_AUDIT_VERSION = "v1.60-cli-audit";
const valueFlags = new Set([
  "data", "drilled", "dump", "effort", "exact", "finish-trace", "hint", "id",
  "levels", "macro", "macrogap", "mincompress", "mix", "move-summary", "movelog",
  "moves", "native", "nostack", "out", "portcap", "progress", "protect",
  "repair", "routewasm", "routing-preference", "drill-domain", "wire-polish", "save", "sched", "seed",
  "skeleton", "speedprobe", "stack", "stackfree", "stackmin", "strict",
  "time", "topmoves", "toptime", "upperparts", "wasm",
]);
const cliUsageError = (message) => {
  process.stderr.write(`CLI argument error: ${message} (exit 64)\n`);
  process.exit(64);
};
const seenFlags = new Set();
for (let i = 0; i < args.length; i += 2) {
  const flag = args[i];
  if (!flag.startsWith("--") || !valueFlags.has(flag.slice(2))) cliUsageError(`unknown argument ${flag}`);
  if (i + 1 >= args.length || args[i + 1].startsWith("--")) cliUsageError(`missing value for ${flag}`);
  if (seenFlags.has(flag)) cliUsageError(`duplicate ${flag}`);
  seenFlags.add(flag);
}
for (const flag of ["native", "drilled", "drill-domain", "wire-polish", "nostack", "strict", "move-summary", "finish-trace", "progress", "exact", "protect", "stackfree"]) {
  const val = argVal(flag);
  if (val !== undefined && val !== "0" && val !== "1") cliUsageError(`--${flag} must be 0 or 1`);
}
if (!argVal("data")) cliUsageError("--data is required");
if (!argVal("id") || !Number.isSafeInteger(Number(argVal("id"))) || Number(argVal("id")) < 0) cliUsageError("--id must be a nonnegative integer");
if (argVal("seed") !== undefined && !Number.isSafeInteger(Number(argVal("seed")))) cliUsageError("--seed must be an integer");
if (argVal("moves") !== undefined && (!Number.isSafeInteger(Number(argVal("moves"))) || Number(argVal("moves")) <= 0)) cliUsageError("--moves must be a positive integer");
if (argVal("routing-preference") !== undefined && !["wires", "cuts"].includes(argVal("routing-preference"))) cliUsageError("--routing-preference must be wires or cuts");
if (argVal("repair") !== undefined && !["0", "1", "2"].includes(argVal("repair"))) cliUsageError("--repair must be 0, 1 or 2");

const OUT = path.resolve(argVal("out") ?? path.join(__dirname, "out"));
const { computeAutoLayout5, finishFromSkeleton } = require(path.join(OUT, "components/stripboard/autoLayout5.js"));
// the stacked solve only exists in builds from 2026-09-25 on
const computeAutoLayout5Macro = (() => { try { return require(path.join(OUT, "components/stripboard/autoLayout5Macro.js")).computeAutoLayout5Macro; } catch { return undefined; } })();
const computeAutoLayout5Stack = (() => { try { return require(path.join(OUT, "components/stripboard/autoLayout5Stack.js")).computeAutoLayout5Stack; } catch { return undefined; } })();
const { rateResult } = require(path.join(OUT, "components/stripboard/autoLayout2.js"));
// the shared price (layout2/boardPrice) only exists in builds from 2026-09-24 on
const priceResult = (() => { try { return require(path.join(OUT, "components/stripboard/layout2/boardPrice.js")).priceResult; } catch { return undefined; } })();
const { expandOffBoard } = require(path.join(OUT, "components/stripboard/offBoard.js"));

const dataDir = argVal("data");
const id = Number(argVal("id"));
const seed = Number(argVal("seed") ?? 0);
const moves = argVal("moves") ? Number(argVal("moves")) : undefined;
const moveLogDir = argVal("movelog");
const sched = argVal("sched") ? JSON.parse(argVal("sched")) : undefined;
const timeMs = argVal("time") ? Number(argVal("time")) : undefined;
const effort = argVal("effort") ? Number(argVal("effort")) : undefined;
const tProg = performance.now();
const speedProbe = argVal("speedprobe") ? Number(argVal("speedprobe")) : undefined;
const onProgress = argVal("progress") === "1" ? (p) => console.error(`progress ${p.frac.toFixed(3)} ${((performance.now() - tProg) / 1000).toFixed(2)}s`) : undefined;
const drilled = argVal("drilled") === "1";
const drillDomain = argVal("drill-domain") === undefined ? undefined : argVal("drill-domain") === "1";
const wirePolish = argVal("wire-polish") === "1";
let wirePolishStats = null;
const noStack = argVal("nostack") === "1";
const strict = argVal("strict") === "1";
const moveSummaryEnabled = argVal("move-summary") === "1";
const finishTraceEnabled = argVal("finish-trace") === "1";
const routingPreference = argVal("routing-preference") === "cuts" ? "cuts" : "wires";
const exact = argVal("exact") === "1";
const protect = argVal("protect") === "1";
// the decoder and the wire router in WebAssembly ("1" also means the default
// file, as older runs passed it); builds before 2026-09-26 route in TypeScript
const moduleOf = (arg, file) => new WebAssembly.Module(fs.readFileSync(arg && arg !== "1" ? arg : path.join(__dirname, "../../components/stripboard/v5wasm", file)));
const wasmOpts = { wasm: moduleOf(argVal("wasm"), "v5decode.wasm") };
const routeModule = moduleOf(argVal("routewasm"), "v5route.wasm");
if (argVal("native") === "1") require("./nativeInstance.js").install(wasmOpts.wasm, routeModule);
try {
  const { setRouteWasm } = require(path.join(OUT, "components/stripboard/v5wasm/routeWasm.js"));
  setRouteWasm(routeModule);
} catch (err) {
  if (err.code !== "MODULE_NOT_FOUND") throw err;
}
const dumpDir = argVal("dump");
const skeletonFile = argVal("skeleton");
const repair = argVal("repair") === "1" ? "fallback" : argVal("repair") === "2" ? "only" : argVal("repair") === "0" ? "never" : undefined;
const hint = argVal("hint") ? Number(argVal("hint")) : undefined;
const moveMix = argVal("mix") ? JSON.parse(argVal("mix")) : undefined;
let stackCap = argVal("stack") ? Number(argVal("stack")) : undefined;
const stackMin = argVal("stackmin") ? Number(argVal("stackmin")) : undefined;
const stackFree = argVal("stackfree") === "1";
const macroCap = argVal("macro") ? Number(argVal("macro")) : undefined;
const topTime = argVal("toptime") ? Number(argVal("toptime")) : undefined;
const topMoves = argVal("topmoves") ? Number(argVal("topmoves")) : undefined;
const saveFile = argVal("save");
const levels = argVal("levels") ? Number(argVal("levels")) : undefined;
const upperParts = argVal("upperparts") ? Number(argVal("upperparts")) : undefined;
const portCap = argVal("portcap") ? Number(argVal("portcap")) : undefined;
const macroGap = argVal("macrogap") !== undefined ? Number(argVal("macrogap")) : undefined;
const minCompress = argVal("mincompress") ? Number(argVal("mincompress")) : undefined;
let stackInfo;
const solverTiming = {};
const collectSolverTiming = (stats) => {
  for (const [key, value] of Object.entries(stats)) solverTiming[key] = (solverTiming[key] ?? 0) + value;
};
const { getComponentBounds } = require(path.join(OUT, "components/stripboard/boardLayout.js"));
let budget;
// The log is written as the run goes, in blocks, through one gzip stream:
// a full anneal is millions of proposals and keeping them all in memory
// cost about 2 GB per worker on a big board, which 12 workers cannot afford.
let logBuf = [];
// written synchronously, one gzip member per batch: the anneal never yields to
// the event loop, so an async stream would hold the whole log in memory
let logGz = null;
const logFlush = () => {
  if (!logGz || logBuf.length === 0) return;
  fs.writeSync(logGz, require("zlib").gzipSync(logBuf.join("\n") + "\n", { level: 1 }));
  logBuf = [];
};
const moveSummary = moveSummaryEnabled
  ? { attempted: 0, mutateFailed: 0, decodeFailed: 0, rejected: 0, accepted: 0, sameBoard: 0, newBest: 0, byKind: {} }
  : undefined;
const moveLog = (moveLogDir || moveSummaryEnabled)
  ? (r, leaf) => {
      if (moveSummary) {
        moveSummary.attempted++;
        if (r.out === 0) moveSummary.mutateFailed++;
        else if (r.out === 1) moveSummary.decodeFailed++;
        else if (r.out === 2) moveSummary.rejected++;
        else if (r.out === 3) moveSummary.accepted++;
        if (r.out >= 2 && r.same) moveSummary.sameBoard++;
        if (r.best) moveSummary.newBest++;
        moveSummary.byKind[r.kind] = (moveSummary.byKind[r.kind] ?? 0) + 1;
      }
      if (!moveLogDir) return;
      if (!logGz) {
        fs.mkdirSync(moveLogDir, { recursive: true });
        logGz = fs.openSync(path.join(moveLogDir, `${id}_s${seed}.csv.gz`), "w");
      }
      logBuf.push(
        r.out < 2
          ? `${id},${seed},${r.it},${r.kind},${r.out},,,,,,,,,,,,,,,,,,${leaf ?? ""}`
          : `${id},${seed},${r.it},${r.kind},${r.out},${r.best},${r.same},${r.dEcur.toFixed(2)},${r.dEfin.toFixed(2)},${r.curFin.toFixed(2)},` +
            `${r.dArea},${r.dWires},${r.dWlen},${r.dCuts},${r.dBcuts},${r.dMess},${r.dHard},${r.dStarv},${r.dOther.toFixed(2)},${r.dGeo},${r.dOverlap},${r.dStarvH},${leaf ?? ""}`
      );
      if (logBuf.length >= 8192) logFlush();
    }
  : undefined;

const timingStartupEnd = performance.now();
const data = JSON.parse(fs.readFileSync(path.join(dataDir, "projects", `${id}.json`), "utf8"));
const defs = [...DEFAULT_COMPONENTS, ...(data.componentDefs ?? [])];
const nets = data.nets ?? [];
const asg = data.netAssignments ?? [];
const blankComps = data.components.map((c) => (
  c.locked && c.boardPos
    ? { ...c }
    : { ...c, boardPos: null, flexibleEndPos: undefined, rotation: 0, locked: undefined }
));
const blankBoard = { ...data.board, cuts: [], wires: [] };
const edgeMountDiagnostic = strict && blankComps.some((c) => c.locked && c.edge === true);
let edgeFeasibility = null;
const timingInputEnd = performance.now();

// Harness-only validation for BOTH finish candidates. The normal solver still
// makes its original selection; these checks are never fed into it.
const traceView = finishTraceEnabled ? expandOffBoard(blankComps, defs, asg) : null;
function validateFinishCandidate(final, shown) {
  if (!final || !shown || !traceView) return null;
  const placements = new Map(final.placements.map((p) => [p.componentId, p]));
  const comps = traceView.components.map((c) => {
    const p = placements.get(c.id);
    return p ? { ...c, boardPos: p.boardPos,
      ...(p.rotation !== undefined ? { rotation: p.rotation } : {}),
      ...(p.flexibleEndPos !== undefined ? { flexibleEndPos: p.flexibleEndPos } : {}) } : c;
  });
  const board = { ...blankBoard, ...(final.boardSize ?? {}),
    cuts: final.cuts, wires: final.wires.map((w, i) => ({ id: `trace-w${i}`, ...w })) };
  const electrical = verify(board, comps, nets, traceView.netAssignments, defs);
  const geometry = checkGeometry(board, comps, defs).length;
  const physical = metrics(board, comps, defs, nets, traceView.netAssignments);
  const incomplete = Array.isArray(electrical.incomplete) ? electrical.incomplete.length : electrical.incomplete;
  const lockedComponents = blankComps.filter((c) => c.locked && c.boardPos);
  const lockedPartsKept = lockedComponents.every((c) => {
    const p = placements.get(c.id);
    if (!p) return true; // a locked component excluded from placements retains its original position
    return p.boardPos?.row === c.boardPos.row && p.boardPos?.col === c.boardPos.col &&
      (p.rotation ?? c.rotation ?? 0) === (c.rotation ?? 0);
  });
  const lockedBoardKept = (!blankBoard.lockedRows || board.rows === blankBoard.rows) &&
    (!blankBoard.lockedCols || board.cols === blankBoard.cols);
  const fails = [];
  if (final.quality !== 0) fails.push("QUALITY");
  if (electrical.conflicts !== 0) fails.push("CONFLICTS");
  if (incomplete !== 0) fails.push("INCOMPLETE");
  if (geometry !== 0) fails.push("GEOMETRY");
  // Historical strict rule: every jumper must be vertical. This includes
  // horizontal links as a failure, not just genuine slanted links.
  if (shown.columnShiftWires !== 0) fails.push("COLUMN_SHIFT");
  if (physical.crossings !== 0) fails.push("CROSSINGS");
  if (final.issues?.length) fails.push("ISSUES");
  if (!lockedPartsKept) fails.push("LOCKED_PART");
  if (!lockedBoardKept) fails.push("LOCKED_BOARD");
  if (drilled && shown.knife !== 0) fails.push("KNIFE");
  if (noStack && shown.stacked !== 0) fails.push("STACKED");
  return { compliant: fails.length === 0, failReasons: fails, conflicts: electrical.conflicts,
    incomplete, geometry, crossingsHarness: physical.crossings, lockedBoardKept, lockedPartsKept };
}
function emitFinishTrace(trace) {
  const { rawCandidates, ...visible } = trace;
  for (const which of ["repair", "router"]) {
    if (visible[which] && rawCandidates?.[which]) {
      visible[which] = { ...visible[which],
        verification: validateFinishCandidate(rawCandidates[which], visible[which]) };
    }
  }
  visible.anyCompliant = !!(visible.repair?.verification?.compliant || visible.router?.verification?.compliant);
  visible.selectedCompliant = !!visible[visible.selected]?.verification?.compliant;
  process.stderr.write(`finishTrace ${JSON.stringify(visible)}\n`);
}
if (stackCap && stackMin) {
  const placeable = new Set(blankComps.filter((c) => !c.boardExcluded).map((c) => c.id));
  if (asg.filter((a) => placeable.has(a.componentId)).length < stackMin) stackCap = undefined;
}

const t0 = Date.now();
// the anneal's own best skeleton for this seed, read off the debugSeeds line
let decoded;
const origLog = console.log;
console.log = (...a) => {
  const m = a.join(" ").match(/^\[v5 seed \d+\] E ([\d.]+) decoded (\d+)x(\d+) (\{.*\})$/);
  if (m) decoded = { E: Number(m[1]), rows: Number(m[2]), cols: Number(m[3]), ...JSON.parse(m[4]) };
  else if (!/^FP0? /.test(a[0] ?? "") && !/^\[v5 seed /.test(a[0] ?? "")) origLog(...a);
};
let res;
try {
  if (skeletonFile) {
    const sk = JSON.parse(fs.readFileSync(skeletonFile, "utf8"));
    const m = sk.metrics;
    decoded = { E: m.eBase + 400 * m.mess, rows: sk.rows, cols: sk.cols, wires: m.wires, wireLen: m.wireLen, cuts: m.cuts, bCuts: m.bCuts };
    res = finishFromSkeleton(blankBoard, blankComps, defs, nets, asg, sk, { drilledCutsOnly: drilled, noWireStacking: noStack, ...(repair ? { repair } : {}) });
  } else if (macroCap) {
    if (!computeAutoLayout5Macro) throw new Error("this build has no macro solve");
    res = computeAutoLayout5Macro(blankBoard, blankComps, defs, nets, asg, undefined, {
      pinCap: macroCap,
      seeds: 1,
      seedBase: seed,
      ...(moves ? { moves } : {}),
      ...(timeMs ? { timeBudgetMs: timeMs } : {}),
      ...(topTime ? { topTimeBudgetMs: topTime } : {}),
      ...(topMoves ? { topMoves } : {}),
      ...(levels ? { levels } : {}),
      ...(upperParts ? { upperPartCap: upperParts } : {}),
      ...(portCap ? { portCap } : {}),
      ...(macroGap !== undefined ? { clusterGap: macroGap } : {}),
      ...(minCompress ? { minCompress } : {}),
      ...(drilled ? { drilledCutsOnly: true } : {}),
      ...(noStack ? { noWireStacking: true } : {}),
      ...(exact ? { exactBest: true } : {}),
      onInfo: (info) => { stackInfo = info; },
    });
  } else if (stackCap) {
    if (!computeAutoLayout5Stack) throw new Error("this build has no stacked solve");
    res = computeAutoLayout5Stack(blankBoard, blankComps, defs, nets, asg, undefined, {
      pinCap: stackCap,
      seeds: 1,
      seedBase: seed,
      ...(moves ? { moves } : {}),
      ...(timeMs ? { timeBudgetMs: timeMs } : {}),
      ...(drilled ? { drilledCutsOnly: true } : {}),
      ...(noStack ? { noWireStacking: true } : {}),
      ...(exact ? { exactBest: true } : {}),
      ...(stackFree ? { freeWidth: true } : {}),
      ...(effort !== undefined ? { effort } : {}),
      ...(protect ? { protectTies: true } : {}),
      ...wasmOpts,
      ...(moveLog ? { moveLog } : {}),
      onLeaves: (info) => { stackInfo = info; },
    });
  } else res = computeAutoLayout5(blankBoard, blankComps, defs, nets, asg, onProgress, {
    seedIndex: seed,
    ...(moves ? { moves } : {}),
    ...(moveLog ? { moveLog } : {}),
    ...(moveMix ? { moveMix } : {}),
    ...(sched ? { schedule: sched } : {}),
    ...(timeMs ? { timeBudgetMs: timeMs, onBudget: (b) => { budget = b; } } : {}),
    ...(effort !== undefined ? { effort } : {}),
    ...(drilled ? { drilledCutsOnly: true } : {}),
    ...(drillDomain !== undefined ? { drilledRotationDomain: drillDomain } : {}),
    ...(wirePolish ? { wirePolish: true,
      onWirePolish: (stats) => { wirePolishStats = stats; } } : {}),
    ...(noStack ? { noWireStacking: true } : {}),
    routingPreference,
    ...(exact ? { exactBest: true } : {}),
    ...(protect ? { protectTies: true } : {}),
    ...wasmOpts,
    ...(hint ? { msPerMoveHint: hint } : {}),
    ...(speedProbe ? { speedProbe, onSpeedProbe: (ms) => { process.stderr.write(`probeMs ${ms}\n`); } } : {}),
    debugSeeds: true,
    ...(edgeMountDiagnostic ? { onEdgeFeasibility: (info) => { edgeFeasibility = info; } } : {}),
    ...(timingEnabled ? { onTiming: collectSolverTiming } : {}),
    ...(finishTraceEnabled ? { onFinishTrace: emitFinishTrace } : {}),
    ...(dumpDir ? { onSkeleton: (s, sk) => { fs.mkdirSync(dumpDir, { recursive: true }); fs.writeFileSync(path.join(dumpDir, `${id}_s${s}.json`), JSON.stringify(sk)); } } : {}),
  });
} catch (err) {
  if (timingEnabled) process.stderr.write(`timing ${JSON.stringify({pid: process.pid, seed, error: String(err), elapsedMs: +(performance.now() - timingProcessStart).toFixed(2)})}\n`);
  console.log(JSON.stringify({ id, seed, error: String(err && err.message ? err.message : err) }));
  process.exit(1);
}
console.log = origLog;
const timingSolveEnd = performance.now();
const ms = Date.now() - t0;
if (logGz) {
  logFlush();
  fs.closeSync(logGz);
}
const rate = rateResult(res, blankBoard, blankComps, defs, drilled);
const price = priceResult ? priceResult(res, blankBoard, expandOffBoard(blankComps, defs, asg).components, defs, drilled, routingPreference) : undefined;
// a fingerprint of the board itself, for bit-identical checks across refactors
const sig = require("crypto").createHash("sha1").update(JSON.stringify({
  size: res.boardSize,
  placements: [...res.placements].sort((a, b) => (a.componentId < b.componentId ? -1 : 1)),
  cuts: [...res.cuts].sort((a, b) => a.row - b.row || a.col - b.col || (a.kind < b.kind ? -1 : 1)),
  wires: [...res.wires].map((w) => [w.from.row, w.from.col, w.to.row, w.to.col]).sort(),
})).digest("hex").slice(0, 12);
const timingScoreEnd = performance.now();
const byId = new Map(res.placements.map((p) => [p.componentId, p]));
const solvedComps = blankComps.map((c) => {
  const p = byId.get(c.id);
  if (!p) return c;
  return {
    ...c,
    boardPos: p.boardPos,
    ...(p.rotation !== undefined ? { rotation: p.rotation } : {}),
    ...(p.flexibleEndPos !== undefined ? { flexibleEndPos: p.flexibleEndPos } : {}),
  };
});
const solvedBoard = {
  ...blankBoard,
  ...(res.boardSize ?? {}),
  cuts: res.cuts,
  wires: res.wires.map((w, i) => ({ id: `w${i}`, ...w })),
};
// the solved board as a project the editor can open: pads folded back onto
// their off-board parents, the board replaced, a name that says what it is
if (saveFile) {
  const { collapseLeads } = require(path.join(OUT, "components/stripboard/offBoard.js"));
  const positions = new Map(res.placements.map((p) => [p.componentId, p.boardPos]));
  const tag = stackCap ? `stack${stackCap}` : macroCap ? `macro${macroCap}` : "joint";
  const saved = {
    ...data,
    name: `${tag} of prod ${id} seed ${seed}`,
    components: collapseLeads(solvedComps, positions),
    board: { ...data.board, rows: solvedBoard.rows, cols: solvedBoard.cols, cuts: solvedBoard.cuts, wires: solvedBoard.wires, lockedRows: data.board.lockedRows ?? false, lockedCols: data.board.lockedCols ?? false },
    autoLayoutUsed: true,
  };
  fs.writeFileSync(saveFile, JSON.stringify(saved));
}
const timingSaveEnd = performance.now();
// measured as the editor sees the board: an off-board part is its pads, placed
// where the layouter put them (until 2026-09-28 the parents were measured, so
// every net through an off-board part counted as incomplete)
const view = expandOffBoard(blankComps, defs, asg);
const boardComps = view.components.map((c) => {
  const p = byId.get(c.id);
  return p ? { ...c, boardPos: p.boardPos, ...(p.rotation !== undefined ? { rotation: p.rotation } : {}), ...(p.flexibleEndPos !== undefined ? { flexibleEndPos: p.flexibleEndPos } : {}) } : c;
});
const m = metrics(solvedBoard, boardComps, defs, nets, view.netAssignments);
// connectors: off any edge, or on an edge but reaching into the board
let connOff = 0, connIn = 0, knife = 0;
for (const c of boardComps) {
  const def = defs.find((x) => x.id === c.defId);
  if (!def || def.category !== "connector" || !c.boardPos || c.boardExcluded) continue;
  let minRow, maxRow, minCol, maxCol;
  if (def.flexible) { const e = c.flexibleEndPos ?? c.boardPos; minRow = Math.min(c.boardPos.row, e.row); maxRow = Math.max(c.boardPos.row, e.row); minCol = Math.min(c.boardPos.col, e.col); maxCol = Math.max(c.boardPos.col, e.col); }
  else { const b = getComponentBounds(def, c.boardPos, c.rotation ?? 0); minRow = b.minRow; maxRow = b.maxRow; minCol = b.minCol; maxCol = b.maxCol; }
  const w = maxCol - minCol + 1, h = maxRow - minRow + 1;
  const onL = minCol === 0, onR = maxCol === solvedBoard.cols - 1, onT = minRow === 0, onB = maxRow === solvedBoard.rows - 1;
  if (!(onL || onR || onT || onB)) connOff++;
  else if (!(((onL || onR) && h >= w) || ((onT || onB) && w >= h))) connIn++;
}
for (const cut of solvedBoard.cuts) if (cut.kind !== "hole") knife++;
const { wireStackDepth } = require(path.join(OUT, "components/stripboard/flexGeometry.js"));
const stacked = res.wires.filter((w, i) => wireStackDepth(w.from, w.to, res.wires.slice(0, i)) > 0).length;
const v = verify(solvedBoard, boardComps, nets, view.netAssignments, defs);
const geo = checkGeometry(solvedBoard, boardComps, defs).length;
// Do not report a deliberately EMPTY fallback board as if the solver built
// 35 badly connected nets. It is an explicit failure to find/finish placement.
const unsolvedText = (res.issues || []).find((i) => typeof i === "string" && i.startsWith("UNSOLVED: "));
const unsolvedReason = unsolvedText ? unsolvedText.slice("UNSOLVED: ".length).split(/[ —]/)[0] : null;

// Edge-mount-only physical diagnostics. Nothing here is fed back to the solver;
// net names are derived from the real connectivity checker, and per-wire
// crossing tests use exactly the same geometry helpers as metrics().
const incompleteNets = edgeMountDiagnostic && !unsolvedReason
  ? v.incomplete.map((n) => ({ id: n.netId, name: n.netName,
      groups: n.groups, unplacedPins: n.unplacedPins }))
  : [];
// Necessary condition for drill-only separation, for ANY rigid part:
/// adjacent hole centres on one copper row must not carry different nets.
/// Unassigned pins are separate floating nets in the real strip checker.
const invalidDrilledOrientations = edgeMountDiagnostic && drilled && !unsolvedReason
  ? boardComps.flatMap((c) => {
      if (!c.boardPos || c.boardExcluded) return [];
      const def = resolveComponentDef(c, defs);
      if (!def || def.flexible) return [];
      const pins = boardLayout.getComponentPinPositions(c, def);
      const assignments = new Map(view.netAssignments.filter((a) => a.componentId === c.id)
        .map((a) => [a.pinId, a.netId]));
      const adjacent = [];
      for (let i = 0; i < pins.length; i++) for (let j = i + 1; j < pins.length; j++) {
        if (pins[i].row !== pins[j].row ||
            Math.abs(pins[i].col - pins[j].col) !== 1) continue;
        const ni = assignments.get(pins[i].pinId), nj = assignments.get(pins[j].pinId);
        if (ni && ni === nj) continue;
        adjacent.push({ pins: [pins[i].pinId, pins[j].pinId],
          nets: [ni ? nets.find((n) => n.id === ni)?.name || ni : "FLOATING",
            nj ? nets.find((n) => n.id === nj)?.name || nj : "FLOATING"] });
      }
      return adjacent.length ? [{
        component: c.label || c.id, rotation: c.rotation ?? 0, adjacent
      }] : [];
    })
  : [];
const knifeCuts = edgeMountDiagnostic && !unsolvedReason
  ? auditKnifeCuts(solvedBoard, boardComps, defs, view.netAssignments, nets) : [];
let wireViolations = [];
if (edgeMountDiagnostic && !unsolvedReason) {
  const segments = computeStripSegments(solvedBoard, boardComps, defs, view.netAssignments);
  const groups = computeConnectivity(segments, solvedBoard.wires);
  const groupBySegment = new Map();
  groups.forEach((g, gi) => g.segmentIndices.forEach((si) => groupBySegment.set(si, gi)));
  const groupNets = groups.map((g) => [...new Set(g.segmentIndices.flatMap((si) => segments[si]?.netIds || []))]);
  const at = (p) => segments.findIndex((seg) =>
    seg.row === p.row && seg.startCol <= p.col && p.col <= seg.endCol);
  const obstacles = boardComps.filter((c) => c.boardPos && !c.boardExcluded).flatMap((c) => {
    const def = resolveComponentDef(c, defs);
    if (!def) return [];
    if (def.flexible) {
      const [a, b] = boardLayout.getFlexiblePinPositions(c, def);
      if (!a || !b) return [];
      const body = partGeometry.flexWireObstacle(def, a, b);
      return [{ component: c.label || c.id, hit: (w) =>
        flexGeometry.wireCrossesBody(w.from, w.to, body) }];
    }
    const body = partGeometry.rigidBody(def, c.boardPos, c.rotation ?? 0);
    return [{ component: c.label || c.id, hit: (w) =>
      flexGeometry.segmentIntersectsRect(w.from, w.to, body) }];
  });
  wireViolations = solvedBoard.wires.flatMap((w, i) => {
    const nonvertical = w.from.col !== w.to.col;
    const slanted = nonvertical && w.from.row !== w.to.row;
    const horizontal = nonvertical && w.from.row === w.to.row;
    const crossingComponents = obstacles.filter((o) => o.hit(w)).map((o) => o.component);
    const stackedWith = solvedBoard.wires.slice(0, i)
      .flatMap((other, j) => flexGeometry.wireStackDepth(w.from, w.to, [other]) > 0 ? [j + 1] : []);
    const violations = [
      ...(nonvertical ? ["NONVERTICAL"] : []),
      ...(slanted ? ["SLANTED"] : []),
      ...(horizontal ? ["HORIZONTAL"] : []),
      ...(crossingComponents.length ? ["CROSSINGS"] : []),
      ...(stackedWith.length ? ["STACKED"] : []),
    ];
    if (!violations.length) return [];
    const sg = groupBySegment.get(at(w.from)) ?? groupBySegment.get(at(w.to));
    const ids = sg === undefined ? [] : groupNets[sg];
    const netNames = ids.length ? ids.map((id) => nets.find((n) => n.id === id)?.name || id)
      : ["UNRESOLVED"];
    return [{ wire: i + 1, netNames, from: w.from, to: w.to,
      violations, crossingComponents, stackedWith }];
  });
}

// This is a gate for the CLI, not a claim that the solver respected its flags.
// Keep the rejected layout on disk when --save is supplied for diagnosis.
const strictFailures = [];
let diagonalsActual, slantedWires, horizontalWires;
if (strict) {
  // diagonalsActual preserves the original benchmark metric: any column change.
  // It includes horizontal (same-row) wires, whereas offAxis counts only slants.
  diagonalsActual = solvedBoard.wires.filter((w) => w.from.col !== w.to.col).length;
  slantedWires = solvedBoard.wires.filter((w) => w.from.col !== w.to.col && w.from.row !== w.to.row).length;
  horizontalWires = solvedBoard.wires.filter((w) => w.from.col !== w.to.col && w.from.row === w.to.row).length;
  if (unsolvedReason) {
    strictFailures.push("UNSOLVED_" + unsolvedReason);
  } else {
    if (res.quality !== 0) strictFailures.push(`QUALITY_${res.quality}`);
    if (v.conflicts !== 0) strictFailures.push(`CONFLICTS_${v.conflicts}`);
    const incompleteN = Array.isArray(v.incomplete) ? v.incomplete.length : v.incomplete;
    if (incompleteN !== 0) strictFailures.push(`INCOMPLETE_${incompleteN}`);
    if (geo !== 0) strictFailures.push(`GEOMETRY_${geo}`);
    if (diagonalsActual !== 0) strictFailures.push(`NONVERTICAL_${diagonalsActual}`);
    if (m.offAxisWires !== 0) strictFailures.push(`SLANTED_${m.offAxisWires}`);
    if (m.crossings !== 0) strictFailures.push(`CROSSINGS_${m.crossings}`);
    if (res.issues?.length) strictFailures.push("SOLVER_ISSUES");
  }
  if (blankBoard.lockedRows && solvedBoard.rows !== blankBoard.rows) strictFailures.push("LOCKED_ROWS");
  if (blankBoard.lockedCols && solvedBoard.cols !== blankBoard.cols) strictFailures.push("LOCKED_COLS");
  // Edge-mount exemptions apply only to the external *body*. No electrical
  // pin, drill cut or wire endpoint can ever be outside the purchased PCB.
  const outsideCopper = (p) => !p || p.row < 0 || p.col < 0 ||
    p.row >= solvedBoard.rows || p.col >= solvedBoard.cols;
  if (solvedBoard.cuts.some((c) => outsideCopper(c))) strictFailures.push("CUT_OUTSIDE_PHYSICAL_BOARD");
  if (solvedBoard.wires.some((w) => outsideCopper(w.from) || outsideCopper(w.to)))
    strictFailures.push("WIRE_OUTSIDE_PHYSICAL_BOARD");
  const actualComponents = new Map(solvedComps.map((c) => [c.id, c]));
  for (const original of blankComps) {
    if (!original.locked || !original.boardPos) continue;
    const actual = actualComponents.get(original.id);
    if (!actual || !actual.boardPos || actual.boardPos.row !== original.boardPos.row ||
        actual.boardPos.col !== original.boardPos.col ||
        (actual.rotation ?? 0) !== (original.rotation ?? 0)) strictFailures.push(`LOCKED_PART_${original.id}`);
  }
  if (drilled && knife !== 0) strictFailures.push(`KNIFE_${knife}`);
  if (noStack && stacked !== 0) strictFailures.push(`STACKED_${stacked}`);
}
const timingVerifyEnd = performance.now();
if (timingEnabled) {
  const cpu = process.cpuUsage(timingCpuStart);
  const ms2 = (a, b) => +(b - a).toFixed(2);
  const timing = {
    pid: process.pid, seed, moves: moves ?? null, lockedParts: blankComps.filter(c => c.locked && c.boardPos).length,
    startupMs: ms2(timingProcessStart, timingStartupEnd),
    inputMs: ms2(timingStartupEnd, timingInputEnd),
    solveMs: ms2(timingInputEnd, timingSolveEnd),
    scoreMs: ms2(timingSolveEnd, timingScoreEnd),
    saveMs: ms2(timingScoreEnd, timingSaveEnd),
    verifyMs: ms2(timingSaveEnd, timingVerifyEnd),
    totalMs: ms2(timingProcessStart, timingVerifyEnd),
    cpuMs: +((cpu.user + cpu.system) / 1000).toFixed(2),
    rssMb: +(process.memoryUsage().rss / 1048576).toFixed(1),
    ...Object.fromEntries(Object.entries(solverTiming).map(([key, value]) => [key, +value.toFixed(2)])),
    wires: m.wires, cuts: m.cuts, quality: res.quality,
    conflicts: v.conflicts, incomplete: v.incomplete.length ?? v.incomplete, geo,
  };
  process.stderr.write(`timing ${JSON.stringify(timing)}\n`);
}
console.log(JSON.stringify({
  id, seed, ms, rate, ...(price !== undefined ? { price } : {}), sig,
  ...(budget ? { budget } : {}),
  ...(decoded && !stackCap && !macroCap ? { decoded } : {}),
  ...(stackInfo ? { stack: stackInfo } : {}),
  quality: res.quality,
  ...(edgeMountDiagnostic ? { unsolvedReason, firstFeasibleMove: edgeFeasibility?.firstMove ?? null,
    firstFeasibleMs: edgeFeasibility?.firstMs ?? null, drilledRotationDomain: drillDomain ?? drilled,
    wirePolish: wirePolishStats, incompleteNets, invalidDrilledOrientations, knifeCuts, wireViolations } : {}),
  rows: solvedBoard.rows, cols: solvedBoard.cols, area: solvedBoard.rows * solvedBoard.cols,
  wires: m.wires, offAxis: m.offAxisWires, crossings: m.crossings, stacked, cuts: m.cuts, knife, connOff, connIn,
  conflicts: v.conflicts, incomplete: v.incomplete.length ?? v.incomplete, geo,
  issues: res.issues,
  ...(strict ? { cliVersion: CLI_AUDIT_VERSION, strictValid: strictFailures.length === 0, strictFailures,
    diagonalsActual, slantedWires, horizontalWires } : {}),
  ...(moveSummary ? { moveSummary: { ...moveSummary, percent: {
    mutateFailed: +(100 * moveSummary.mutateFailed / Math.max(1, moveSummary.attempted)).toFixed(2),
    decodeFailed: +(100 * moveSummary.decodeFailed / Math.max(1, moveSummary.attempted)).toFixed(2),
    rejected: +(100 * moveSummary.rejected / Math.max(1, moveSummary.attempted)).toFixed(2),
    accepted: +(100 * moveSummary.accepted / Math.max(1, moveSummary.attempted)).toFixed(2),
    sameBoard: +(100 * moveSummary.sameBoard / Math.max(1, moveSummary.attempted)).toFixed(2),
  } } } : {}),
}));
if (strict && strictFailures.length) process.exitCode = 2;
