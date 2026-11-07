"""Hidden History H5: the history map graphic (places, route, period, sourced region only)."""
import json
import shutil

import pytest

from crcontent import graphic_templates as gt
from crcontent import timeline
from crcontent.script import Clip, Scene, VideoScript
from crcontent.shorts import motion

SQUARE = {"type": "Polygon", "coordinates": [[[103, 13], [105, 13], [105, 14], [103, 14], [103, 13]]]}
SOURCED = {"region_geojson": json.dumps(SQUARE), "region_source": "https://example.org/khmer-map", "region_dates": "1150-1220"}


def test_places_and_route_without_a_region():
    props, errors = gt.validate("HistoryMap", {"markers": "Angkor @ 13.4, 103.9; Kulen @ -13.5,104.1", "route": "through_the_places"})
    assert errors == []
    assert props["points"] == [{"label": "Angkor", "lat": 13.4, "lon": 103.9}, {"label": "Kulen", "lat": -13.5, "lon": 104.1}]
    assert props["region"] is None  # honest fallback: places and route only


def test_bad_places_and_a_route_with_one_place():
    errors = gt.validate("HistoryMap", {"markers": "Angkor 13.4 103.9; Mars @ 95, 10", "route": "through_the_places"})[1]
    found = " | ".join(errors)
    assert "isn't 'name @ latitude, longitude'" in found and "no such latitude" in found and "at least two places" in found


def test_a_region_needs_its_source_and_dates():
    errors = gt.validate("HistoryMap", {"region_geojson": json.dumps(SQUARE)})[1]
    assert any("needs the link" in e for e in errors) and any("which years" in e for e in errors)
    assert "not valid GeoJSON" in gt.validate("HistoryMap", {**SOURCED, "region_geojson": "{nope"})[1][0]
    line = json.dumps({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})
    assert "Polygon" in gt.validate("HistoryMap", {**SOURCED, "region_geojson": line})[1][0]


def test_a_sourced_region_as_feature_or_collection():
    feat = {"type": "Feature", "properties": {}, "geometry": SQUARE}
    assert gt.validate("HistoryMap", {**SOURCED, "region_geojson": json.dumps(feat)})[0]["region"] == SQUARE
    coll = {"type": "FeatureCollection", "features": [feat, feat]}
    region = gt.validate("HistoryMap", {**SOURCED, "region_geojson": json.dumps(coll)})[0]["region"]
    assert region == {"type": "GeometryCollection", "geometries": [SQUARE, SQUARE]}


def test_render_leaves_an_unsourced_region_out_and_keeps_map_zoom():
    bad = Clip(id="g1", track="graphics", template="HistoryMap", start=0, duration=4, props={"region_geojson": json.dumps(SQUARE)})
    old = Clip(id="g2", track="graphics", template="MapZoom", start=5, duration=3, props={})
    left: dict = {}
    s = VideoScript(title="T", caption="c", hashtags=[], scenes=[Scene(narration="a", visual_query="b")], clips=[bad, old])
    out = timeline.graphic_clips(s, 10, "", log=lambda *_: None, left_out=left)
    assert [c["id"] for c in out] == ["MapZoom"] and "needs the link" in left["g1"]


@pytest.mark.skipif(not ((motion.PROJECT / "node_modules").is_dir() and shutil.which("node")), reason="needs Remotion")
def test_a_real_history_map_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(gt, "STILLS", tmp_path)
    props = gt.validate("HistoryMap", {**SOURCED, "route": "through_the_places"})[0]
    assert list(gt.render_stills([{"template": "HistoryMap", "props": props, "seconds": 4.5}]).values()) == [""]
