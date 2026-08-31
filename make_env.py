"""Generate baqa/.env from central secrets (C:/Users/LOQ/secrets/.env.central).

Keys stay local; the file is gitignored. Written once per user instruction,
2026-08-31. Safe to re-run (idempotent).
"""
import os

CENTRAL = r"C:\Users\LOQ\secrets\.env.central"
TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baqa", ".env")

WANT = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENROUTER_API_KEY",
        "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "GEMINI_API_KEY",
        "GROQ_API_KEY", "DEEPSEEK_API_KEY", "MISTRAL_API_KEY", "COHERE_API_KEY"]

keys = {}
with open(CENTRAL, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            if v.strip():
                keys[k.strip()] = v.strip()

with open(TARGET, "w", encoding="utf-8") as f:
    f.write("# Generated from central secrets 2026-08-31 - gitignored, never commit\n")
    for k in WANT:
        if k in keys:
            f.write(f"{k}={keys[k]}\n")

found = [k for k in WANT if k in keys]
print("wrote", TARGET, "with", len(found), "keys:", ", ".join(found))
