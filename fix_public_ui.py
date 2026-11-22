from pathlib import Path
p = Path('/app/web/index.html')
s = p.read_text(encoding='utf-8')
old = "try{$('rememberAccess').checked=localStorage.getItem(rememberKey)==='true';token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}"
new = "try{$('rememberAccess').checked=localStorage.getItem(rememberKey)==='true';if(!publicSession)token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}"
if old not in s:
    raise SystemExit('Could not find the expected token initialization in web/index.html')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
