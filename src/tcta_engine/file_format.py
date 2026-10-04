"""file_format.py -- parse/serialize the `.tcta` reference block
representation, tcta_file_format_v1.md's "Reference representation (v1)"
section (through the v1.2 COMPLIANCE/ALGORITHM_SELECT addition).

This targets `.tcta`'s specific block grammar only -- GOAL/ENGINE/
PARAMETERS/CONSUMPTION_POINTS/SPREAD/ALGORITHM_SELECT/COMPLIANCE, each
with its own line shape. It is not a generalized `.bonit`/`.ork` parser:
those files use the same family of block syntax but with materially
different per-block grammars (`.bonit`'s WORKFLOW's "STEP N actor : ACTION"
lines, `.ork`'s nested POSITION.PATH array of objects) that this module
does not attempt to cover. A shared general-purpose parser for the whole
block-syntax family, if wanted, is separate future work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Dataclasses mirroring the reference representation's blocks
# ---------------------------------------------------------------------------


@dataclass
class Goal:
    desired_sr: Optional[str] = None
    source: Optional[str] = None  # "stated" | "inferred" | None


@dataclass
class Engine:
    gamma_ref: Optional[str] = None
    psi_ref: Optional[str] = None
    phi_ref: Optional[str] = None


@dataclass
class Parameters:
    eta: Optional[float] = None
    lambda_rec: Optional[float] = None
    alpha: Optional[float] = None
    epsilon: Optional[float] = None
    prefix_k: Optional[int] = None
    spread_low: Optional[float] = None
    spread_high: Optional[float] = None


@dataclass
class ConsumptionPoint:
    source: Optional[str] = None
    defined: Optional[bool] = None
    status: str = "not_yet_wired"


@dataclass
class ConsumptionPoints:
    domain_prune: ConsumptionPoint = field(default_factory=ConsumptionPoint)
    competency_prune: ConsumptionPoint = field(default_factory=ConsumptionPoint)
    inverse_transform: ConsumptionPoint = field(default_factory=ConsumptionPoint)
    trajectory_narrowing: ConsumptionPoint = field(default_factory=ConsumptionPoint)


@dataclass
class Spread:
    value: Optional[float] = None
    epsilon_check: Optional[float] = None


@dataclass
class AlgorithmSelect:
    result: Optional[str] = None  # "HDRP_LOCALIZED" | "UNRESOLVED" | None
    reason: Optional[str] = None


@dataclass
class TctaFile:
    name: str
    applies_to: str
    goal: Goal = field(default_factory=Goal)
    engine: Engine = field(default_factory=Engine)
    parameters: Parameters = field(default_factory=Parameters)
    consumption_points: ConsumptionPoints = field(default_factory=ConsumptionPoints)
    spread: Spread = field(default_factory=Spread)
    algorithm_select: AlgorithmSelect = field(default_factory=AlgorithmSelect)
    compliance: List[str] = field(default_factory=list)  # e.g. ["ALGORITHM_SUBSTITUTED", ...]


class TctaParseError(ValueError):
    """Raised on malformed `.tcta` content. Never repaired silently."""


# ---------------------------------------------------------------------------
# Tokenizing helpers
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r'"[^"]*"|\S+')


def _strip_comment(line: str) -> str:
    """Strips a trailing `# ...` comment, respecting quoted strings (a `#`
    inside quotes is not a comment marker)."""
    in_quotes = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "#" and not in_quotes:
            return line[:i]
    return line


def _tokenize(line: str) -> List[str]:
    return _TOKEN_RE.findall(line)


def _parse_scalar(token: str):
    """quoted string -> str (unquoted); `null` -> None; `true`/`false` ->
    bool; int/float literal -> number; anything else -> str as-is."""
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    if token == "null":
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


def _split_top_level_blocks(lines: List[str]) -> dict:
    """Splits header lines from named `BLOCK { ... }` bodies by brace
    depth. Returns {"_header": [...], "GOAL": [...], "ENGINE": [...], ...}.
    """
    blocks: dict = {"_header": []}
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        tokens = _tokenize(stripped)
        if len(tokens) >= 2 and tokens[1] == "{":
            name = tokens[0]
            depth = 1
            body: List[str] = []
            i += 1
            while i < n and depth > 0:
                inner = lines[i]
                inner_stripped = inner.strip()
                depth += inner_stripped.count("{") - inner_stripped.count("}")
                if depth > 0:
                    body.append(inner)
                i += 1
            blocks[name] = body
            continue
        blocks["_header"].append(stripped)
        i += 1
    return blocks


def _kv_lines(body: List[str]) -> List[List[str]]:
    """Each non-empty body line, tokenized. Used by blocks whose lines are
    `KEY value [more tokens...]`."""
    out = []
    for line in body:
        stripped = line.strip()
        if not stripped:
            continue
        out.append(_tokenize(stripped))
    return out


# ---------------------------------------------------------------------------
# Per-block parsers
# ---------------------------------------------------------------------------


def _parse_goal(body: List[str]) -> Goal:
    goal = Goal()
    for tokens in _kv_lines(body):
        key, value = tokens[0], _parse_scalar(tokens[1]) if len(tokens) > 1 else None
        if key == "DESIRED_SR":
            goal.desired_sr = value
        elif key == "SOURCE":
            goal.source = value
    return goal


def _parse_engine(body: List[str]) -> Engine:
    engine = Engine()
    for tokens in _kv_lines(body):
        key, value = tokens[0], _parse_scalar(tokens[1]) if len(tokens) > 1 else None
        if key == "GAMMA_REF":
            engine.gamma_ref = value
        elif key == "PSI_REF":
            engine.psi_ref = value
        elif key == "PHI_REF":
            engine.phi_ref = value
    return engine


_PARAM_FIELD_MAP = {
    "ETA": "eta",
    "LAMBDA_REC": "lambda_rec",
    "ALPHA": "alpha",
    "EPSILON": "epsilon",
    "PREFIX_K": "prefix_k",
    "SPREAD_LOW": "spread_low",
    "SPREAD_HIGH": "spread_high",
}


def _parse_parameters(body: List[str]) -> Parameters:
    params = Parameters()
    for tokens in _kv_lines(body):
        key = tokens[0]
        value = _parse_scalar(tokens[1]) if len(tokens) > 1 else None
        field_name = _PARAM_FIELD_MAP.get(key)
        if field_name:
            setattr(params, field_name, value)
    return params


_CONSUMPTION_POINT_MAP = {
    "DOMAIN_PRUNE": "domain_prune",
    "COMPETENCY_PRUNE": "competency_prune",
    "INVERSE_TRANSFORM": "inverse_transform",
    "TRAJECTORY_NARROWING": "trajectory_narrowing",
}


def _parse_consumption_points(body: List[str]) -> ConsumptionPoints:
    points = ConsumptionPoints()
    for tokens in _kv_lines(body):
        point_name = tokens[0]
        field_name = _CONSUMPTION_POINT_MAP.get(point_name)
        if not field_name:
            raise TctaParseError(
                f"unknown CONSUMPTION_POINTS entry {point_name!r}; expected "
                f"one of {sorted(_CONSUMPTION_POINT_MAP)}"
            )
        cp = ConsumptionPoint()
        rest = tokens[1:]
        for j in range(0, len(rest) - 1, 2):
            field_key, raw_value = rest[j], rest[j + 1]
            value = _parse_scalar(raw_value)
            if field_key == "SOURCE":
                cp.source = value
            elif field_key == "DEFINED":
                cp.defined = value
            elif field_key == "STATUS":
                cp.status = value
        setattr(points, field_name, cp)
    return points


def _parse_spread(body: List[str]) -> Spread:
    spread = Spread()
    for tokens in _kv_lines(body):
        key, value = tokens[0], _parse_scalar(tokens[1]) if len(tokens) > 1 else None
        if key == "VALUE":
            spread.value = value
        elif key == "EPSILON_CHECK":
            spread.epsilon_check = value
    return spread


def _parse_algorithm_select(body: List[str]) -> AlgorithmSelect:
    sel = AlgorithmSelect()
    for tokens in _kv_lines(body):
        key, value = tokens[0], _parse_scalar(tokens[1]) if len(tokens) > 1 else None
        if key == "RESULT":
            sel.result = value
        elif key == "REASON":
            sel.reason = value
    return sel


def _parse_compliance(body: List[str]) -> List[str]:
    rules = []
    for tokens in _kv_lines(body):
        if len(tokens) >= 3 and tokens[0] == "REJECT" and tokens[1] == "IF":
            rules.append(tokens[2])
        elif len(tokens) >= 3 and tokens[0] == "REVISE" and tokens[1] == "IF":
            rules.append(f"REVISE:{tokens[2]}")
    return rules


# ---------------------------------------------------------------------------
# Public parse / serialize
# ---------------------------------------------------------------------------


def parse_tcta(text: str) -> TctaFile:
    """Parses `.tcta` reference-representation text into a `TctaFile`.
    Raises TctaParseError on anything the grammar doesn't recognize --
    never guesses or repairs silently."""
    raw_lines = text.splitlines()
    lines = [_strip_comment(line) for line in raw_lines]
    blocks = _split_top_level_blocks(lines)

    header = blocks.pop("_header")
    name = None
    applies_to = None
    version_seen = False
    for stripped in header:
        tokens = _tokenize(stripped)
        if not tokens:
            continue
        if tokens[0] == "TCTA/1.0":
            version_seen = True
            continue
        if tokens[0] == "NAME" and len(tokens) > 1:
            name = _parse_scalar(tokens[1])
        elif tokens[0] == "APPLIES_TO" and len(tokens) > 1:
            applies_to = _parse_scalar(tokens[1])

    if not version_seen:
        raise TctaParseError("missing TCTA/1.0 header line")
    if name is None:
        raise TctaParseError("missing NAME")
    if applies_to is None:
        raise TctaParseError("missing APPLIES_TO")

    tcta = TctaFile(name=name, applies_to=applies_to)
    if "GOAL" in blocks:
        tcta.goal = _parse_goal(blocks["GOAL"])
    if "ENGINE" in blocks:
        tcta.engine = _parse_engine(blocks["ENGINE"])
    if "PARAMETERS" in blocks:
        tcta.parameters = _parse_parameters(blocks["PARAMETERS"])
    if "CONSUMPTION_POINTS" in blocks:
        tcta.consumption_points = _parse_consumption_points(blocks["CONSUMPTION_POINTS"])
    if "SPREAD" in blocks:
        tcta.spread = _parse_spread(blocks["SPREAD"])
    if "ALGORITHM_SELECT" in blocks:
        tcta.algorithm_select = _parse_algorithm_select(blocks["ALGORITHM_SELECT"])
    if "COMPLIANCE" in blocks:
        tcta.compliance = _parse_compliance(blocks["COMPLIANCE"])
    return tcta


def _fmt(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def serialize_tcta(tcta: TctaFile) -> str:
    """Serializes a `TctaFile` back to `.tcta` reference-representation
    text. `parse_tcta(serialize_tcta(x))` round-trips for any `TctaFile`
    this module produced."""
    lines = [
        "TCTA/1.0",
        f"NAME {tcta.name}",
        f'APPLIES_TO "{tcta.applies_to}"',
        "",
        "GOAL {",
        f"  DESIRED_SR {_fmt(tcta.goal.desired_sr)}",
        f"  SOURCE {_fmt(tcta.goal.source)}",
        "}",
        "",
        "ENGINE {",
        f"  GAMMA_REF {_fmt(tcta.engine.gamma_ref)}",
        f"  PSI_REF   {_fmt(tcta.engine.psi_ref)}",
        f"  PHI_REF   {_fmt(tcta.engine.phi_ref)}",
        "}",
        "",
        "PARAMETERS {",
        f"  ETA {_fmt(tcta.parameters.eta)}",
        f"  LAMBDA_REC {_fmt(tcta.parameters.lambda_rec)}",
        f"  ALPHA {_fmt(tcta.parameters.alpha)}",
        f"  EPSILON {_fmt(tcta.parameters.epsilon)}",
        f"  PREFIX_K {_fmt(tcta.parameters.prefix_k)}",
        f"  SPREAD_LOW {_fmt(tcta.parameters.spread_low)}",
        f"  SPREAD_HIGH {_fmt(tcta.parameters.spread_high)}",
        "}",
        "",
        "CONSUMPTION_POINTS {",
    ]
    cp = tcta.consumption_points
    for point_name, field_name in _CONSUMPTION_POINT_MAP.items():
        point: ConsumptionPoint = getattr(cp, field_name)
        parts = [point_name]
        if point.source is not None:
            parts.append(f"SOURCE {_fmt(point.source)}")
        if point.defined is not None:
            parts.append(f"DEFINED {_fmt(point.defined)}")
        parts.append(f"STATUS {_fmt(point.status)}")
        lines.append("  " + " ".join(parts))
    lines += [
        "}",
        "",
        "SPREAD {",
        f"  VALUE {_fmt(tcta.spread.value)}",
        f"  EPSILON_CHECK {_fmt(tcta.spread.epsilon_check)}",
        "}",
        "",
        "ALGORITHM_SELECT {",
        f"  RESULT {_fmt(tcta.algorithm_select.result)}",
        f"  REASON {_fmt(tcta.algorithm_select.reason)}",
        "}",
        "",
        "COMPLIANCE {",
    ]
    for rule in tcta.compliance:
        if rule.startswith("REVISE:"):
            lines.append(f"  REVISE IF {rule[len('REVISE:'):]}")
        else:
            lines.append(f"  REJECT IF {rule}")
    lines.append("}")
    return "\n".join(lines) + "\n"
