"""Test data: bookmark seeds, {site} placeholders, generated files."""
from sbtest.data import Bm, BookmarksSeed, files, Folder
from sbtest.data.loader import format_data


def test_bookmarks_seed_ids_unique():
    seed = BookmarksSeed().url("A", "http://a").folder("F", [Bm("B", "http://b"), Folder("E")])
    data = seed.to_json()
    ids = []

    def walk(n):
        ids.append(n["id"])
        for c in n.get("children", []):
            walk(c)

    for root in data["roots"].values():
        walk(root)
    assert len(ids) == len(set(ids))
    assert data["roots"]["bookmark_bar"]["children"][1]["children"][0]["url"] == "http://b"


def test_seed_from_dict_and_format():
    raw = {"bookmark_bar": [{"name": "A", "url": "{site}/a"}, {"name": "F", "children": [{"name": "B", "url": "{site}/b"}]}]}
    seed = BookmarksSeed.from_dict(format_data(raw, {"site": "http://h:1"}))
    j = seed.to_json()["roots"]["bookmark_bar"]["children"]
    assert j[0]["url"] == "http://h:1/a" and j[1]["children"][0]["url"] == "http://h:1/b"


def test_png_is_valid(tmp_path):
    f = files.png_file(tmp_path)
    assert f.read_bytes().startswith(b"\x89PNG")
