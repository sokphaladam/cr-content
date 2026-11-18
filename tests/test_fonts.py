"""Settings → Caption fonts: downloads land in the app's fonts folder as static Bold faces the renderer can find by name."""
import io

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.designspaceLib import AxisDescriptor
from fontTools.ttLib import TTFont

from crcontent import fonts


def variable_font() -> bytes:
    """A tiny variable font with a weight axis, like the ones Google ships."""
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "A"])
    fb.setupCharacterMap({65: "A"})
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0)); pen.lineTo((500, 700)); pen.lineTo((1000, 0)); pen.closePath()
    fb.setupGlyf({".notdef": pen.glyph(), "A": pen.glyph()})
    fb.setupHorizontalMetrics({".notdef": (1000, 0), "A": (1000, 0)})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Source", "styleName": "Regular"})
    fb.setupOS2(); fb.setupPost()
    axis = AxisDescriptor(); axis.tag, axis.name, axis.minimum, axis.default, axis.maximum = "wght", "Weight", 400, 400, 900
    fb.setupFvar([axis], [])
    out = io.BytesIO(); fb.save(out)
    return out.getvalue()


class Reply:
    def __init__(self, content): self.content = content
    def raise_for_status(self): pass


def test_variable_font_is_cut_at_its_caption_weight(tmp_path, monkeypatch):
    monkeypatch.setattr(fonts, "folder", lambda: tmp_path)
    monkeypatch.setattr(fonts.requests, "get", lambda url, timeout: Reply(variable_font()))
    assert fonts.download("Cinzel") == {"family": "Cinzel", "installed": True}
    font = TTFont(tmp_path / "Cinzel-ExtraBold.ttf")  # Cinzel headlines are ExtraBold
    assert "fvar" not in font and font["name"].getDebugName(1) == "Cinzel" and font["OS/2"].usWeightClass == 800
    assert not list(tmp_path.glob("*.part"))


def test_only_known_families_and_good_files(tmp_path, monkeypatch):
    monkeypatch.setattr(fonts, "folder", lambda: tmp_path)
    with pytest.raises(fonts.FontError):
        fonts.download("../../evil")
    monkeypatch.setattr(fonts.requests, "get", lambda url, timeout: Reply(b"not a font"))
    with pytest.raises(fonts.FontError):
        fonts.download("Inter")
    assert not list(tmp_path.iterdir())  # nothing half-saved


def test_catalog_names_who_uses_each_font():
    rows = {r["family"]: r for r in fonts.catalog()}
    assert "Hidden History Files headline" in rows["Cinzel"]["used_by"]
    assert "Wildlife Facts captions" in rows["Montserrat"]["used_by"]


def test_medium_body_font_is_not_marked_bold(tmp_path, monkeypatch):
    monkeypatch.setattr(fonts, "folder", lambda: tmp_path)
    monkeypatch.setattr(fonts.requests, "get", lambda url, timeout: Reply(variable_font()))
    fonts.download("Inter")
    font = TTFont(tmp_path / "Inter-Medium.ttf")
    assert font["OS/2"].usWeightClass == 500 and not font["head"].macStyle & 1
    assert (font["name"].getDebugName(1), font["name"].getDebugName(17)) == ("Inter", "Medium")
