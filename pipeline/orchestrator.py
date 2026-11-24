"""Run-state lifecycle and sidecar persistence for the shared pipeline.

This module records existing stage outputs. It does not execute, reorder, or
change collector, sanity, placement, routing, or verification algorithms.
"""
from __future__ import annotations

import json
from pathlib import Path
import uuid
from typing import Any, Mapping

from .contracts import Finding, PipelineContext, StageResult, project_sha256


def sidecar_path(project_path: str | Path) -> Path:
    """Return the run-state sidecar path associated with a project file."""
    path = Path(project_path)
    return path.with_name(f"{path.stem}.routemate-state.json")


class PipelineRun:
    """Own one PipelineContext and persist it beside its canonical project."""

    def __init__(
        self,
        context: PipelineContext,
        state_path: str | Path | None = None,
    ) -> None:
        if not isinstance(context, PipelineContext):
            raise TypeError("context must be a PipelineContext")
        self.context = context
        self.state_path = Path(state_path) if state_path is not None else sidecar_path(
            context.project_path
        )

    @classmethod
    def create(
        cls,
        project_path: str | Path,
        project: Mapping[str, Any],
        *,
        sources: list[dict[str, Any]] | None = None,
        state_path: str | Path | None = None,
        run_id: str | None = None,
    ) -> "PipelineRun":
        """Create a new run for the supplied canonical project snapshot."""
        if not isinstance(project, Mapping):
            raise ValueError("project must be an object")
        path = str(Path(project_path))
        context = PipelineContext(
            run_id=run_id or uuid.uuid4().hex,
            project_path=path,
            project_sha256=project_sha256(dict(project)),
            sources=[] if sources is None else sources,
        )
        return cls(context, state_path)

    @classmethod
    def load(cls, state_path: str | Path) -> "PipelineRun":
        """Load and validate an existing run-state sidecar."""
        path = Path(state_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"could not read pipeline state {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("pipeline state root must be an object")
        return cls(PipelineContext.from_dict(data), path)

    def handoff(self, project: Mapping[str, Any], consumer: str) -> dict[str, Any]:
        """Return a validated, immutable-by-convention input package for the next module.

        The canonical project remains owned by the caller. The handoff contains a
        deep JSON copy plus all unresolved findings so downstream modules and the
        GUI can see exactly which snapshot and outstanding issues they received.
        """
        from copy import deepcopy

        if not isinstance(consumer, str) or not consumer.strip():
            raise ValueError("consumer must be a non-empty module name")
        snapshot = deepcopy(dict(project))
        actual_hash = project_sha256(snapshot)
        if actual_hash != self.context.project_sha256:
            raise ValueError(
                "stale pipeline handoff: project hash does not match the latest "
                f"recorded output ({actual_hash} != {self.context.project_sha256})"
            )
        outstanding = [
            item.to_dict() for item in self.context.findings
            if item.status in {"open", "acknowledged"}
        ]
        return {
            "run_id": self.context.run_id,
            "from_stage": self.context.current_stage,
            "to_module": consumer,
            "project": snapshot,
            "project_sha256": actual_hash,
            "findings": outstanding,
            "finding_ids": [item["finding_id"] for item in outstanding],
        }

    def record_stage(
        self,
        result: StageResult,
        findings: list[Finding] | None = None,
        *,
        save: bool = True,
    ) -> None:
        """Validate the input snapshot, record the result, and persist the run."""
        if result.input_project_sha256 is not None:
            if result.input_project_sha256 != self.context.project_sha256:
                raise ValueError(
                    f"{result.stage}: stale stage input; expected project hash "
                    f"{self.context.project_sha256}, got {result.input_project_sha256}"
                )
        workflow_stage = {
            "IN.project_import": "COLLECT",
            "IN.collect": "COLLECT",
            "PREPARE.electrical": "TEST",
            "PREPARE.presolve": "TEST",
            "TEST.repository": "TEST",
            "PREPARE.constraints": "TEST",
            "SOLVE.quick_fit": "QUICKSOLVE",
            "SOLVE.quick_place": "QUICKSOLVE",
            "SOLVE.route": "SOLVE",
            "VERIFY.independent": "SOLVE",
        }.get(result.stage)
        if workflow_stage:
            result.extra.setdefault("workflow_stage", workflow_stage)
        self.context.record_stage(result, findings)
        if result.output_project_sha256 is not None:
            self.context.project_sha256 = result.output_project_sha256
        if save:
            self.save()

    def save(self) -> Path:
        """Atomically replace the sidecar with the complete current run state."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_name(self.state_path.name + ".tmp")
        payload = json.dumps(
            self.context.to_dict(),
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(self.state_path)
        return self.state_path


__all__ = ["PipelineRun", "sidecar_path"]
