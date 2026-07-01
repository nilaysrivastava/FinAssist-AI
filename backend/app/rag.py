import math
from collections import Counter, defaultdict
from functools import lru_cache
from typing import Dict, List
from app.config import KB_INDEX_FILE
from app.embeddings import cosine_sparse, sparse_to_dict, text_embedding, tokenize
from app.ingest import ensure_index_exists


def _embedding_dict(chunk: dict) -> Dict[int, float]:
    return sparse_to_dict(chunk.get("embedding", []))


@lru_cache(maxsize=1)
def load_index() -> dict:
    ensure_index_exists()
    import json
    with KB_INDEX_FILE.open("r", encoding="utf-8") as f:
        index = json.load(f)
    chunks = index.get("chunks", [])
    df = defaultdict(int)
    for ch in chunks:
        for t in set(ch.get("tokens", [])):
            df[t] += 1
    n = max(len(chunks), 1)
    avgdl = sum(len(ch.get("tokens", [])) for ch in chunks) / n
    idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
    index["_idf"] = idf
    index["_avgdl"] = avgdl
    for ch in chunks:
        ch["_embedding_dict"] = _embedding_dict(ch)
    return index


def bm25_score(query_tokens: List[str], doc_tokens: List[str], idf: dict, avgdl: float) -> float:
    tf = Counter(doc_tokens)
    score = 0.0
    k1 = 1.5
    b = 0.75
    dl = len(doc_tokens) or 1
    for q in query_tokens:
        if q not in tf:
            continue
        freq = tf[q]
        denom = freq + k1 * (1 - b + b * dl / max(avgdl, 1))
        score += idf.get(q, 0.0) * (freq * (k1 + 1) / denom)
    return score


def _normalize(rows: List[dict], key: str) -> None:
    vals = [float(x.get(key, 0.0)) for x in rows]
    mn = min(vals or [0.0])
    mx = max(vals or [0.0])
    for x in rows:
        x[key + "_norm"] = 0.0 if mx == mn else (float(x.get(key, 0.0)) - mn) / (mx - mn)


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _dedupe_context(rows: List[dict], max_per_doc: int = 2) -> List[dict]:
    selected = []
    per_doc = Counter()
    for row in rows:
        if per_doc[row["doc_id"]] >= max_per_doc:
            continue
        if any(_jaccard(row.get("tokens", []), s.get("tokens", [])) > 0.86 for s in selected):
            continue
        selected.append(row)
        per_doc[row["doc_id"]] += 1
    return selected


def rerank(query: str, rows: List[dict]) -> List[dict]:
    q_tokens = set(tokenize(query))
    q = query.lower().strip()
    for r in rows:
        title_tokens = set(tokenize(r.get("title", "") + " " + r.get("section", "") + " " + r.get("category", "")))
        exact = 0.18 if q and q in r.get("text", "").lower() else 0.0
        title = 0.16 if q_tokens & title_tokens else 0.0
        policy_boost = 0.08 if any(t in q_tokens for t in ["policy", "process", "workflow", "rule"]) else 0.0
        r["rerank_score"] = r["hybrid_score"] + exact + title + policy_boost
    return sorted(rows, key=lambda x: x["rerank_score"], reverse=True)


def search_kb(query: str, role: str = "customer", top_k: int = 6) -> List[dict]:
    index = load_index()
    chunks = index.get("chunks", [])
    q_tokens = tokenize(query)
    q_vec = sparse_to_dict(text_embedding(query))
    rows = []
    for ch in chunks:
        access = ch.get("access", "public")
        if access == "internal" and role != "employee":
            continue
        if access == "confidential":
            continue
        doc_tokens = ch.get("tokens", [])
        bm = bm25_score(q_tokens, doc_tokens, index["_idf"], index["_avgdl"])
        sem = cosine_sparse(q_vec, ch.get("_embedding_dict", {}))
        overlap = len(set(q_tokens) & set(doc_tokens)) / max(len(set(q_tokens)), 1)
        rows.append({
            **{k: v for k, v in ch.items() if not k.startswith("_") and k not in {"embedding"}},
            "bm25": bm,
            "semantic": sem,
            "overlap": overlap,
        })
    if not rows:
        return []
    _normalize(rows, "bm25")
    _normalize(rows, "semantic")
    for r in rows:
        r["hybrid_score"] = 0.45 * r["bm25_norm"] + 0.40 * r["semantic_norm"] + 0.15 * r["overlap"]
    candidates = sorted(rows, key=lambda x: x["hybrid_score"], reverse=True)[: max(top_k * 5, 20)]
    ranked = _dedupe_context(rerank(query, candidates))
    output = []
    for r in ranked[:top_k]:
        output.append({
            "source_id": r["doc_id"],
            "chunk_id": r["chunk_id"],
            "title": r["title"],
            "category": r["category"],
            "section": r.get("section"),
            "access": r.get("access", "public"),
            "score": round(float(r.get("rerank_score", 0.0)), 4),
            "citation": r.get("citation"),
            "content": r["text"],
        })
    return output


def refresh_index():
    load_index.cache_clear()
    load_index()
