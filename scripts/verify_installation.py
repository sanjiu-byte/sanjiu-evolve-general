"""Compare a trusted package and an installation; no writes or network."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(source, installed):
    source, installed = Path(source).resolve(), Path(installed).resolve()
    result = {'files_ok': False, 'source': str(source), 'installed': str(installed),
              'version': None, 'checked_files': 0, 'errors': [],
              'host_activation': 'not_checked', 'cross_chat_activation': 'not_checked',
              'persistent_storage': 'not_checked'}
    if source == installed or source in installed.parents or installed in source.parents:
        result['errors'].append('Use independent source and installation directories.')
        return result
    try:
        manifest = json.loads((source / 'PACKAGE.json').read_text(encoding='utf-8'))
        files = manifest['files']
        if manifest.get('name') != 'sanjiu-evolve-general' or not isinstance(files, dict):
            raise ValueError('Wrong package identity or manifest format.')
        required = {'SKILL.md', 'VERSION', 'references/首次启用.md', 'references/安装确认.md',
                    'references/多平台接入.md', 'references/资料保存.md', 'scripts/verify_installation.py'}
        if not required.issubset(files):
            raise ValueError('Incomplete package manifest.')
        version = (source / 'VERSION').read_text(encoding='utf-8').strip()
        if version != manifest.get('version'):
            raise ValueError('Source version and manifest disagree.')
        result['version'] = version
        for relative, expected in files.items():
            parts = PurePosixPath(relative)
            if parts.is_absolute() or '..' in parts.parts or '\\' in relative or ':' in relative:
                raise ValueError('Unsafe manifest path.')
            if not isinstance(expected, str) or len(expected) != 64:
                raise ValueError('Invalid expected hash.')
            for root, label in [(source, 'source'), (installed, 'installed')]:
                path = (root / relative).resolve()
                if root not in path.parents or not path.is_file():
                    result['errors'].append(f'{label}: missing or external file {relative}')
                elif digest(path) != expected:
                    result['errors'].append(f'{label}: content differs {relative}')
            result['checked_files'] += 1
        if not (installed / 'PACKAGE.json').is_file() or digest(installed / 'PACKAGE.json') != digest(source / 'PACKAGE.json'):
            result['errors'].append('installed: PACKAGE.json differs or is missing')
        result['files_ok'] = not result['errors']
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result['errors'].append(str(exc))
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--installed', required=True)
    args = parser.parse_args()
    result = verify(args.source, args.installed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['files_ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
