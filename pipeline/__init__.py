"""Route-Mate pipeline contracts, adapters, and run-state orchestration."""

from .adapters import (
    collector_stage_result,
    electrical_sanity_stage_result,
    project_import_stage_result,
    presolve_stage_result,
    quick_fit_stage_result,
    quick_place_stage_result,
    route_stage_result,
    test_suite_stage_result,
    verification_stage_result,
)
from .contracts import (
    Finding,
    PipelineContext,
    StageResult,
    make_finding_id,
    project_sha256,
)
from .orchestrator import PipelineRun, sidecar_path

__all__ = [
    "Finding", "PipelineContext", "PipelineRun", "StageResult",
    "collector_stage_result", "electrical_sanity_stage_result",
    "project_import_stage_result", "presolve_stage_result",
    "quick_fit_stage_result", "quick_place_stage_result",
    "route_stage_result", "test_suite_stage_result", "verification_stage_result",
    "make_finding_id", "project_sha256", "sidecar_path",
]
