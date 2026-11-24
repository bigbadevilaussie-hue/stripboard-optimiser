"""Adapters from existing IN/PREPARE/SOLVE outputs to pipeline contracts.

The adapters are deliberately observational: they wrap existing return
objects and never call or modify the underlying solver/verifier algorithms.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any, Mapping

from .contracts import Finding, StageResult, make_finding_id, project_sha256


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return deepcopy(dict(value))


def _messages(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be an array of strings")
    return list(value)


def _findings(
    stage: str,
    module: str,
    groups: list[tuple[str, str, list[str]]],
) -> list[Finding]:
    findings = []
    for code, severity, messages in groups:
        occurrences: dict[str, int] = {}
        for message in messages:
            occurrence = occurrences.get(message, 0)
            occurrences[message] = occurrence + 1
            digest = hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
            subjects = [{"type": "stage_message", "key": digest,
                         "occurrence": occurrence}]
            findings.append(Finding(
                finding_id=make_finding_id(stage, code, subjects),
                code=code,
                severity=severity,
                status="open",
                message=message,
                producer={"stage": stage, "module": module},
                subjects=subjects,
                evidence={"message": message},
            ))
    return findings


def _result(
    *,
    stage: str,
    module: str,
    source_project: Mapping[str, Any],
    output_project: Mapping[str, Any] | None,
    report: Mapping[str, Any],
    errors: list[str],
    warnings: list[str],
    metrics: Mapping[str, Any] | None = None,
    options: Mapping[str, Any] | None = None,
    summary: str | None = None,
) -> tuple[StageResult, list[Finding]]:
    findings = _findings(stage, module, [
        (f"{stage.lower().replace('.', '_')}_error", "error", errors),
        (f"{stage.lower().replace('.', '_')}_warning", "warning", warnings),
    ])
    source = _mapping(source_project, "source_project")
    output = source if output_project is None else _mapping(output_project, "output_project")
    result = StageResult(
        stage=stage,
        status="completed",
        module=module,
        input_project_sha256=project_sha256(source),
        output_project_sha256=project_sha256(output),
        options={} if options is None else deepcopy(dict(options)),
        metrics={} if metrics is None else deepcopy(dict(metrics)),
        finding_ids=[item.finding_id for item in findings],
        report=deepcopy(dict(report)),
        summary=summary or f"{stage}: {len(errors)} error(s), {len(warnings)} warning(s).",
    )
    return result, findings


def collector_stage_result(
    project: Mapping[str, Any],
    manifest: Mapping[str, Any],
    index_entry: Mapping[str, Any] | None = None,
    *,
    source_project: Mapping[str, Any] | None = None,
) -> tuple[StageResult, list[Finding]]:
    """Adapt completed collect.py outputs to an IN StageResult."""
    canonical = _mapping(project, "project")
    manifest_data = _mapping(manifest, "manifest")
    index_data = {} if index_entry is None else _mapping(index_entry, "index_entry")
    warnings = _messages(manifest_data.get("warnings", []), "manifest.warnings")
    stage, module = "IN.collect", "collect"
    findings = _findings(stage, module, [("collector_warning", "warning", warnings)])
    metrics = {
        "components": manifest_data.get("component_count", len(canonical.get("components", []))),
        "nets": len(canonical.get("nets", [])),
        "assignments": manifest_data.get("json_pin_assignments", len(canonical.get("netAssignments", []))),
        "custom_definitions": manifest_data.get("custom_definition_count", len(canonical.get("componentDefs", []))),
        "footprints_added": manifest_data.get("footprint_files_parsed", 0),
        "warnings": len(warnings),
    }
    artifacts = [
        {"kind": key, "path": manifest_data[key]}
        for key in ("campaign_project", "campaign_index")
        if isinstance(manifest_data.get(key), str) and manifest_data[key]
    ]
    result = StageResult(
        stage=stage, status="completed", module=module,
        input_project_sha256=project_sha256(source_project) if source_project is not None else None,
        output_project_sha256=project_sha256(canonical),
        options={"actual_board": deepcopy(manifest_data.get("actual_board", {})),
                 "wanted_board": deepcopy(manifest_data.get("wanted_board", {}))},
        metrics=metrics, finding_ids=[item.finding_id for item in findings],
        artifacts=artifacts,
        report={"manifest": manifest_data, "index_entry": index_data, "warnings": warnings},
        summary=f"Collected {metrics['components']} components with {len(warnings)} warning(s).",
    )
    return result, findings



def project_import_stage_result(
    source_project: Mapping[str, Any],
    project: Mapping[str, Any],
    *,
    warnings: list[str] | None = None,
    options: Mapping[str, Any] | None = None,
) -> tuple[StageResult, list[Finding]]:
    """Adapt GUI JSON validation and explicit board sizing as an IN stage.

    This is intentionally distinct from collector_stage_result: the GUI's
    JSON-load path does not create a collector manifest or campaign index.
    """
    source = _mapping(source_project, "source_project")
    canonical = _mapping(project, "project")
    messages = _messages([] if warnings is None else warnings, "warnings")
    stage, module = "IN.project_import", "gui.project_import"
    findings = _findings(stage, module, [
        ("project_import_warning", "warning", messages),
    ])
    result = StageResult(
        stage=stage,
        status="completed",
        module=module,
        input_project_sha256=project_sha256(source),
        output_project_sha256=project_sha256(canonical),
        options={} if options is None else deepcopy(dict(options)),
        metrics={
            "components": len(canonical.get("components", [])),
            "nets": len(canonical.get("nets", [])),
            "assignments": len(canonical.get("netAssignments", [])),
            "warnings": len(messages),
        },
        finding_ids=[item.finding_id for item in findings],
        report={"warnings": messages},
        summary=f"Imported {len(canonical.get('components', []))} components with {len(messages)} warning(s).",
    )
    return result, findings

def electrical_sanity_stage_result(
    project: Mapping[str, Any], report: Mapping[str, Any],
) -> tuple[StageResult, list[Finding]]:
    """Adapt run_electrical_sanity's report; PASS/FAIL remains domain status."""
    canonical = _mapping(project, "project")
    data = _mapping(report, "report")
    status = data.get("status")
    if status not in {"PASS", "FAIL"}:
        raise ValueError("electrical sanity report status must be PASS or FAIL")
    errors = _messages(data.get("errors", []), "report.errors")
    warnings = _messages(data.get("warnings", []), "report.warnings")
    counts = data.get("counts", {})
    if not isinstance(counts, Mapping):
        raise ValueError("report.counts must be an object")
    findings = _findings("PREPARE.electrical", "prepare.sanity.electrical", [
        ("electrical_sanity_error", "error", errors),
        ("electrical_sanity_warning", "warning", warnings),
    ])
    result = StageResult(
        stage="PREPARE.electrical", status="completed",
        module="prepare.sanity.electrical",
        input_project_sha256=project_sha256(canonical),
        output_project_sha256=project_sha256(canonical),
        metrics={
            "components": counts.get("components", 0),
            "nets": counts.get("nets", 0),
            "assignments": counts.get("assignments", 0),
            "errors": len(errors), "warnings": len(warnings),
            "netlist_checked": bool(data.get("netlist_checked", False)),
        },
        finding_ids=[item.finding_id for item in findings],
        report=data,
        summary=f"Electrical sanity {status}: {len(errors)} error(s), {len(warnings)} warning(s).",
    )
    return result, findings



def presolve_stage_result(project: Mapping[str, Any]) -> tuple[StageResult, list[Finding]]:
    """Analyse every component and package the report for the existing sidecar."""
    from prepare.presolve import analyse_project

    canonical = _mapping(project, "project")
    report = analyse_project(canonical)
    warnings = [
        f"{item['component_id']}: {item['code']}"
        for item in report["warnings"]
    ]
    findings = _findings("PREPARE.presolve", "prepare.presolve", [
        ("presolve_warning", "warning", warnings),
    ])
    result = StageResult(
        stage="PREPARE.presolve", status="completed", module="prepare.presolve",
        input_project_sha256=project_sha256(canonical),
        output_project_sha256=project_sha256(canonical),
        metrics={
            "components": len(report["components"]),
            "unresolved_footprints": len(report["warnings"]),
            "placement_candidate_status": report["board"]["placement_candidate_status"],
        },
        finding_ids=[item.finding_id for item in findings],
        report=report,
        summary=f"PRE-SOLVE analysed {len(report['components'])} components.",
    )
    return result, findings


def test_suite_stage_result(
    project: Mapping[str, Any],
    *,
    returncode: int | None,
    output: str = "",
    skipped: bool = False,
) -> tuple[StageResult, list[Finding]]:
    """Record the GUI's repository-test run as the TEST workflow stage."""
    canonical = _mapping(project, "project")
    if skipped:
        status, execution = "not_run", "SKIPPED"
        errors: list[str] = []
    elif type(returncode) is not int:
        raise ValueError("returncode must be an integer unless tests were skipped")
    elif returncode == 0:
        status, execution = "completed", "PASS"
        errors = []
    else:
        status, execution = "failed", "FAIL"
        errors = ["Repository unittest suite failed; inspect captured test output."]
    lines = output.splitlines() if isinstance(output, str) else None
    if lines is None:
        raise ValueError("output must be a string")
    ran = next((line.strip() for line in reversed(lines) if line.strip().startswith("Ran ")), None)
    summary_line = next((line.strip() for line in reversed(lines)
                         if line.strip() in {"OK", "FAILED (failures=1)", "FAILED (errors=1)"}), None)
    findings = _findings("TEST.repository", "tests.unittest", [
        ("repository_tests_failed", "error", errors),
    ])
    result = StageResult(
        stage="TEST.repository",
        status=status,
        module="tests.unittest",
        input_project_sha256=project_sha256(canonical),
        output_project_sha256=project_sha256(canonical),
        metrics={"returncode": returncode, "tests_run": ran, "summary": summary_line},
        finding_ids=[item.finding_id for item in findings],
        report={
            "status": execution,
            "returncode": returncode,
            "skipped": skipped,
            "output_tail": "\\n".join(lines[-80:]),
        },
        summary=("Repository tests skipped in standalone build." if skipped else
                 f"Repository tests {execution}."),
        extra={"workflow_stage": "TEST"},
    )
    return result, findings


def quick_fit_stage_result(
    project: Mapping[str, Any], output: Mapping[str, Any],
) -> tuple[StageResult, list[Finding]]:
    """Adapt solve.quick_fit.quick_fit output."""
    data = _mapping(output, "quick_fit output")
    if not isinstance(data.get("project"), Mapping):
        raise ValueError("quick_fit output.project must be an object")
    errors = _messages(data.get("errors", []), "quick_fit.errors")
    warnings = _messages(data.get("warnings", []), "quick_fit.warnings")
    report = data.get("report", {})
    if not isinstance(report, Mapping):
        raise ValueError("quick_fit.report must be an object")
    details = {"status": data.get("status"), "report": deepcopy(dict(report))}
    metrics = {
        "placed": data.get("placed", 0), "excluded": data.get("excluded", 0),
        "errors": len(errors), "warnings": len(warnings),
    }
    return _result(
        stage="SOLVE.quick_fit", module="solve.quick_fit",
        source_project=project, output_project=data["project"],
        report={"result": data, "details": details},
        errors=errors, warnings=warnings, metrics=metrics,
        options={"clearance_requested": report.get("clearance_requested")},
        summary=f"Quick Fit {data.get('status')}: {metrics['placed']} placed, {len(errors)} error(s).",
    )


def quick_place_stage_result(
    project: Mapping[str, Any], output: Mapping[str, Any],
) -> tuple[StageResult, list[Finding]]:
    """Adapt solve.quick_place.quick_place output."""
    data = _mapping(output, "quick_place output")
    if not isinstance(data.get("project"), Mapping):
        raise ValueError("quick_place output.project must be an object")
    errors = _messages(data.get("errors", []), "quick_place.errors")
    warnings = _messages(data.get("warnings", []), "quick_place.warnings")
    metrics = {
        "placed": data.get("placed", 0), "excluded": data.get("excluded", 0),
        "errors": len(errors), "warnings": len(warnings),
    }
    return _result(
        stage="SOLVE.quick_place", module="solve.quick_place",
        source_project=project, output_project=data["project"],
        report={"result": data, "status": data.get("status")},
        errors=errors, warnings=warnings, metrics=metrics,
        summary=f"Quick Place {data.get('status')}: {metrics['placed']} placed, {len(errors)} error(s).",
    )


def route_stage_result(
    project: Mapping[str, Any], output: Mapping[str, Any],
) -> tuple[StageResult, list[Finding]]:
    """Adapt solve.route.route_copper output, retaining nested verification."""
    data = _mapping(output, "route output")
    if not isinstance(data.get("project"), Mapping):
        raise ValueError("route output.project must be an object")
    errors = _messages(data.get("errors", []), "route.errors")
    warnings = _messages(data.get("warnings", []), "route.warnings")
    verification = data.get("verification")
    if verification is not None and not isinstance(verification, Mapping):
        raise ValueError("route.verification must be an object or null")
    metrics = {
        "cuts_added": data.get("cuts_added", 0),
        "wires_added": data.get("wires_added", 0),
        "errors": len(errors), "warnings": len(warnings),
    }
    return _result(
        stage="SOLVE.route", module="solve.route",
        source_project=project, output_project=data["project"],
        report={"result": data, "verification": deepcopy(verification)},
        errors=errors, warnings=warnings, metrics=metrics,
        summary=f"Routing {data.get('status')}: {metrics['cuts_added']} cuts and {metrics['wires_added']} wires added.",
    )


def verification_stage_result(
    project: Mapping[str, Any], report: Mapping[str, Any],
) -> tuple[StageResult, list[Finding]]:
    """Adapt independent verify_project output without changing the project."""
    data = _mapping(report, "verification report")
    status = data.get("status")
    if status not in {"PASS", "FAIL"}:
        raise ValueError("verification report status must be PASS or FAIL")
    errors = _messages(data.get("errors", []), "verification.errors")
    warnings = _messages(data.get("warnings", []), "verification.warnings")
    counts = data.get("counts", {})
    if not isinstance(counts, Mapping):
        raise ValueError("verification.counts must be an object")
    metrics = {**deepcopy(dict(counts)), "errors": len(errors), "warnings": len(warnings)}
    result, findings = _result(
        stage="VERIFY.independent", module="solve.verify",
        source_project=project, output_project=project,
        report=data, errors=errors, warnings=warnings, metrics=metrics,
        summary=f"Independent verification {status}: {len(errors)} error(s), {len(warnings)} warning(s).",
    )
    return result, findings


__all__ = [
    "collector_stage_result", "electrical_sanity_stage_result", "presolve_stage_result",
    "test_suite_stage_result",
    "quick_fit_stage_result", "quick_place_stage_result",
    "route_stage_result", "verification_stage_result",
]
