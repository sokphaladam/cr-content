from PIL import Image

from crcontent.pipeline import cover_canvas, picture_shape, scene_cover

SCENE = "a young man on a rooftop, one huge glowing full moon in a starry night sky, anime style"
PLAIN = "1girl, solo, long black hair, holding a radio, simple background, red background"


def test_a_scene_prompt_is_drawn_in_the_frames_shape():
    assert scene_cover(SCENE) and not scene_cover(PLAIN) and not scene_cover("")
    assert picture_shape({"frame": "cover", "prompt": SCENE}, (1920, 1080)) == (1920, 1080)
    assert picture_shape({"frame": "cover", "prompt": PLAIN}, (1920, 1080)) == (1080, 1920)


def test_a_scene_is_kept_whole(tmp_path):
    pic = tmp_path / "pic.png"
    sky = Image.new("RGB", (1344, 768), (24, 46, 117))  # a night sky, nothing like the flat red
    sky.save(pic)
    out = Image.open(cover_canvas(pic, (1920, 1080), "red", SCENE)).convert("RGB")
    assert out.size == (1920, 1080)
    r, g, b = out.getpixel((100, 100))
    assert abs(r - 24) < 6 and abs(b - 117) < 6  # not painted over with the cover colour


def test_fill_draws_a_cover_character_in_the_frames_shape():
    assert picture_shape({"frame": "cover", "prompt": PLAIN}, (1920, 1080), "fill") == (1920, 1080)


def test_fit_shows_an_odd_shaped_scene_whole(tmp_path):
    pic = tmp_path / "tall.png"
    Image.new("RGB", (540, 960), (24, 46, 117)).save(pic)  # a portrait scene on a landscape frame
    whole = Image.open(cover_canvas(pic, (1920, 1080), "red", SCENE, fit="fit")).convert("RGB")
    filled = Image.open(cover_canvas(pic, (1920, 1080), "red", SCENE, fit="fill")).convert("RGB")
    assert whole.getpixel((100, 540))[2] < 117 * 0.8  # the sides: the blurred, darkened copy
    assert abs(filled.getpixel((100, 540))[2] - 117) < 6  # the picture itself, edge to edge
