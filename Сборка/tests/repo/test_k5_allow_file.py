#!/usr/bin/env python3
"""RB-13 delta: exact file allowances cannot bypass immutable acceptance inputs."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
START = '65d72f6ad680b0eabaf14b7f2f5fcf8827a8ec43'
ACCEPTANCE = 'Сборка/tests/acceptance/'
ALLOWED = ['embedding_reference.rb10.json', 'embedding_reference.rb10.json.sha256', 't_fast_client.py']
IMMUTABLE = ['baseline.json', 'baseline.live-2026-10-17.json', 'evaluate.py']


class ExactFileAllowance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='rb13-k5-')
        cls.fixture = Path(cls.temp.name) / 'repo'
        subprocess.run(['git', 'clone', '--quiet', '--shared', str(REPO), str(cls.fixture)], check=True)
        checker = 'Сборка/tests/repo/check_package.py'
        shutil.copy2(REPO / checker, cls.fixture / checker)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check(self, *extra, working_tree=True):
        output = Path(self.temp.name) / 'result.json'
        output.unlink(missing_ok=True)
        args = ['python3', '-I', 'Сборка/tests/repo/check_package.py', '--static-only',
                '--start', START, '--allow-artifact-dir', 'Сборка/artifacts/postboot/',
                '--output', str(output)]
        if working_tree:
            args.append('--working-tree')
        for name in ALLOWED:
            args += ['--allow-file', ACCEPTANCE + name]
        result = subprocess.run(args + list(extra), cwd=self.fixture, capture_output=True, text=True)
        data = json.loads(output.read_text()) if output.exists() else None
        return result, data

    def test_requested_exact_files_are_allowed(self):
        result, data = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(data['checks']['K5']['status'], 'PASS')

    def test_directory_is_rejected(self):
        result, data = self.check('--allow-file', 'Сборка/tests/acceptance/')
        self.assertEqual(result.returncode, 2)
        self.assertIn('never a directory', result.stderr)
        self.assertIsNone(data)

    def test_allowance_does_not_cover_sibling(self):
        name = ACCEPTANCE + 't_fast_server.sh'
        path = self.fixture / name
        original = path.read_bytes()
        try:
            path.write_bytes(original + b'\n')
            result, data = self.check()
            self.assertEqual(result.returncode, 1)
            self.assertIn('accepted bytes changed: ' + name, data['checks']['K5']['errors'])
        finally:
            path.write_bytes(original)

    def test_immutable_files_fail_even_when_explicitly_allowed(self):
        for name in IMMUTABLE:
            path = self.fixture / ACCEPTANCE / name
            original = path.read_bytes()
            try:
                path.write_bytes(original + b'\n')
                for working_tree in [False, True]:
                    with self.subTest(name=name, working_tree=working_tree):
                        result, data = self.check('--allow-file', ACCEPTANCE + name, working_tree=working_tree)
                        self.assertEqual(result.returncode, 1)
                        self.assertEqual(data['checks']['K5']['status'], 'FAIL')
                        self.assertIn('immutable accepted bytes changed: ' + ACCEPTANCE + name, data['checks']['K5']['errors'])
            finally:
                path.write_bytes(original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
