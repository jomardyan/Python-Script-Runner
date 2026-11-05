"""Check owned Python syntax without creating caches inside distributable templates.

Copyright (c) 2026 Hayk Jomardyan - Lolisoft. Repository license applies.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = [root / 'runner.py']
for folder in ('runners', 'WEBAPI'):
    files.extend(sorted((root / folder).rglob('*.py')))
for path in files:
    compile(path.read_bytes(), str(path), 'exec')
print('Checked {} Python sources without writing bytecode.'.format(len(files)))
