import cv2
import numpy as np

from neonmekong.lyricvideo import Loop


def test_loop_wraps_and_cover_crops(tmp_path):
    clip = tmp_path / "loop.mp4"
    out = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 36))
    for i in range(10):   # frame i is grey level i*25
        out.write(np.full((36, 64, 3), i * 25, np.uint8))
    out.release()

    loop = Loop(clip, 40, 40)
    assert loop.count == 10
    first = loop.at(0.0)
    assert first.shape == (40, 40, 3)
    assert abs(int(loop.at(0.5).mean()) - 125) < 8       # frame 5, read in order after a seek
    assert abs(int(loop.at(1.3).mean()) - 75) < 8        # 1.3 s wraps round to frame 3
    assert abs(int(loop.at(0.0).mean()) - int(first.mean())) < 3
