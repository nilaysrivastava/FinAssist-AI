"""Seed a fresh checkout; never overwrite existing local customer or account files."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
seed=root/'backend/demo_data'; data=root/'backend/app/data'
data.mkdir(parents=True,exist_ok=True)
for src in seed.glob('*.json'):
    dst=data/src.name
    if not dst.exists():
        shutil.copyfile(src,dst)
        print('Created',dst.relative_to(root))
print('Demo data ready; existing files were retained.')
