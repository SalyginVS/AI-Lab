#!/usr/bin/env python3
"""Verify C03 archive discovery using files in a temporary client home."""
import ast
import json
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]


class ClientArchive(unittest.TestCase):
    def test_archive_and_extension_without_snap(self):
        with tempfile.TemporaryDirectory(prefix='rb13-c03-') as name:
            root = Path(name)
            home = root / 'home'
            app = home / '.local/opt/vscode/1.142.0/VSCode-linux-x64/resources/app/package.json'
            extension = home / '.vscode/extensions/pi0.pi-vscode-0.0.9/package.json'
            for path, version in [(app, '1.142.0'), (extension, '0.0.9')]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({'version': version}))
            source = ast.parse((REPO / 'Сборка/tests/acceptance/t_fast_client.py').read_text())
            function = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == 'c03')
            def local_path(path):
                return root / str(path).lstrip('/')
            scope = {'Path': local_path, 'H': home, 'json': json}
            exec(compile(ast.Module(body=[function], type_ignores=[]), '<c03>', 'exec'), scope)
            self.assertEqual(scope['c03'](), {'vscode_versions': ['1.142.0'], 'extensions': ['0.0.9']})


if __name__ == '__main__':
    unittest.main(verbosity=2)
