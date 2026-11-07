import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_lang_sync as cls  # noqa: E402


class LangSyncTest(unittest.TestCase):
    def _mk(self, base, en, zh):
        for name in en:
            p = base / "docs" / "en" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")
        for name in zh:
            p = base / "docs" / "zh-CN" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")

    def test_match(self):
        with tempfile.TemporaryDirectory() as t:
            self._mk(Path(t), ["a.md", "img/b.png"], ["a.md", "img/b.png"])
            self.assertEqual(cls.main([t]), 0)

    def test_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            self._mk(Path(t), ["a.md", "c.md"], ["a.md"])
            self.assertEqual(cls.diff(Path(t) / "docs" / "en", Path(t) / "docs" / "zh-CN"), (["c.md"], []))
            self.assertEqual(cls.main([t]), 1)


if __name__ == "__main__":
    unittest.main()
