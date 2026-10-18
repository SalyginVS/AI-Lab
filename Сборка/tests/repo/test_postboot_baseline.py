#!/usr/bin/env python3
"""RB-13 F1: choose only a baseline included in the suite; never touch host services."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
COMMIT = '65d72f6ad680b0eabaf14b7f2f5fcf8827a8ec43'
PACKAGE = REPO / 'Сборка/artifacts/postboot'


class BaselineSelection(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rb13-postboot-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.export = self.parent / 'export'
        self.package = self.export / 'Сборка/artifacts/postboot'
        shutil.copytree(PACKAGE, self.package)
        files = ['Сборка/tests/acceptance/t_fast_server.sh',
                 'Сборка/tests/acceptance/evaluate.py',
                 'Сборка/tests/acceptance/baseline.json',
                 'Сборка/tests/acceptance/baseline.live-2026-10-17.json',
                 'Сборка/tests/acceptance/baseline.live-2026-10-18.json',
                 'Сборка/artifacts/q6/llama-server.wrapper.in']
        for name in files:
            path = self.export / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, path)
        (self.export / 'SOURCE_COMMIT').write_text(COMMIT + '\n')

    def install(self, root, *args):
        return subprocess.run(['env', 'LAB_OPERATOR=vladimir', 'bash',
                               str(self.package / 'install_postboot.sh'),
                               '--repo', str(self.export), '--commit', COMMIT,
                               '--root', str(root), *args],
                              capture_output=True, text=True)

    def test_default_preserves_accepted_script(self):
        root = self.parent / 'default'
        result = self.install(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = (root / 'usr/local/libexec/ailab/postboot-check.sh').read_bytes()
        expected = (PACKAGE / 'postboot-check.sh.in').read_bytes()
        self.assertEqual(actual, expected)
        self.assertIn(b'baseline_name=baseline.live-2026-10-18.json', actual)
        print('F1_DEFAULT_SHA256=' + hashlib.sha256(actual).hexdigest())

    def test_build_baseline_changes_only_assignment(self):
        root = self.parent / 'build'
        result = self.install(root, '--baseline-name', 'baseline.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = (PACKAGE / 'postboot-check.sh.in').read_bytes().replace(
            b'baseline_name=baseline.live-2026-10-18.json', b'baseline_name=baseline.json')
        self.assertEqual((root / 'usr/local/libexec/ailab/postboot-check.sh').read_bytes(), expected)

    def test_historical_baseline_is_selectable(self):
        root = self.parent / 'historical'
        result = self.install(root, '--baseline-name', 'baseline.live-2026-10-17.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = (root / 'usr/local/libexec/ailab/postboot-check.sh').read_bytes()
        self.assertIn(b'baseline_name=baseline.live-2026-10-17.json', actual)

    def test_invalid_names_fail_before_writing(self):
        for number, name in enumerate(['baseline.missing.json', '../baseline.json',
                                       'baseline.json;exit', 'evaluate.py']):
            with self.subTest(name=name):
                root = self.parent / ('invalid-' + str(number))
                result = self.install(root, '--baseline-name', name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Baseline must be', result.stderr)
                self.assertFalse(root.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
