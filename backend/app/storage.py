import json
from pathlib import Path
from typing import Any
from app.config import DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)


def _safe_path(filename: str) -> Path:
    path = DATA_DIR / filename
    resolved = path.resolve()
    data_root = DATA_DIR.resolve()
    if data_root not in resolved.parents and resolved != data_root:
        raise ValueError("Unsafe data filename")
    return path


def read_json(filename: str, default: Any):
    path = _safe_path(filename)
    if not path.exists():
        write_json(filename, default)
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(filename: str, data: Any):
    path = _safe_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def append_json_list(filename: str, item: dict):
    data = read_json(filename, [])
    data.append(item)
    write_json(filename, data)
    return item
