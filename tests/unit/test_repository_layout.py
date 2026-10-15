"""Guard relocated entry points, test isolation and task-routing documentation."""
import ast
import importlib
from pathlib import Path
import re
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]


class RepositoryLayoutTest(unittest.TestCase):
    def test_compatibility_facades_export_canonical_implementations(self):
        pairs = (
            ('pipeline', 'asset_pipeline.legacy', ('validate', 'digest', 'bundle_digest', 'local_file')),
            ('surface_gate', 'asset_pipeline.surface', ('geometry', 'geometry_delta', 'surface_digest', 'validate_surface')),
            ('asset_pipeline.blender_adapter', 'asset_pipeline.adapters.blender.adapter', ('validate_plan', 'execute_blender')),
        )
        for old, new, names in pairs:
            before, after = importlib.import_module(old), importlib.import_module(new)
            for name in names:
                self.assertIs(getattr(before, name), getattr(after, name))

    def test_runtime_does_not_depend_on_facades_tests_or_experiments(self):
        banned = {'pipeline', 'surface_gate', 'surface_fixture', 'tests', 'experiments'}
        for path in (ROOT/'asset_pipeline').rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules = [node.module]
                for module in modules:
                    self.assertNotIn(module.split('.')[0], banned, str(path))

    def test_fixtures_do_not_import_test_case_modules(self):
        for path in (ROOT/'tests/fixtures').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module] + [n.name for n in node.names]
                for module in modules:
                    self.assertFalse(any(part.startswith('test_') for part in module.split('.')), str(path))

    def test_local_markdown_links_resolve_inside_repository(self):
        documents = [ROOT/'README.md', ROOT/'AGENTS.md']
        for folder in ('docs', 'templates', 'examples', 'experiments', 'tests'):
            documents.extend((ROOT/folder).rglob('*.md'))
        for document in documents:
            for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
                if ':' in link or link.startswith('#'):
                    continue
                target = (document.parent/unquote(link.split('#')[0])).resolve()
                self.assertTrue(target.is_relative_to(ROOT), f'{document}: {link}')
                self.assertTrue(target.exists(), f'{document}: broken link {link}')
