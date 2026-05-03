from pathlib import Path

import pytest

from src.entity_rewriter import Entity, generate_entity_rewrites, load_entities


RUDEUS = Entity(
    id="rudeus",
    type="person",
    canonical="鲁迪乌斯",
    aliases=("鲁迪乌斯", "鲁迪", "主角", "鲁迪乌斯·格雷拉特"),
)


def test_generate_entity_rewrites_expands_alias_to_canonical_and_full_name():
    rewrites = generate_entity_rewrites("鲁迪活了多少岁？", entities=[RUDEUS])

    assert rewrites == [
        "鲁迪乌斯活了多少岁？",
        "鲁迪 鲁迪乌斯 活了多少岁？",
        "鲁迪乌斯·格雷拉特活了多少岁？",
    ]


def test_generate_entity_rewrites_expands_title_alias():
    rewrites = generate_entity_rewrites("主角活了多少岁？", entities=[RUDEUS])

    assert rewrites == [
        "鲁迪乌斯活了多少岁？",
        "主角 鲁迪乌斯 活了多少岁？",
        "鲁迪乌斯·格雷拉特活了多少岁？",
    ]


def test_generate_entity_rewrites_skips_query_that_already_has_canonical():
    rewrites = generate_entity_rewrites("鲁迪乌斯活了多少岁？", entities=[RUDEUS])

    assert rewrites == []


def test_generate_entity_rewrites_simplifies_long_alias_that_contains_canonical():
    nanahoshi = Entity(
        id="nanahoshi",
        type="person",
        canonical="七星",
        aliases=("七星", "七星静香", "沉默的七星"),
    )

    rewrites = generate_entity_rewrites("沉默的七星是谁？", entities=[nanahoshi])

    assert rewrites == [
        "七星是谁？",
        "沉默的七星 七星 是谁？",
        "七星静香是谁？",
    ]


def test_load_entities_validates_shape(tmp_path: Path):
    path = tmp_path / "entities.json"
    path.write_text('{"id": "bad"}', encoding="utf-8")

    with pytest.raises(ValueError, match="JSON array"):
        load_entities(path)
