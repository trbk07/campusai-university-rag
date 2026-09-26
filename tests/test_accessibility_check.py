from scripts.accessibility_check import check
from campusai.web import INDEX_HTML


def test_demo_ui_accessibility_smoke():
    assert check(INDEX_HTML) == []
