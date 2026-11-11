import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('installation_check', Path(__file__).parents[1] / 'scripts/verify_installation.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

class InstallationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source'
        self.installed = Path(self.temp.name) / 'installed'
        names = ['SKILL.md', 'VERSION', 'references/首次启用.md', 'references/安装确认.md',
                 'references/多平台接入.md', 'references/资料保存.md', 'scripts/verify_installation.py']
        for name in names:
            p = self.source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('0.1.1\n' if name == 'VERSION' else 'synthetic fixture\n', 'utf-8')
        self.manifest = {'name': 'sanjiu-evolve-general', 'version': '0.1.1',
                         'files': {name: check.digest(self.source / name) for name in names}}
        (self.source / 'PACKAGE.json').write_text(json.dumps(self.manifest), 'utf-8')
        shutil.copytree(self.source, self.installed)

    def test_complete_does_not_claim_activation(self):
        r = check.verify(self.source, self.installed)
        self.assertTrue(r['files_ok'])
        self.assertEqual(r['cross_chat_activation'], 'not_checked')
        self.assertEqual(r['persistent_storage'], 'not_checked')

    def test_missing_reference(self):
        (self.installed / 'references/资料保存.md').unlink()
        self.assertFalse(check.verify(self.source, self.installed)['files_ok'])

    def test_modified_installation_and_version(self):
        (self.installed / 'VERSION').write_text('0.1.0', 'utf-8')
        self.assertFalse(check.verify(self.source, self.installed)['files_ok'])

    def test_html_is_not_package(self):
        (self.source / 'PACKAGE.json').write_text('<html>Login</html>', 'utf-8')
        self.assertFalse(check.verify(self.source, self.installed)['files_ok'])

    def test_source_tampering(self):
        (self.source / 'SKILL.md').write_text('changed', 'utf-8')
        self.assertFalse(check.verify(self.source, self.installed)['files_ok'])

    def test_same_directory_not_an_install_check(self):
        self.assertFalse(check.verify(self.source, self.source)['files_ok'])

    def test_personal_files_preserved(self):
        p = self.installed / 'my-private-notes.md'
        p.write_bytes(b'keep unchanged')
        self.assertTrue(check.verify(self.source, self.installed)['files_ok'])
        self.assertEqual(p.read_bytes(), b'keep unchanged')

    def test_path_traversal_manifest_rejected(self):
        self.manifest['files']['../outside.txt'] = 'a' * 64
        (self.source / 'PACKAGE.json').write_text(json.dumps(self.manifest), 'utf-8')
        self.assertFalse(check.verify(self.source, self.installed)['files_ok'])

if __name__ == '__main__':
    unittest.main()
