"""Registry authority projection and parity verifier.

This module owns the seam between the source-controlled secret-free authority
(`config/agent-registry.toml`) and the private host runtime config
(`agents.toml`). It is intentionally small and does not import Coordinate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_ROOT_KEYS = {"registry", "agents", "external_agents"}
_REGISTRY_KEYS = {"id", "version"}
_ENTRY_KEYS = {"id", "display_name", "discord_user_id"}
_AGENT_KINDS = {"managed", "external"}


class AuthorityError(Exception):
    """The authority file violates the strict allow-list schema."""


@dataclass(frozen=True)
class AgentEntry:
    id: str
    display_name: str
    discord_user_id: str
    agent_type: str

    def to_canonical_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "discord_user_id": self.discord_user_id,
            "display_name": self.display_name,
            "agent_type": self.agent_type,
        }


@dataclass
class Authority:
    source_id: str
    source_version: int
    entries: list[AgentEntry]
    source_hash: str


@dataclass
class ParityResult:
    ok: bool
    authority: Authority | None = None
    authority_count: int = 0
    runtime_count: int = 0
    source_hash: str | None = None
    authority_hash: str | None = None
    diff: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "source_id": self.authority.source_id if self.authority else None,
            "source_version": self.authority.source_version if self.authority else None,
            "source_hash": self.source_hash,
            "authority_hash": self.authority_hash,
            "authority_count": self.authority_count,
            "runtime_count": self.runtime_count,
            "diff": self.diff,
            "errors": self.errors,
        }


def _is_ascii_decimal_positive(value: str) -> bool:
    return (
        bool(value)
        and value.isascii()
        and value.isdigit()
        and int(value) > 0
    )


def _validate_discord_user_id(value: Any, *, require_string: bool = False) -> str:
    """Normalize a Discord user id or raise ValueError.

    The authority always requires a quoted string. The runtime may supply an
    integer or a string, but the normalized canonical form is the same string.
    """
    if value is None:
        raise ValueError("missing discord_user_id")
    if require_string and not isinstance(value, str):
        raise ValueError("invalid discord_user_id: must be a quoted string")
    raw = str(value)
    if raw != raw.strip():
        raise ValueError("invalid discord_user_id: surrounding whitespace is not allowed")
    did = raw
    if not _is_ascii_decimal_positive(did):
        raise ValueError("invalid discord_user_id")
    return did


def _normalize_id(value: Any) -> str:
    if value is None:
        raise ValueError("missing 'id'")
    agent_id = str(value).strip()
    if not agent_id:
        raise ValueError("missing 'id'")
    return agent_id


def _normalize_display_name(value: Any, agent_id: str) -> str:
    display_name = str(value).strip() if value is not None else ""
    return display_name or agent_id


def canonical_hash(entries: list[AgentEntry]) -> str:
    """Deterministic SHA-256 of the normalized roster.

    Matches Coordinate v10's canonical contract exactly:
    id-sorted JSON list with keys id, discord_user_id, display_name, agent_type;
    sort_keys=True, separators=(',', ':'), ensure_ascii=False; UTF-8; SHA-256.
    """
    payload = [entry.to_canonical_dict() for entry in sorted(entries, key=lambda e: e.id)]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_toml(path: str | Path) -> dict[str, Any]:
    return tomllib.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def _authority_section_label(agent_type: str) -> str:
    return "agents" if agent_type == "managed" else "external_agents"


def load_authority(path: str | Path) -> Authority:
    """Load the canonical authority with a strict allow-list schema.

    Rejects unknown root, [registry] or entry keys (including every
    secret-bearing field) before any deploy or copy.
    """
    try:
        data = _load_toml(path)
    except Exception as exc:
        raise AuthorityError(f"cannot parse authority TOML: {exc}") from exc

    unknown_root = set(data.keys()) - _ROOT_KEYS
    if unknown_root:
        raise AuthorityError(f"unknown root keys: {sorted(unknown_root)}")

    registry = data.get("registry")
    if not isinstance(registry, dict):
        raise AuthorityError("missing [registry] metadata")
    unknown_registry = set(registry.keys()) - _REGISTRY_KEYS
    if unknown_registry:
        raise AuthorityError(f"unknown [registry] keys: {sorted(unknown_registry)}")

    source_id = str(registry.get("id", "")).strip()
    if not source_id:
        raise AuthorityError("[registry].id is required")

    version = registry.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise AuthorityError("[registry].version must be a non-negative integer")
    source_version = version

    entries: list[AgentEntry] = []
    seen_ids: dict[str, str] = {}
    seen_discord_ids: dict[str, str] = {}

    for agent_type in ("managed", "external"):
        section = _authority_section_label(agent_type)
        section_data = data.get(section)
        if section_data is None:
            continue
        if not isinstance(section_data, list):
            raise AuthorityError(f"{section} must be a list of tables")

        for raw in section_data:
            if not isinstance(raw, dict):
                raise AuthorityError(f"{section} entry must be a table")
            unknown = set(raw.keys()) - _ENTRY_KEYS
            if unknown:
                raise AuthorityError(f"unknown keys in {section} entry: {sorted(unknown)}")

            try:
                agent_id = _normalize_id(raw.get("id"))
            except ValueError as exc:
                raise AuthorityError(f"{section} entry: {exc}") from exc
            if agent_id in seen_ids:
                raise AuthorityError(
                    f"duplicate agent id '{agent_id}' in {seen_ids[agent_id]} and {section}"
                )
            seen_ids[agent_id] = section

            display_name = _normalize_display_name(raw.get("display_name"), agent_id)
            try:
                discord_user_id = _validate_discord_user_id(
                    raw.get("discord_user_id"), require_string=True
                )
            except ValueError as exc:
                raise AuthorityError(
                    f"{section} entry '{agent_id}': {exc}"
                ) from exc

            if discord_user_id in seen_discord_ids:
                raise AuthorityError(
                    f"duplicate discord_user_id '{discord_user_id}' in "
                    f"{seen_discord_ids[discord_user_id]} and {agent_id}"
                )
            seen_discord_ids[discord_user_id] = agent_id

            entries.append(AgentEntry(
                id=agent_id,
                display_name=display_name,
                discord_user_id=discord_user_id,
                agent_type=agent_type,
            ))

    source_hash = canonical_hash(entries)
    return Authority(
        source_id=source_id,
        source_version=source_version,
        entries=entries,
        source_hash=source_hash,
    )


def project_runtime_roster(path: str | Path) -> tuple[list[AgentEntry], list[str]]:
    """Project Coordinate's canonical fields from a private runtime TOML.

    Extra fields are ignored. Missing/invalid entries are reported as redacted
    errors rather than silently skipped.
    """
    try:
        data = _load_toml(path)
    except Exception as exc:
        return [], [f"cannot parse runtime TOML: {exc}"]

    entries: list[AgentEntry] = []
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    seen_discord_ids: dict[str, str] = {}

    for agent_type in ("managed", "external"):
        section = _authority_section_label(agent_type)
        section_data = data.get(section)
        if section_data is None:
            continue
        if not isinstance(section_data, list):
            errors.append(f"{section} must be a list of tables")
            continue

        for idx, raw in enumerate(section_data):
            if not isinstance(raw, dict):
                errors.append(f"{section} entry {idx} must be a table")
                continue
            try:
                agent_id = _normalize_id(raw.get("id"))
            except ValueError:
                errors.append(f"{section} entry {idx} missing 'id'")
                continue

            if agent_id in seen_ids:
                errors.append(
                    f"duplicate agent id '{agent_id}' in {seen_ids[agent_id]} and {section}"
                )
                continue
            seen_ids[agent_id] = section

            display_name = _normalize_display_name(raw.get("display_name"), agent_id)
            discord_user_id_value = raw.get("discord_user_id")
            if discord_user_id_value is None:
                errors.append(f"{section} entry '{agent_id}' missing discord_user_id")
                continue
            try:
                discord_user_id = _validate_discord_user_id(discord_user_id_value)
            except ValueError as exc:
                errors.append(f"{section} entry '{agent_id}': {exc}")
                continue

            if discord_user_id in seen_discord_ids:
                errors.append(
                    f"duplicate discord_user_id in {seen_discord_ids[discord_user_id]} and {agent_id}"
                )
                continue
            seen_discord_ids[discord_user_id] = agent_id

            entries.append(AgentEntry(
                id=agent_id,
                display_name=display_name,
                discord_user_id=discord_user_id,
                agent_type=agent_type,
            ))

    return entries, errors


def _diff_rosters(
    authority_entries: list[AgentEntry], runtime_entries: list[AgentEntry]
) -> list[dict[str, Any]]:
    authority_by_id = {e.id: e for e in authority_entries}
    runtime_by_id = {e.id: e for e in runtime_entries}
    diff: list[dict[str, Any]] = []

    for agent_id in sorted(set(authority_by_id) | set(runtime_by_id)):
        a = authority_by_id.get(agent_id)
        r = runtime_by_id.get(agent_id)
        if a is None:
            diff.append({"id": agent_id, "status": "removed"})
        elif r is None:
            diff.append({"id": agent_id, "status": "added"})
        else:
            changes: dict[str, tuple[str, str]] = {}
            for field_name in ("display_name", "discord_user_id", "agent_type"):
                av = getattr(a, field_name)
                rv = getattr(r, field_name)
                if av != rv:
                    changes[field_name] = (rv, av)
            if changes:
                diff.append({"id": agent_id, "status": "changed", "fields": list(changes.keys())})

    return diff


def verify_parity(authority_path: str | Path, runtime_path: str | Path) -> ParityResult:
    """Compare the authority to the private runtime projection."""
    try:
        authority = load_authority(authority_path)
    except AuthorityError as exc:
        return ParityResult(ok=False, errors=[f"authority: {exc}"])

    runtime_entries, runtime_errors = project_runtime_roster(runtime_path)
    result = ParityResult(
        ok=False,
        authority=authority,
        authority_count=len(authority.entries),
        runtime_count=len(runtime_entries),
        source_hash=authority.source_hash,
        authority_hash=authority.source_hash,
        errors=[f"runtime: {e}" for e in runtime_errors],
    )
    if runtime_errors:
        return result

    diff = _diff_rosters(authority.entries, runtime_entries)
    if diff:
        result.diff = diff
        return result

    runtime_hash = canonical_hash(runtime_entries)
    if runtime_hash != authority.source_hash:
        # Should not happen once diffs are empty, but guard against drift in
        # canonical serialization.
        result.errors.append("canonical hash mismatch")
        return result

    result.ok = True
    return result


def _cmd_verify(args: argparse.Namespace) -> int:
    result = verify_parity(args.authority, args.runtime)
    print(json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0 if result.ok else 1


def _cmd_show(args: argparse.Namespace) -> int:
    try:
        authority = load_authority(args.authority)
    except AuthorityError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({
        "ok": True,
        "source_id": authority.source_id,
        "source_version": authority.source_version,
        "source_hash": authority.source_hash,
        "count": len(authority.entries),
        "entries": [e.to_canonical_dict() for e in sorted(authority.entries, key=lambda e: e.id)],
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify parity between the canonical agent registry authority and a runtime config."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify = subparsers.add_parser("verify", help="Compare authority and runtime TOML")
    verify.add_argument("--authority", required=True)
    verify.add_argument("--runtime", required=True)
    verify.set_defaults(func=_cmd_verify)

    show = subparsers.add_parser("show", help="Emit safe authority evidence as JSON")
    show.add_argument("--authority", required=True)
    show.set_defaults(func=_cmd_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
