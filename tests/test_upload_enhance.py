from PIL import Image

from crcontent.shorts.footage import own_pick
from crcontent.visuals import enhance, media_size


def test_small_photo_is_upscaled_big_one_copied(tmp_path):
    Image.new("RGB", (400, 300), "red").save(tmp_path / "small.jpg")
    Image.new("RGB", (1080, 1920), "red").save(tmp_path / "big.jpg")
    assert media_size(enhance(tmp_path / "small.jpg", tmp_path / "a.jpg")) == (1440, 1080)
    assert media_size(enhance(tmp_path / "big.jpg", tmp_path / "b.jpg")) == (1080, 1920)


def test_wide_upload_fits_tall_one_fills(tmp_path):
    Image.new("RGB", (1920, 1080)).save(tmp_path / "wide.jpg")
    Image.new("RGB", (1080, 1920)).save(tmp_path / "tall.jpg")
    plan = {"shot": "a cat", "key_objects": []}
    assert own_pick(tmp_path / "wide.jpg", 3.0, False, "cat", plan, check=False)[0]["layout"] == "fit"
    assert "layout" not in own_pick(tmp_path / "tall.jpg", 3.0, False, "cat", plan, check=False)[0]
