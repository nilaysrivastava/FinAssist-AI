from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".idea",
    ".vscode",
}

TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".env",
    ".example",
    ".css",
    ".html",
    ".yml",
    ".yaml",
    ".toml",
}

REPLACEMENTS = [
    ("FinAssist AI", "FinAssist AI"),
    ("FINASSIST AI", "FINASSIST AI"),
    ("FinAssist", "FinAssist"),
    ("finassist", "finassist"),
    ("Demo Finance Platform", "Demo Finance Platform"),
    ("Demo Finance Platform", "Demo Finance Platform"),
    ("Demo Finance", "Demo Finance"),
    ("Scooter Model X", "Scooter Model X"),
    ("Scooter Model X", "Scooter Model X"),
    ("FinAssist_NOC_FORECLOSURE_POLICY", "FINASSIST_NOC_FORECLOSURE_POLICY"),
    ("FinAssist_EMI_REPAYMENT_POLICY", "FINASSIST_EMI_REPAYMENT_POLICY"),
    ("FinAssist_PORTAL_FAQ", "FINASSIST_PORTAL_FAQ"),
    ("FinAssist_PRIVACY_SECURITY_POLICY", "FINASSIST_PRIVACY_SECURITY_POLICY"),
    ("FinAssist Customer Portal FAQ", "FinAssist Customer Portal FAQ"),
    ("FinAssist Customer Portal", "FinAssist Customer Portal"),
    ("FinAssist GenAI Chatbot", "FinAssist AI GenAI Chatbot"),
    ("FinAssist GenAI", "FinAssist AI"),
]

REGEX_REPLACEMENTS = [
    (re.compile(r"\bTVS\b"), "Demo"),
    (re.compile(r"\btvs\b"), "demo"),
]


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def replace_content(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return

    original = text

    for old, new in REPLACEMENTS:
        text = text.replace(old, new)

    for pattern, new in REGEX_REPLACEMENTS:
        text = pattern.sub(new, text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"updated: {path.relative_to(ROOT)}")


def rename_paths() -> None:
    paths = sorted(
        [p for p in ROOT.rglob("*") if not should_skip(p)],
        key=lambda p: len(p.parts),
        reverse=True,
    )

    for path in paths:
        name = path.name
        new_name = name

        for old, new in [
            ("finassist", "finassist"),
            ("FinAssist", "FinAssist"),
            ("demo", "finassist"),
        ]:
            new_name = new_name.replace(old, new)

        if new_name != name:
            new_path = path.with_name(new_name)

            if not new_path.exists():
                path.rename(new_path)
                print(f"renamed: {path.relative_to(ROOT)} -> {new_path.relative_to(ROOT)}")


def main() -> None:
    for path in ROOT.rglob("*"):
        if should_skip(path) or not path.is_file() or not is_text_file(path):
            continue

        replace_content(path)

    rename_paths()

    print("\nSanitization complete. Run ripgrep audit next.")


if __name__ == "__main__":
    main()