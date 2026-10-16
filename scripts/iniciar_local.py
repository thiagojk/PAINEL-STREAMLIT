"""Auxiliar do iniciador Windows: instala somente quando necessário."""
from pathlib import Path
import hashlib
import importlib.util
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    requirements = root / 'requirements.txt'
    marker = Path(sys.prefix) / '.pqavs-requirements.sha256'
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    modules = ['streamlit', 'pandas', 'numpy', 'pyarrow', 'plotly', 'openpyxl']
    installed = all(importlib.util.find_spec(name) for name in modules)
    if not installed or not marker.exists() or marker.read_text() != digest:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements)], check=True, cwd=root)
        marker.write_text(digest)
    subprocess.run([sys.executable, '-m', 'pip', 'check'], check=True, cwd=root)
    return subprocess.call([sys.executable, '-m', 'streamlit', 'run', 'app.py', '--server.headless=false'], cwd=root)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError) as error:
        print(f'Falha ao preparar o painel: {error}', file=sys.stderr)
        raise SystemExit(1)
