"""Create an isolated environment beside this script; no global pip changes."""

import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    if sys.version_info[:2] != (3, 11):
        raise SystemExit('Use Python 3.11 for the tested Windows environment.')
    cache = ROOT / '.pip-cache'
    temp = ROOT / '.tmp'
    temp.mkdir(exist_ok=True)
    cache.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(TEMP=str(temp), TMP=str(temp), PIP_CACHE_DIR=str(cache))
    python = ROOT / '.venv' / 'Scripts' / 'python.exe'
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(ROOT / '.venv')
    subprocess.run([str(python), '-m', 'pip', 'install', '--only-binary=:all:', '-r', str(ROOT/'requirements-lock.txt')], env=env, check=True)
    print('Ready. Double-click start.cmd to open the app.')
