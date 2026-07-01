import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from app.config import CHUNK_OVERLAP_WORDS, CHUNK_TARGET_WORDS, KB_INDEX_FILE, KB_SOURCE_DIR
from app.embeddings import text_embedding, tokenize

try:
    from pypdf import PdfReader
except Exception:  # pypdf is optional until a PDF is indexed
    PdfReader = None

META_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
HEADING_RE = re.compile(r"^(#{1,4}\s+.+|[A-Z][A-Z0-9 &/()\-]{8,}:?)$")


def read_source(path: Path) -> Tuple[Dict[str, str], str]:
    if path.suffix.lower() == ".pdf":
        if PdfReader is None:
            raise RuntimeError("pypdf is not installed. Run: pip install pypdf")
        reader = PdfReader(str(path))
        pages = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"\n\n[Page {idx + 1}]\n{text}")
        raw = "\n".join(pages)
        meta = {
            "doc_id": path.stem.upper().replace("-", "_"),
            "title": path.stem.replace("_", " ").replace("-", " ").title(),
            "category": "policy",
            "access": "public",
            "version": "unknown",
            "effective_date": "unknown",
        }
        return meta, raw

    raw = path.read_text(encoding="utf-8")
    meta = {}
    match = META_RE.match(raw)
    if match:
        meta_text = match.group(1)
        raw = raw[match.end():]
        for line in meta_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

    meta.setdefault("doc_id", path.stem.upper().replace("-", "_"))
    meta.setdefault("title", path.stem.replace("_", " ").replace("-", " ").title())
    meta.setdefault("category", "policy")
    meta.setdefault("access", "public")
    meta.setdefault("version", "unknown")
    meta.setdefault("effective_date", "unknown")
    meta.setdefault("source_file", str(path.relative_to(KB_SOURCE_DIR)))
    return meta, raw


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n\s*Page\s+\d+\s*\n", "\n", text, flags=re.I)
    text = re.sub(r"(?i)confidential\s*\|\s*internal\s*use\s*only", "", text)
    text = re.sub(r"[\t\x0b\x0c]+", " ", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(lines).strip()


def split_sections(text: str) -> List[Tuple[str, str]]:
    sections = []
    current_title = "General"
    current_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            current_lines.append("")
            continue
        is_heading = False
        if stripped.startswith("#"):
            is_heading = True
        elif HEADING_RE.match(stripped) and len(stripped.split()) <= 12:
            is_heading = True
        if is_heading:
            body = "\n".join(current_lines).strip()
            if body:
                sections.append((current_title, body))
            current_title = stripped.lstrip("#").strip().rstrip(":")
            current_lines = []
        else:
            current_lines.append(stripped)
    body = "\n".join(current_lines).strip()
    if body:
        sections.append((current_title, body))
    return sections or [("General", text)]


def words(text: str) -> List[str]:
    return re.findall(r"\S+", text)


def semantic_chunks(section_text: str, target_words: int, overlap_words: int) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section_text) if p.strip()]
    chunks = []
    current = []
    count = 0
    for para in paragraphs:
        w = words(para)
        if current and count + len(w) > target_words:
            chunk = "\n\n".join(current).strip()
            if chunk:
                chunks.append(chunk)
            overlap = " ".join(words(chunk)[-overlap_words:]) if overlap_words else ""
            current = [overlap, para] if overlap else [para]
            count = len(words(overlap)) + len(w)
        else:
            current.append(para)
            count += len(w)

    if current:
        chunks.append("\n\n".join(current).strip())

    final_chunks = []
    for chunk in chunks:
        w = words(chunk)
        if len(w) <= target_words * 1.4:
            final_chunks.append(chunk)
            continue
        step = max(target_words - overlap_words, 120)
        for start in range(0, len(w), step):
            part = " ".join(w[start:start + target_words]).strip()
            if len(part.split()) >= 45:
                final_chunks.append(part)
    return final_chunks


def build_index(source_dir: Path = KB_SOURCE_DIR) -> dict:
    source_dir.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in source_dir.rglob("*") if p.suffix.lower() in {".txt", ".md", ".pdf"}])
    chunks = []
    documents = []
    for path in files:
        meta, raw = read_source(path)
        access = meta.get("access", "public").lower().strip()
        indexable = meta.get("indexable", "true").lower().strip() != "false"
        doc = {
            "doc_id": meta["doc_id"],
            "title": meta["title"],
            "category": meta.get("category", "policy"),
            "access": access,
            "version": meta.get("version", "unknown"),
            "effective_date": meta.get("effective_date", "unknown"),
            "source_file": meta.get("source_file", str(path.relative_to(source_dir))),
            "indexable": indexable,
        }
        documents.append(doc)
        if not indexable or access == "confidential":
            continue
        clean = clean_text(raw)
        for section_title, section_body in split_sections(clean):
            for part_idx, chunk_text in enumerate(semantic_chunks(section_body, CHUNK_TARGET_WORDS, CHUNK_OVERLAP_WORDS), start=1):
                chunk_id = f"{doc['doc_id']}::{len([c for c in chunks if c['doc_id'] == doc['doc_id']]) + 1:03d}"
                indexed_text = f"{doc['title']} {doc['category']} {section_title}\n{chunk_text}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "access": access,
                    "version": doc["version"],
                    "effective_date": doc["effective_date"],
                    "source_file": doc["source_file"],
                    "section": section_title,
                    "text": chunk_text,
                    "word_count": len(words(chunk_text)),
                    "tokens": tokenize(indexed_text),
                    "embedding": text_embedding(indexed_text),
                    "citation": f"{doc['title']} / {section_title} / {chunk_id}",
                })
    index = {
        "schema_version": "2.0",
        "description": "Read-only local RAG index generated from backend/app/kb_sources. Do not edit from frontend.",
        "chunk_target_words": CHUNK_TARGET_WORDS,
        "chunk_overlap_words": CHUNK_OVERLAP_WORDS,
        "documents": documents,
        "chunks": chunks,
    }
    KB_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    KB_INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return index


def ensure_index_exists() -> None:
    if not KB_INDEX_FILE.exists():
        build_index()


def main():
    parser = argparse.ArgumentParser(description="Build FinAssist local RAG vector index from project-folder KB sources.")
    parser.add_argument("--source-dir", default=str(KB_SOURCE_DIR))
    args = parser.parse_args()
    index = build_index(Path(args.source_dir))
    print(f"Indexed {len(index['documents'])} documents and {len(index['chunks'])} chunks into {KB_INDEX_FILE}")


if __name__ == "__main__":
    main()
