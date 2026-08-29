"""Scrub employer/internal identifiers from codebases (ordered: specific -> generic)."""
import os, sys

REPLACEMENTS = [
    # credentials / secrets
    ("cure2000", "ENV_DB_PASSWORD"),
    # server / db names
    ("baseline11x_Curemd", "APP_SERVER_11X"),
    ("MUII_CUREMD", "MUII_DB"),
    ("FHIR_CureMD", "FHIR_DB"),
    ("Release01", "APP_SERVER_10G"),
    # internal endpoints
    ("curemdinc.sharepoint.com", "example.sharepoint.com"),
    ("devops.curemd.com", "devops.example.com"),
    ("fhirendpoint.curemd.net", "fhir.example.net"),
    ("fhir.curemd.com", "fhir.example.com"),
    ("curemd.com", "example.com"),
    ("dev.azure.com/curemd", "dev.azure.com/example"),
    # personal name
    ("Hassan Ali Laghari", "analyst"),
    # product / employer name (last)
    ("CUREMD", "HEALTHOS"),
    ("Curemd", "HealthOS"),
    ("CureMD", "HealthOS"),
    ("curemd", "healthos"),
]

SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
SKIP_FILES = {"bun.lock", "package-lock.json"}
TEXT_EXT = {".py", ".md", ".json", ".ts", ".tsx", ".js", ".jsx", ".bat", ".yaml", ".yml", ".txt", ".toml", ".cfg", ".env", ""}

def scrub(root):
    changed = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES:
                continue
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT and fn != ".env":
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, encoding="utf-8", errors="strict") as f:
                    src = f.read()
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
            out = src
            hits = 0
            for a, b in REPLACEMENTS:
                n = out.count(a)
                if n:
                    out = out.replace(a, b)
                    hits += n
            if hits:
                with open(fp, "w", encoding="utf-8", newline="") as f:
                    f.write(out)
                changed[os.path.relpath(fp, root)] = hits
    return changed

if __name__ == "__main__":
    for root in sys.argv[1:]:
        print(f"=== {root} ===")
        changed = scrub(root)
        total = sum(changed.values())
        for p, n in sorted(changed.items()):
            print(f"  {n:4d}  {p}")
        print(f"  -> {len(changed)} files, {total} replacements")
