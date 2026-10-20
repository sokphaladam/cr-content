from pathlib import Path

from crcontent.longform.parse import chapters_from, clock, parse, stamp, unquote

SAMPLE = Path(__file__).resolve().parent.parent / "scripts" / "smartest-birds.md"

SCRIPT = """# Cats, Explained — Video Script

## Overview

| Rank | Cat | Why |
| --- | --- | --- |
| 1 | Lion | Big |

## Part one

| Time | Visual | On-screen Text | Voiceover |
| --- | --- | --- | --- |
| 0:00 | Cat yawning | "WHY CATS?" | Cats sleep a lot. |
| 0:08 | Lion on a rock | “#1 LION” | Number one: the lion. |

## Part two

| Ep | Time | Visual | On-screen Text | Voiceover |
|---|---|---|---|---|
| 1 | 1:02:03 | Tiger \\| stripes | 'Stripes' | Tigers have stripes. |

**Title options**

- Cats, Explained
- Why Cats Rule

**Description (first lines)**

All about cats.

Chapters: 0:00 Intro · 0:08 Lion · 1:02:03 Tiger

**Shorts spin-offs**

1. Lions nap
"""


def test_tables_titles_and_packaging(tmp_path):
    md = tmp_path / "cats.md"
    md.write_text(SCRIPT, encoding="utf-8")
    s = parse(md)
    assert s.title == "Cats, Explained"
    assert s.slug == "cats"
    assert [sc.n for sc in s.scenes] == [1, 2, 3]
    assert [sc.text for sc in s.scenes] == ["WHY CATS?", "#1 LION", "Stripes"]
    assert s.scenes[2].visual == "Tiger | stripes"
    assert s.scenes[2].planned == 3723
    assert (s.scenes[1].rank, s.scenes[1].name) == (1, "LION")
    assert s.scenes[0].rank is None
    assert s.title_options == ["Cats, Explained", "Why Cats Rule"]
    assert s.description == "All about cats."
    assert [(c.planned, c.title) for c in s.chapters] == [(0, "Intro"), (8, "Lion"), (3723, "Tiger")]
    assert s.shorts == ["Lions nap"]
    assert any("Overview" in n for n in s.notes)


def test_sample_script():
    s = parse(SAMPLE)
    assert len(s.scenes) == 42
    assert [sc.rank for sc in s.scenes if sc.rank] == list(range(10, 0, -1))
    assert len(s.chapters) == 11
    assert all('"' not in sc.text for sc in s.scenes)


def test_helpers():
    assert clock("0:00–0:12") == 0
    assert clock("10:32") == 632
    assert clock("no time") is None
    assert stamp(632) == "10:32" and stamp(3723) == "1:02:03"
    assert unquote('"“BIRD BRAIN?”"') == "BIRD BRAIN?"
    assert unquote("It's fine") == "It's fine"
    assert [c.title for c in chapters_from("0:00 Intro · 1:35 Pigeon")] == ["Intro", "Pigeon"]
