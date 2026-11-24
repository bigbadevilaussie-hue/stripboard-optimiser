"""Electrical integrity checks for Route-Mate's canonical project model.

This stage checks data integrity and, when supplied, independently compares the
JSON connectivity partition with a KiCad-format .net export. It does not infer
electrical behaviour or treat missing metadata as a fault.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any


_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+')


def _parse_sexpr(source: str) -> list[Any]:
    """Parse the small S-expression subset used by KiCad netlists."""
    tokens = _TOKEN.findall(source)
    pos = 0

    def parse_one() -> Any:
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("unexpected end of .net file")
        token = tokens[pos]
        pos += 1
        if token == "(":
            result = []
            while pos < len(tokens) and tokens[pos] != ")":
                result.append(parse_one())
            if pos >= len(tokens):
                raise ValueError("unclosed S-expression in .net file")
            pos += 1
            return result
        if token == ")":
            raise ValueError("unexpected ')' in .net file")
        if token.startswith('"'):
            return json.loads(token)
        return token

    forms = []
    while pos < len(tokens):
        forms.append(parse_one())
    return forms


def _walk(value: Any, tag: str):
    if isinstance(value, list):
        if value and value[0] == tag:
            yield value
        for child in value:
            yield from _walk(child, tag)


def _child(form: list[Any], tag: str) -> list[Any] | None:
    return next((item for item in form[1:] if isinstance(item, list)
                 and item and item[0] == tag), None)


def _netlist_partition(source: str, label_to_id: dict[str, str]) -> tuple[set[frozenset], list[str]]:
    errors: list[str] = []
    try:
        forms = _parse_sexpr(source)
    except (ValueError, json.JSONDecodeError) as exc:
        return set(), [f".net parse error: {exc}"]

    nets_form = next(_walk(forms, "nets"), None)
    if nets_form is None:
        return set(), [".net file has no (nets ...) section"]

    partition: set[frozenset] = set()
    seen_nodes: set[tuple[str, str]] = set()
    for net in (item for item in nets_form[1:] if isinstance(item, list)
                and item and item[0] == "net"):
        members = set()
        for node in (item for item in net[1:] if isinstance(item, list)
                     and item and item[0] == "node"):
            ref_form = _child(node, "ref")
            pin_form = _child(node, "pin")
            if not ref_form or len(ref_form) < 2 or not pin_form or len(pin_form) < 2:
                errors.append(".net node is missing ref or pin")
                continue
            ref, pin = str(ref_form[1]), str(pin_form[1])
            component_id = label_to_id.get(ref)
            if component_id is None:
                errors.append(f".net references unknown component label {ref!r}")
                continue
            endpoint = (component_id, pin)
            if endpoint in seen_nodes:
                errors.append(f".net assigns {ref} pin {pin} more than once")
            seen_nodes.add(endpoint)
            members.add(endpoint)
        if members:
            partition.add(frozenset(members))
    return partition, errors


def run_electrical_sanity(project: Any, netlist_text: str | None = None) -> dict[str, Any]:
    """Return a deterministic PASS/FAIL report for a collected project."""
    errors: list[str] = []
    warnings: list[str] = []
    counts = {"components": 0, "nets": 0, "assignments": 0}

    if not isinstance(project, dict):
        return {"status": "FAIL", "errors": ["project root must be an object"],
                "warnings": [], "counts": counts, "netlist_checked": netlist_text is not None}

    components = project.get("components")
    nets = project.get("nets")
    assignments = project.get("netAssignments")
    if not isinstance(components, list):
        errors.append("components must be an array")
        components = []
    if not isinstance(nets, list):
        errors.append("nets must be an array")
        nets = []
    if not isinstance(assignments, list):
        errors.append("netAssignments must be an array")
        assignments = []

    counts.update(components=len(components), nets=len(nets), assignments=len(assignments))
    for name, items in (("components", components), ("nets", nets),
                        ("netAssignments", assignments)):
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{name}[{index}] must be an object")

    components = [item for item in components if isinstance(item, dict)]
    nets = [item for item in nets if isinstance(item, dict)]
    assignments = [item for item in assignments if isinstance(item, dict)]

    component_ids = [str(c.get("id", "")) for c in components]
    net_ids = [str(n.get("id", "")) for n in nets]
    for label, values in (("component", component_ids), ("net", net_ids)):
        if "" in values:
            errors.append(f"{label} ID is missing")
        duplicates = sorted({value for value in values if value and values.count(value) > 1})
        for value in duplicates:
            errors.append(f"duplicate {label} ID {value!r}")

    component_by_id = {str(c.get("id")): c for c in components if c.get("id")}
    net_id_set = {str(n.get("id")) for n in nets if n.get("id")}
    raw_definitions = project.get("componentDefs") or []
    if not isinstance(raw_definitions, list):
        warnings.append("componentDefs is not an array; footprint pin inventories are unavailable")
        raw_definitions = []
    definitions = {
        str(d.get("id")): d for d in raw_definitions
        if isinstance(d, dict) and d.get("id")
    }
    assigned_pins: dict[tuple[str, str], str] = {}
    json_groups: dict[str, set[tuple[str, str]]] = defaultdict(set)

    for index, assignment in enumerate(assignments):
        component_id = str(assignment.get("componentId", ""))
        net_id = str(assignment.get("netId", ""))
        pin_id = str(assignment.get("pinId", ""))
        if component_id not in component_by_id:
            errors.append(f"netAssignments[{index}] references unknown component {component_id!r}")
            continue
        if net_id not in net_id_set:
            errors.append(f"netAssignments[{index}] references unknown net {net_id!r}")
            continue
        if not pin_id:
            errors.append(f"netAssignments[{index}] has no pinId")
            continue

        endpoint = (component_id, pin_id)
        previous_net = assigned_pins.get(endpoint)
        if previous_net is not None:
            if previous_net == net_id:
                errors.append(f"duplicate assignment for component {component_id!r} pin {pin_id!r}")
            else:
                errors.append(f"component {component_id!r} pin {pin_id!r} is assigned to multiple nets")
            continue
        assigned_pins[endpoint] = net_id
        json_groups[net_id].add(endpoint)

        component = component_by_id[component_id]
        override = component.get("footprintOverride")
        definition = definitions.get(str(component.get("defId") or component.get("componentDefId") or ""))
        pin_source = override if isinstance(override, dict) else definition
        if isinstance(pin_source, dict) and isinstance(pin_source.get("pins"), list):
            known_pins = {str(p.get("id")) for p in pin_source["pins"]
                          if isinstance(p, dict) and p.get("id") is not None}
            if pin_id not in known_pins:
                label = component.get("label") or component_id
                errors.append(f"{label}: assignment references unknown footprint pin {pin_id!r}")

    # Empty net records and singleton nets are retained: the source format does
    # not encode enough intent to decide whether either is an electrical fault.
    label_to_id: dict[str, str] = {}
    duplicate_labels: set[str] = set()
    for component in components:
        label = str(component.get("label") or component.get("name") or "")
        cid = str(component.get("id") or "")
        if not label:
            continue
        if label in label_to_id:
            duplicate_labels.add(label)
        else:
            label_to_id[label] = cid
    if netlist_text is not None:
        for label in sorted(duplicate_labels):
            errors.append(f"component label {label!r} is not unique; cannot map .net references")
        netlist_partition, netlist_errors = _netlist_partition(netlist_text, label_to_id)
        errors.extend(netlist_errors)
        json_partition = {frozenset(members) for members in json_groups.values() if members}
        if not netlist_errors and json_partition != netlist_partition:
            json_only = len(json_partition - netlist_partition)
            net_only = len(netlist_partition - json_partition)
            errors.append(
                f".net connectivity does not match JSON ({json_only} JSON-only groups, "
                f"{net_only} .net-only groups)"
            )

    return {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        "warnings": warnings,
        "counts": counts,
        "netlist_checked": netlist_text is not None,
    }
