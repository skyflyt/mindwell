"""Exercise an installed package against fictional, disposable vaults.

Run with the Python interpreter from a fresh environment containing the built wheel.
This script never registers schedules, contacts a model, or accesses a real vault.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    checks = []
    with tempfile.TemporaryDirectory(prefix='mindwell-release-smoke-') as tmp:
        root = Path(tmp)
        vault = root / 'vault'
        env = dict(os.environ, MINDWELL_CACHE=str(root / 'cache'))
        # An ambient user's index/backup override must never escape this fixture.
        for key in ('MINDWELL_INDEX', 'LOBY_INDEX', 'MINDWELL_BACKUPS', 'PYTHONPATH'):
            env.pop(key, None)
        def cli(*args):
            result = subprocess.run([sys.executable, '-m', 'mindwell', *map(str, args)],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return json.loads(result.stdout)
        cli('init', vault, '--agent-name', 'Nova', '--profile', 'personal-ops',
            '--automations', 'core', '--timezone', 'UTC')
        assert (vault / 'START-HERE.md').is_file()
        assert (vault / 'automations' / 'plan.json').is_file()
        checks.append('installed personal-ops scaffold and automation plan')
        note = vault / 'wiki' / 'observatory.md'
        note.write_text('# Observatory\n\nThe observatory bulletin recipient is Morgan Example.\n', encoding='utf-8')
        cli('index', vault)
        assert cli('doctor', vault)['ready']
        result = cli('retrieve', vault, 'Who receives the observatory bulletin?', '--explain')
        assert 'Morgan Example' in result['context']
        checks.append('index, doctor, and grounded lexical retrieval')
        note.write_text('# Observatory\n\nThe observatory bulletin recipient is Casey Example.\n', encoding='utf-8')
        result = cli('retrieve', vault, 'Who receives the observatory bulletin?', '--explain')
        assert 'Casey Example' in result['context'] and 'Morgan Example' not in result['context']
        note.unlink()
        result = cli('retrieve', vault, 'Who receives the observatory bulletin?', '--explain')
        assert all(row['path'] != 'wiki/observatory.md' for row in result['results'])
        checks.append('edited and removed source refresh')
        custom = '# My own contract\nKeep this exact user wording.\n'
        (vault / 'AGENTS.md').write_text(custom, encoding='utf-8')
        install = vault / 'config' / 'installation.json'
        data = json.loads(install.read_text(encoding='utf-8'))
        old = '# Old fictional memory template\n'
        (vault / 'MEMORY.md').write_text(old, encoding='utf-8')
        data.setdefault('scaffold_hashes', {})['MEMORY.md'] = hashlib.sha256(old.encode()).hexdigest()
        install.write_text(json.dumps(data), encoding='utf-8')
        cli('upgrade', vault)
        assert (vault / 'AGENTS.md').read_text(encoding='utf-8') == custom
        assert (vault / 'MEMORY.md').read_text(encoding='utf-8') != old
        preview = cli('restore', vault)
        assert preview['ok'] and not preview['applied']
        restored = cli('restore', vault, '--yes')
        assert restored['applied']
        assert (vault / 'MEMORY.md').read_text(encoding='utf-8') == old
        assert (vault / 'AGENTS.md').read_text(encoding='utf-8') == custom
        checks.append('upgrade preserves customization; backup preview and restore work')
    print(json.dumps({'ok': True, 'checks': checks}, indent=2))


if __name__ == '__main__':
    main()
