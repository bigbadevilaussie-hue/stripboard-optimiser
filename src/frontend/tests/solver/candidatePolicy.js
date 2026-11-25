// Explicit candidate qualification. Strict validity is never redefined.
// Saved-board audits are the authority; native prequalification is diagnostic.
"use strict";

const POLICIES = Object.freeze(["strict", "diagonal", "crossings", "archive"]);
const NONVERTICAL = /^NONVERTICAL_[1-9]\d*$/;
const BODY_CROSSINGS = /^BODY_CROSSINGS_[1-9]\d*$/;
const NATIVE_SLANTED = /^SLANTED_[1-9]\d*$/;
const NATIVE_CROSSINGS = /^CROSSINGS_[1-9]\d*$/;

function assertPolicy(policy) {
  if (!POLICIES.includes(policy)) {
    throw new RangeError("candidate policy must be one of: " + POLICIES.join(", "));
  }
  return policy;
}

function counts(failures, pattern) {
  return failures.reduce((total, f) => {
    if (!pattern.test(f)) return total;
    const n = Number(f.slice(f.lastIndexOf("_") + 1));
    return total + n;
  }, 0);
}

// Classify failures emitted by the independent saved-board auditor, not
// raw native SOLVER_ISSUES. Unknown faults are HARD failures, not exemptions.
// A crossing means a jumper intersects a component BODY: research only.
function classifySavedAudit(audit, policy = "strict") {
  assertPolicy(policy);
  if (!audit || !Array.isArray(audit.failures) ||
      typeof audit.valid !== "boolean" ||
      audit.failures.some((f) => typeof f !== "string")) {
    return { policy, status: "AUDIT_ERROR", qualified: false, strictValid: false,
      electricalComplete: false, diagonals: 0, bodyCrossings: 0,
      hardFailures: ["INVALID_AUDIT_RESULT"] };
  }
  const failures = [...new Set(audit.failures)];
  const diagonals = Number.isInteger(audit.nonvertical) ? audit.nonvertical : counts(failures, NONVERTICAL);
  const bodyCrossings = Number.isInteger(audit.crossings) ? audit.crossings : counts(failures, BODY_CROSSINGS);
  const strictValid = audit.valid === true && failures.length === 0;
  const electricalComplete = !failures.some((f) =>
    /^(INCOMPLETE_|CONFLICTS_|UNPLACED_|UNRESOLVED_COMPONENT_DEFS_|PROJECT_NETLIST_OR_DEFINITIONS_CHANGED|MISSING_COMPONENT_)/.test(f));
  const hardFailures = failures.filter((f) =>
    !NONVERTICAL.test(f) && !BODY_CROSSINGS.test(f));

  // An internally contradictory audit must NEVER qualify.
  if (audit.valid !== (failures.length === 0) ||
      diagonals < 0 || bodyCrossings < 0 ||
      (diagonals > 0) !== failures.some((f) => NONVERTICAL.test(f)) ||
      (bodyCrossings > 0) !== failures.some((f) => BODY_CROSSINGS.test(f))) {
    return { policy, status: "AUDIT_ERROR", qualified: false, strictValid: false,
      electricalComplete: false, diagonals, bodyCrossings,
      hardFailures: ["INCONSISTENT_AUDIT_RESULT"] };
  }

  let status = "REJECTED";
  if (strictValid) status = "STRICT_PASS";
  else if (hardFailures.length === 0) {
    if (bodyCrossings > 0) status = "ROUTE_CANDIDATE";
    else if (diagonals > 0) status = "DIAG_PASS";
  }
  const qualified = status === "STRICT_PASS" ||
    (status === "DIAG_PASS" && ["diagonal", "crossings", "archive"].includes(policy)) ||
    (status === "ROUTE_CANDIDATE" && ["crossings", "archive"].includes(policy));
  // Archive is discovery only: it retains failures, never makes them pass.
  return {
    policy, status, qualified, strictValid, electricalComplete,
    diagonals, bodyCrossings, hardFailures,
    archiveOnly: policy === "archive" && !qualified,
    buildReady: strictValid,
  };
}

// The native run is a useful cheap FILTER, not the qualification authority.
// SOLVER_ISSUES is a catch-all; it may accompany routing violations. We allow
// it through prequalification only; the saved-board audit decides acceptance.
function classifyNativeDiagnostic(native, policy = "strict") {
  assertPolicy(policy);
  const failures = Array.isArray(native?.strictFailures) ? native.strictFailures : null;
  if (!failures || typeof native.strictValid !== "boolean" ||
      failures.some((f) => typeof f !== "string")) {
    return { policy, prequalified: false, strictValid: false,
      needsSavedAudit: true, blockingFailures: ["NO_STRICT_DIAGNOSTICS"] };
  }
  const strictValid = native.strictValid && failures.length === 0;
  const allowed = (f) => {
    if (policy === "strict") return false;
    if (NONVERTICAL.test(f) || NATIVE_SLANTED.test(f)) return true;
    if (["crossings", "archive"].includes(policy) && NATIVE_CROSSINGS.test(f)) return true;
    return f === "SOLVER_ISSUES";
  };
  const blockingFailures = strictValid ? [] : failures.filter((f) => !allowed(f));
  return {
    policy,
    prequalified: strictValid || blockingFailures.length === 0,
    strictValid,
    needsSavedAudit: true,
    blockingFailures,
    // A native pass is insufficient: even a strict PASS must be audited.
  };
}

module.exports = { POLICIES, assertPolicy, classifySavedAudit, classifyNativeDiagnostic };
