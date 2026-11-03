"""Every downloaded photo or clip whose licence asks for a credit is credited: commons.credit reads the source record
beside any downloaded file, and a Short's post.txt lists its cutaways too."""
import json

from crcontent import commons
from crcontent.pipeline import post_body


def _file(tmp_path, name, record=None):
    path = tmp_path / name
    path.write_bytes(b"x")
    if record is not None:
        path.with_suffix(".json").write_text(json.dumps(record), encoding="utf-8")
    return path


def test_credit_reads_inaturalist_commons_and_archive_records(tmp_path):
    inat = _file(tmp_path, "inaturalist-photo-1.jpg", {"source": "inaturalist", "kind": "photo", "author": "Mila C.",
                                                        "licence": "CC BY 4.0", "page": "https://inaturalist.org/o/1"})
    assert commons.credit(inat) == "Photo: Mila C., CC BY 4.0, via iNaturalist (https://inaturalist.org/o/1)"
    assert commons.site(inat) == "iNaturalist"
    # Commons' own records have no "source" key
    com = _file(tmp_path, "abc.jpg", {"author": "F. S.", "licence": "CC BY-SA 4.0", "page": "https://c/f"})
    assert commons.credit(com) == "Photo: F. S., CC BY-SA 4.0, via Wikimedia Commons (https://c/f)"
    clip = _file(tmp_path, "archive-video-1.mp4", {"source": "archive", "kind": "video", "licence": "Public domain"})
    assert commons.credit(clip) == "Clip: unknown author, Public domain, via the Internet Archive"


def test_no_credit_without_a_licence_record(tmp_path):
    assert commons.credit(_file(tmp_path, "pixabay-video-1.mp4")) == ""  # Pixabay keeps no record: none needed
    assert commons.credit(_file(tmp_path, "x.jpg", {"check": 8})) == ""  # some other json beside it
    bad = _file(tmp_path, "y.jpg")
    bad.with_suffix(".json").write_text("{not json", encoding="utf-8")
    assert commons.credit(bad) == ""
    assert commons.credit(tmp_path / "missing.jpg") == ""


def test_post_lists_each_credit_once():
    body = post_body("T", "Caption", "#a", photos=["Photo: A, CC BY 4.0", "", "Photo: A, CC BY 4.0", "Photo: B, CC0"])
    assert body.count("Photo: A, CC BY 4.0") == 1 and "Photo: B, CC0" in body
