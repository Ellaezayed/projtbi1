"""Check staged files and reachable Git history without printing secret values."""
import argparse
import re
import subprocess
import sys
from pathlib import PurePosixPath

PRIVATE_DIRECTORIES = {
    ".venv", "node_modules", ".next", "__pycache__", "cache", ".cache",
    "caches", "data", "datasets", "private", "secrets",
}
PRIVATE_SUFFIXES = {
    ".parquet", ".pkl", ".pickle", ".db", ".sqlite", ".sqlite3",
    ".pem", ".key", ".p12", ".pfx", ".jks", ".zip", ".7z", ".tar", ".gz", ".log",
}
PRIVATE_NAMES = {
    ".netrc", ".npmrc", ".pypirc", "credentials.json", "secrets.json",
    "config.local.json", "id_rsa", "id_ed25519",
}
PATTERNS = {
    "private key": r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----",
    "GitHub token": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b",
    "AI provider key": r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b",
    "cloud access key": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "Google API key": r"\bAIza[A-Za-z0-9_-]{35}\b",
    "Slack token": r"\bxox[baprs]-[A-Za-z0-9-]{15,}\b",
    "credential in URL": r"\b[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@",
    "public secret variable": r"\bNEXT_PUBLIC_[A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)[A-Z0-9_]*\b",
}
ASSIGNMENT = re.compile(
    r"""(?im)^[ \t]*(?:export[ \t]+)?["']?([A-Z0-9_.-]*(?:API_KEY|ACCESS_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)[A-Z0-9_.-]*)["']?[ \t]*[:=][ \t]*(.*)$"""
)
SAFE_PLACEHOLDERS = {"", "your_key_here", "your_token_here", "replace_me", "changeme", "example", "placeholder"}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def entries(raw: bytes, oid_index: int):
    for item in raw.decode("utf-8", errors="replace").split("\0"):
        if not item:
            continue
        metadata, path = item.split("\t", 1)
        yield path, metadata.split()[oid_index]


def private_path(path: str) -> bool:
    file = PurePosixPath(path.lower())
    name = file.name
    if name == ".env.example":
        return any(part in PRIVATE_DIRECTORIES for part in file.parts[:-1])
    return (
        any(part in PRIVATE_DIRECTORIES for part in file.parts[:-1])
        or name in PRIVATE_NAMES
        or name.startswith((".env", "secrets.", "credentials."))
        or name.endswith((".local", ".local.yaml", ".local.yml", ".local.toml", ".local.json"))
        or file.suffix in PRIVATE_SUFFIXES
        or ".csv" in file.suffixes
    )


def findings(blob: bytes):
    encoding = "utf-16" if blob.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    source = blob.decode(encoding, errors="replace")
    for label, pattern in PATTERNS.items():
        if re.search(pattern, source):
            yield label
    for match in ASSIGNMENT.finditer(source):
        value = match.group(2).strip().rstrip(",").strip("'\x22")
        if value.lower() in SAFE_PLACEHOLDERS or value.startswith(("${", "$env:", "os.getenv(", "process.env.")):
            continue
        yield "possible literal credential assignment"
        break


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-push", action="store_true")
    args = parser.parse_args()
    tips = []
    if args.pre_push:
        for line in sys.stdin:
            _, local, _, _ = line.split()
            if local.strip("0"):
                tips.append(local)

    paths_and_blobs = set(entries(git("ls-files", "-s", "-z"), 1))
    commits = git("rev-list", "--all", *tips).decode().splitlines()
    failed = False
    for commit in commits:
        paths_and_blobs.update(entries(git("ls-tree", "-r", "-z", commit), 2))
        for label in findings(git("show", "-s", "--format=%B", commit)):
            print(f"Blocked {label} in commit message: {commit[:12]}", file=sys.stderr)
            failed = True

    result = {}
    for path, blob in sorted(paths_and_blobs):
        if private_path(path):
            print(f"Blocked private file: {path}", file=sys.stderr)
            failed = True
            continue
        if blob not in result:
            result[blob] = list(findings(git("cat-file", "blob", blob)))
        for label in result[blob]:
            print(f"Blocked {label}: {path}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    print(f"Public repository scan passed ({len(result)} unique blobs, {len(commits)} commits).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
