import hashlib
import math
import re
from collections import Counter
from typing import Dict, List, Tuple
from app.config import EMBEDDING_DIMS

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "to", "of", "for", "and", "or", "in", "on", "at", "by", "with",
    "me", "my", "i", "you", "your", "it", "this", "that", "from", "as", "be", "can", "do", "does", "how", "what",
    "when", "where", "why", "please", "tell", "about", "using", "into", "there", "their", "should", "would", "could",
}

DOMAIN_EXPANSIONS = {
    "emi": ["equated", "monthly", "installment", "instalment", "due", "repayment"],
    "noc": ["no", "objection", "certificate", "closure", "document"],
    "foreclosure": ["preclosure", "loan", "closure", "outstanding", "quote"],
    "payment": ["repayment", "receipt", "transaction", "upi", "autodebit", "debit"],
    "customer": ["borrower", "applicant", "user", "profile"],
    "overdue": ["late", "dpd", "delay", "penalty"],
    "ticket": ["service", "request", "case", "support", "escalation"],
    "portal": ["login", "download", "dashboard", "self", "service"],
    "employee": ["agent", "internal", "ops", "workflow"],
}

def tokenize(text: str) -> List[str]:
    tokens = [t for t in TOKEN_RE.findall((text or "").lower()) if len(t) > 1 and t not in STOPWORDS]
    expanded = []
    token_set = set(tokens)
    for t in tokens:
        expanded.append(t)
        if t in DOMAIN_EXPANSIONS:
            expanded.extend(DOMAIN_EXPANSIONS[t])
    joined = " ".join(tokens)
    if "no objection certificate" in joined:
        expanded.extend(["noc", "closure", "document"])
    if "auto debit" in joined or "autodebit" in joined:
        expanded.extend(["nach", "mandate", "payment"])
    return expanded


def _hash_feature(feature: str, dims: int = EMBEDDING_DIMS) -> int:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % dims


def text_embedding(text: str, dims: int = EMBEDDING_DIMS) -> List[Tuple[int, float]]:
    tokens = tokenize(text)
    features = Counter(tokens)
    for t in tokens:
        if len(t) >= 5:
            for i in range(len(t) - 2):
                features[f"tri:{t[i:i+3]}"] += 0.25
    hashed = Counter()
    for feat, val in features.items():
        hashed[_hash_feature(feat, dims)] += float(val)
    norm = math.sqrt(sum(v * v for v in hashed.values())) or 1.0
    return sorted((idx, round(val / norm, 6)) for idx, val in hashed.items() if val)


def sparse_to_dict(vec: List[Tuple[int, float]]) -> Dict[int, float]:
    return {int(i): float(v) for i, v in vec}


def cosine_sparse(a: Dict[int, float], b: Dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())
