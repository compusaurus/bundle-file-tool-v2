"""Headless Linux browsing preserves the private web-session contract."""
from pathlib import Path
import pytest
from web.file_browser import browse_directory


def test_browse_lists_directories_before_files_without_reading_contents(tmp_path):
    (tmp_path / "z folder").mkdir()
    (tmp_path / "a.txt").write_text("not returned")
    result = browse_directory({"path": str(tmp_path)})
    assert result["path"] == str(tmp_path.resolve())
    assert [(entry["name"], entry["directory"]) for entry in result["entries"]] == [
        ("z folder", True), ("a.txt", False)]
    assert not result["truncated"]
    assert browse_directory({"path": str(tmp_path / "a.txt")}) == result


@pytest.mark.parametrize("payload", [None, [], {"path": 5}])
def test_browse_rejects_invalid_request(payload):
    with pytest.raises(ValueError, match="text path"):
        browse_directory(payload)


def test_browse_missing_folder_has_clear_error(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        browse_directory({"path": str(tmp_path / "missing")})


def test_browse_empty_path_uses_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert browse_directory({})["path"] == str(tmp_path.resolve())


def test_browse_limits_large_directory(tmp_path):
    for number in range(1003):
        (tmp_path / str(number)).touch()
    result = browse_directory({"path": str(tmp_path)})
    assert len(result["entries"]) == 1000
    assert result["truncated"]
