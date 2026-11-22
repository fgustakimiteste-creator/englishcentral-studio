"""Patch the Playwright Python CDP call in the Render image."""
from pathlib import Path
import os

root = Path(os.getenv("EC_SOURCE_ROOT", "/app"))
path = root / "servidor.py"
source = path.read_text(encoding="utf-8")
old = "connect_over_cdp(endpoint,timeout=25000,no_defaults=True)"
new = "connect_over_cdp(endpoint,timeout=25000)"
if old in source:
    source = source.replace(old, new, 1)
elif new not in source:
    raise SystemExit("Não encontrei a chamada Playwright connect_over_cdp esperada.")
if "connect_over_cdp(endpoint,timeout=25000,no_defaults=True)" in source:
    raise SystemExit("A chamada CDP incompatível permaneceu.")
path.write_text(source, encoding="utf-8")
