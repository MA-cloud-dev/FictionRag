"""Conservative entity-alias query rewriting."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import DEFAULT_ENTITIES_PATH


DEFAULT_REWRITE_LIMIT = 3


@dataclass(frozen=True)
class Entity:
    id: str
    type: str
    canonical: str
    aliases: tuple[str, ...]


def load_entities(path: Path = DEFAULT_ENTITIES_PATH) -> list[Entity]:
    if not path.exists():
        return []

    raw_entities = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_entities, list):
        raise ValueError("Entity file must contain a JSON array")

    entities: list[Entity] = []
    for raw in raw_entities:
        if not isinstance(raw, dict):
            raise ValueError("Each entity must be a JSON object")
        entities.append(_parse_entity(raw))
    return entities


def generate_entity_rewrites(
    query: str,
    entities: list[Entity] | None = None,
    limit: int = DEFAULT_REWRITE_LIMIT,
) -> list[str]:
    if limit <= 0:
        return []
    if entities is None:
        entities = load_entities()

    rewrites: list[str] = []
    seen = {query}
    for entity, alias in _find_entity_matches(query, entities):
        candidates = [
            _replace_alias(query, alias, entity.canonical),
            _append_canonical_after_alias(query, alias, entity.canonical),
        ]
        full_name = _full_name(entity)
        if full_name:
            candidates.append(_replace_alias(query, alias, full_name))

        for candidate in candidates:
            normalized = candidate.strip()
            if not normalized or normalized in seen:
                continue
            rewrites.append(normalized)
            seen.add(normalized)
            if len(rewrites) >= limit:
                return rewrites

    return rewrites


def _parse_entity(raw: dict[str, Any]) -> Entity:
    entity_id = _required_string(raw, "id")
    entity_type = _required_string(raw, "type")
    canonical = _required_string(raw, "canonical")
    aliases_raw = raw.get("aliases")
    if not isinstance(aliases_raw, list):
        raise ValueError(f"Entity {entity_id!r} aliases must be a list")

    aliases: list[str] = []
    seen: set[str] = set()
    for item in [canonical, *aliases_raw]:
        alias = str(item).strip()
        if not alias or alias in seen:
            continue
        aliases.append(alias)
        seen.add(alias)
    return Entity(
        id=entity_id,
        type=entity_type,
        canonical=canonical,
        aliases=tuple(aliases),
    )


def _required_string(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Entity field {key!r} must be a non-empty string")
    return value.strip()


def _find_entity_matches(query: str, entities: list[Entity]) -> list[tuple[Entity, str]]:
    matches: list[tuple[int, int, Entity, str]] = []
    for entity in entities:
        aliases = sorted(entity.aliases, key=len, reverse=True)
        has_canonical = entity.canonical in query
        for alias in aliases:
            if alias == entity.canonical:
                continue
            if has_canonical and entity.canonical not in alias:
                continue
            index = query.find(alias)
            if index >= 0:
                matches.append((index, -len(alias), entity, alias))
                break
    matches.sort(key=lambda item: (item[0], item[1]))
    return [(entity, alias) for _, _, entity, alias in matches]


def _replace_alias(query: str, alias: str, replacement: str) -> str:
    return query.replace(alias, replacement, 1)


def _append_canonical_after_alias(query: str, alias: str, canonical: str) -> str:
    return query.replace(alias, f"{alias} {canonical} ", 1)


def _full_name(entity: Entity) -> str | None:
    candidates = [
        alias
        for alias in entity.aliases
        if alias != entity.canonical and entity.canonical in alias
    ]
    if not candidates:
        return None
    preferred = [
        alias
        for alias in candidates
        if alias.startswith(entity.canonical)
    ]
    if preferred:
        return max(preferred, key=len)
    return max(candidates, key=len)
