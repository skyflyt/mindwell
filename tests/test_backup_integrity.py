import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mindwell import scaffold
from mindwell.fsio import atomic_write_bytes


class BackupIntegrityTests(unittest.TestCase):
    def test_restore_in_same_second_preserves_both_backup_generations(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'MINDWELL_CACHE': str(Path(tmp) / 'cache')}):
            vault = Path(tmp) / 'vault'
            vault.mkdir()
            note = vault / 'MEMORY.md'
            note.write_bytes(b'original\r\n')
            with patch.object(scaffold, 'datetime') as clock:
                clock.now.return_value.strftime.return_value = '20240101T010101Z'
                original = scaffold._backup_vault(vault, ['MEMORY.md'])
                note.write_bytes(b'new version\r\n')
                result = scaffold.restore_backup(vault, apply=True)
            self.assertTrue(result['applied'])
            self.assertEqual(b'original\r\n', note.read_bytes())
            self.assertEqual(b'original\r\n', (original / 'MEMORY.md').read_bytes())
            undo = Path(result['pre_restore_backup'])
            self.assertNotEqual(original, undo)
            self.assertEqual(b'new version\r\n', (undo / 'MEMORY.md').read_bytes())
            self.assertEqual(undo.name, scaffold.list_backups(vault)[0]['stamp'])

    def test_failed_backup_is_not_offered_as_a_restore_point(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'MINDWELL_CACHE': str(Path(tmp) / 'cache')}):
            vault = Path(tmp) / 'vault'
            vault.mkdir()
            (vault / 'MEMORY.md').write_bytes(b'original')
            with patch.object(scaffold, 'atomic_write_bytes', side_effect=OSError('fictional disk full')):
                with self.assertRaises(OSError):
                    scaffold._backup_vault(vault, ['MEMORY.md'])
            self.assertEqual([], scaffold.list_backups(vault))
            self.assertEqual(b'original', (vault / 'MEMORY.md').read_bytes())

    def test_failed_binary_replace_preserves_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'binary.dat'
            path.write_bytes(b'\xff\x00original')
            with patch('mindwell.fsio.os.replace', side_effect=OSError('fictional failure')):
                with self.assertRaises(OSError):
                    atomic_write_bytes(path, b'new bytes')
            self.assertEqual(b'\xff\x00original', path.read_bytes())
