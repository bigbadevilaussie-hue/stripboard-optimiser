"""Shared, serializable contracts for Route-Mate pipeline hand-offs.

The canonical project remains a separate dictionary/file. These records carry
run provenance, stage reports and findings without modifying source project JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping


RUN_STATE_SCHEMA = "route-mate-run-state"
RUN_STATE_SCHEMA_VERSION = 1

STAGE_STATUSES = frozenset({
    "not_run", "running", "completed", "failed", "blocked", "stale",
})
FINDING_SEVERITIES = frozenset({"info", "warning", "error", "blocker"})
FINDING_STATUSES = frozenset({
    "open", "acknowledged", "resolved", "superseded",
})


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return dict(value)


def _string(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{name} must be an array of non-empty strings")
    return list(value)


def _json_copy(value: Any, name: str) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain JSON-compatible values") from exc


def project_sha256(project: Any) -> str:
    """Return a deterministic SHA-256 for a JSON-compatible project value."""
    try:
        encoded = json.dumps(
            project, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("project must be JSON-compatible") from exc
    return hashlib.sha256(encoded).hexdigest()


def make_finding_id(
    producer_stage: str,
    code: str,
    subjects: list[Mapping[str, Any]] | None = None,
    location: Mapping[str, Any] | None = None,
) -> str:
    """Build a repeatable ID from a finding's stable identity, not its wording."""
    stage = _string(producer_stage, "producer_stage")
    finding_code = _string(code, "code")
    stable_subjects = sorted(
        (_json_copy(dict(item), "subject") for item in (subjects or [])),
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
    )
    identity = {
        "stage": stage,
        "code": finding_code,
        "subjects": stable_subjects,
        "location": _json_copy(dict(location), "location") if location is not None else None,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return f"{stage}:{finding_code}:{digest}"


@dataclass(slots=True)
class Finding:
    """A durable, attributable observation made by a pipeline module."""

    finding_id: str
    code: str
    severity: str
    status: str
    message: str
    producer: dict[str, Any]
    subjects: list[dict[str, Any]] = field(default_factory=list)
    location: dict[str, Any] | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    resolution: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _string(self.finding_id, "finding_id")
        _string(self.code, "code")
        if not isinstance(self.severity, str) or self.severity not in FINDING_SEVERITIES:
            raise ValueError(f"unsupported finding severity: {self.severity!r}")
        if not isinstance(self.status, str) or self.status not in FINDING_STATUSES:
            raise ValueError(f"unsupported finding status: {self.status!r}")
        _string(self.message, "message", allow_empty=True)
        self.producer = _object(self.producer, "producer")
        if not isinstance(self.subjects, list):
            raise ValueError("subjects must be an array")
        self.subjects = [_object(item, "subject") for item in self.subjects]
        self.location = None if self.location is None else _object(self.location, "location")
        self.evidence = _object(self.evidence, "evidence")
        self.resolution = None if self.resolution is None else _object(self.resolution, "resolution")
        self.extra = _object(self.extra, "extra")
        _json_copy(self.to_dict(), "finding")

    def to_dict(self) -> dict[str, Any]:
        result = dict(self.extra)
        result.update({
            "finding_id": self.finding_id,
            "code": self.code,
            "severity": self.severity,
            "status": self.status,
            "message": self.message,
            "producer": _json_copy(self.producer, "producer"),
            "subjects": _json_copy(self.subjects, "subjects"),
            "location": _json_copy(self.location, "location"),
            "evidence": _json_copy(self.evidence, "evidence"),
            "resolution": _json_copy(self.resolution, "resolution"),
        })
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Finding":
        raw = _object(data, "finding")
        known = {
            "finding_id", "code", "severity", "status", "message", "producer",
            "subjects", "location", "evidence", "resolution",
        }
        return cls(
            finding_id=raw.get("finding_id"),
            code=raw.get("code"),
            severity=raw.get("severity"),
            status=raw.get("status"),
            message=raw.get("message"),
            producer=raw.get("producer", {}),
            subjects=raw.get("subjects", []),
            location=raw.get("location"),
            evidence=raw.get("evidence", {}),
            resolution=raw.get("resolution"),
            extra={key: value for key, value in raw.items() if key not in known},
        )


@dataclass(slots=True)
class StageResult:
    """Execution record and report for one named pipeline stage."""

    stage: str
    status: str
    module: str
    input_project_sha256: str | None = None
    output_project_sha256: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    finding_ids: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    report: dict[str, Any] | None = None
    summary: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _string(self.stage, "stage")
        _string(self.module, "module")
        if not isinstance(self.status, str) or self.status not in STAGE_STATUSES:
            raise ValueError(f"unsupported stage status: {self.status!r}")
        for name in ("input_project_sha256", "output_project_sha256"):
            value = getattr(self, name)
            if value is not None:
                _string(value, name)
        self.options = _object(self.options, "options")
        self.metrics = _object(self.metrics, "metrics")
        self.finding_ids = _string_list(self.finding_ids, "finding_ids")
        if not isinstance(self.artifacts, list):
            raise ValueError("artifacts must be an array")
        self.artifacts = [_object(item, "artifact") for item in self.artifacts]
        self.report = None if self.report is None else _object(self.report, "report")
        for name in ("summary", "started_at", "completed_at"):
            value = getattr(self, name)
            if value is not None:
                _string(value, name, allow_empty=(name == "summary"))
        self.extra = _object(self.extra, "extra")
        _json_copy(self.to_dict(), "stage result")

    def to_dict(self) -> dict[str, Any]:
        result = dict(self.extra)
        result.update({
            "stage": self.stage,
            "status": self.status,
            "module": self.module,
            "input_project_sha256": self.input_project_sha256,
            "output_project_sha256": self.output_project_sha256,
            "options": _json_copy(self.options, "options"),
            "metrics": _json_copy(self.metrics, "metrics"),
            "finding_ids": list(self.finding_ids),
            "artifacts": _json_copy(self.artifacts, "artifacts"),
            "report": _json_copy(self.report, "report"),
            "summary": self.summary,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        })
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StageResult":
        raw = _object(data, "stage result")
        known = {
            "stage", "status", "module", "input_project_sha256",
            "output_project_sha256", "options", "metrics", "finding_ids",
            "artifacts", "report", "summary", "started_at", "completed_at",
        }
        return cls(
            stage=raw.get("stage"),
            status=raw.get("status"),
            module=raw.get("module"),
            input_project_sha256=raw.get("input_project_sha256"),
            output_project_sha256=raw.get("output_project_sha256"),
            options=raw.get("options", {}),
            metrics=raw.get("metrics", {}),
            finding_ids=raw.get("finding_ids", []),
            artifacts=raw.get("artifacts", []),
            report=raw.get("report"),
            summary=raw.get("summary"),
            started_at=raw.get("started_at"),
            completed_at=raw.get("completed_at"),
            extra={key: value for key, value in raw.items() if key not in known},
        )


@dataclass(slots=True)
class PipelineContext:
    """Run-level hand-off state; deliberately separate from the canonical project."""

    run_id: str
    project_path: str
    project_sha256: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    current_stage: str | None = None
    stages: dict[str, StageResult] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    project_extra: dict[str, Any] = field(default_factory=dict)
    pipeline_extra: dict[str, Any] = field(default_factory=dict)
    schema: str = RUN_STATE_SCHEMA
    schema_version: int = RUN_STATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _string(self.run_id, "run_id")
        _string(self.project_path, "project_path")
        _string(self.project_sha256, "project_sha256")
        if self.schema != RUN_STATE_SCHEMA:
            raise ValueError(f"unsupported run-state schema: {self.schema!r}")
        if type(self.schema_version) is not int or self.schema_version != RUN_STATE_SCHEMA_VERSION:
            raise ValueError(f"unsupported run-state schema version: {self.schema_version!r}")
        if self.current_stage is not None:
            _string(self.current_stage, "current_stage")
        if not isinstance(self.sources, list):
            raise ValueError("sources must be an array")
        self.sources = [_object(item, "source") for item in self.sources]
        if not isinstance(self.stages, dict):
            raise ValueError("stages must be an object")
        self.stages = {
            _string(key, "stage key"): (
                value if isinstance(value, StageResult) else StageResult.from_dict(value)
            )
            for key, value in self.stages.items()
        }
        if not isinstance(self.findings, list):
            raise ValueError("findings must be an array")
        self.findings = [
            value if isinstance(value, Finding) else Finding.from_dict(value)
            for value in self.findings
        ]
        if not isinstance(self.artifacts, list):
            raise ValueError("artifacts must be an array")
        self.artifacts = [_object(item, "artifact") for item in self.artifacts]
        self.extra = _object(self.extra, "extra")
        self.project_extra = _object(self.project_extra, "project_extra")
        self.pipeline_extra = _object(self.pipeline_extra, "pipeline_extra")
        self._validate_finding_ids()
        _json_copy(self.to_dict(), "pipeline context")

    def _validate_finding_ids(self) -> None:
        seen: dict[str, Finding] = {}
        for finding in self.findings:
            previous = seen.get(finding.finding_id)
            if previous is not None and previous.to_dict() != finding.to_dict():
                raise ValueError(f"conflicting duplicate finding ID {finding.finding_id!r}")
            seen[finding.finding_id] = finding

    def add_findings(self, findings: list[Finding]) -> None:
        """Append new findings without deleting or silently replacing old ones."""
        existing = {item.finding_id: item for item in self.findings}
        additions: list[Finding] = []
        for finding in findings:
            if not isinstance(finding, Finding):
                raise TypeError("add_findings accepts Finding records")
            previous = existing.get(finding.finding_id)
            if previous is not None:
                if previous.to_dict() != finding.to_dict():
                    raise ValueError(f"conflicting duplicate finding ID {finding.finding_id!r}")
                continue
            existing[finding.finding_id] = finding
            additions.append(finding)
        self.findings.extend(additions)

    def record_stage(
        self, result: StageResult, findings: list[Finding] | None = None
    ) -> None:
        """Store a stage result and its findings as one validated hand-off."""
        if not isinstance(result, StageResult):
            raise TypeError("result must be a StageResult")
        incoming = findings or []
        existing = {item.finding_id: item for item in self.findings}
        for finding in incoming:
            if not isinstance(finding, Finding):
                raise TypeError("findings must contain Finding records")
            previous = existing.get(finding.finding_id)
            if previous is not None and previous.to_dict() != finding.to_dict():
                raise ValueError(f"conflicting duplicate finding ID {finding.finding_id!r}")
            existing[finding.finding_id] = finding
        missing = sorted(set(result.finding_ids) - set(existing))
        if missing:
            raise ValueError(f"stage references unknown finding IDs: {', '.join(missing)}")
        self.add_findings(incoming)
        self.stages[result.stage] = result
        self.current_stage = result.stage

    def to_dict(self) -> dict[str, Any]:
        project = dict(self.project_extra)
        project.update({"path": self.project_path, "sha256": self.project_sha256})
        pipeline = dict(self.pipeline_extra)
        pipeline.update({
            "current_stage": self.current_stage,
            "stages": {key: value.to_dict() for key, value in self.stages.items()},
            "findings": [item.to_dict() for item in self.findings],
            "artifacts": _json_copy(self.artifacts, "artifacts"),
        })
        result = dict(self.extra)
        result.update({
            "schema": self.schema,
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "project": project,
            "sources": _json_copy(self.sources, "sources"),
            "pipeline": pipeline,
        })
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PipelineContext":
        raw = _object(data, "pipeline context")
        project = _object(raw.get("project"), "project")
        pipeline = _object(raw.get("pipeline"), "pipeline")
        known_top = {"schema", "schema_version", "run_id", "project", "sources", "pipeline"}
        known_pipeline = {"current_stage", "stages", "findings", "artifacts"}
        pipeline_extra = {key: value for key, value in pipeline.items() if key not in known_pipeline}
        project_extra = {key: value for key, value in project.items()
                         if key not in {"path", "sha256"}}
        top_extra = {key: value for key, value in raw.items() if key not in known_top}
        return cls(
            run_id=raw.get("run_id"),
            project_path=project.get("path"),
            project_sha256=project.get("sha256"),
            sources=raw.get("sources", []),
            current_stage=pipeline.get("current_stage"),
            stages=pipeline.get("stages", {}),
            findings=pipeline.get("findings", []),
            artifacts=pipeline.get("artifacts", []),
            extra=top_extra,
            project_extra=project_extra,
            pipeline_extra=pipeline_extra,
            schema=raw.get("schema", RUN_STATE_SCHEMA),
            schema_version=raw.get("schema_version", RUN_STATE_SCHEMA_VERSION),
        )


__all__ = [
    "FINDING_SEVERITIES", "FINDING_STATUSES", "RUN_STATE_SCHEMA",
    "RUN_STATE_SCHEMA_VERSION", "STAGE_STATUSES", "Finding",
    "PipelineContext", "StageResult", "make_finding_id", "project_sha256",
]
