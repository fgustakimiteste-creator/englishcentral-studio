from pathlib import Path
p = Path('/app/servidor.py')
s = p.read_text(encoding='utf-8')
old = 'from fastapi import Depends, FastAPI, Header, HTTPException'
new = 'from fastapi import Depends, FastAPI, Header, HTTPException, Request'
if old not in s:
    raise SystemExit('FastAPI import line not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
