"""Habilita apenas o acesso automático por sessão privada no EnglishCentral Studio.

O token real continua no arquivo token_painel.txt do perfil, dentro do servidor.
O navegador recebe somente um cookie HttpOnly, Secure, assinado e isolado por
visitante. O gateway lê o token no servidor e o injeta na chamada interna.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import py_compile
import re
import sys
import time
import uuid
from pathlib import Path

COOKIE_NAME = "ec_private_session"
SESSION_MAX_AGE = 365 * 24 * 60 * 60


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    if new in source:
        return
    if old not in source:
        raise SystemExit(f"Não foi possível aplicar {label}: trecho original não encontrado em {path.name}.")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def patch_mobile(root: Path) -> None:
    path = root / "mobile_app.py"
    source = path.read_text(encoding="utf-8")

    imports_old = "import asyncio\nimport hmac\nimport os\nimport re\n"
    imports_new = "import asyncio\nimport hashlib\nimport hmac\nimport os\nimport re\nimport time\nimport uuid\n"
    if imports_new not in source:
        if imports_old not in source:
            raise SystemExit("Imports do mobile_app.py mudaram; patch interrompido para preservar o arquivo.")
        source = source.replace(imports_old, imports_new, 1)
    marker = "PROFILE_ID = re.compile(r'principal|pessoa(?:[2-9]|[1-9]\\d+)')\n"
    helper = marker + f'''PUBLIC_COOKIE = "{COOKIE_NAME}"
PUBLIC_SESSION_ID = re.compile(r"[a-f0-9]{{32}}")
PUBLIC_SESSION_MAX_AGE = {SESSION_MAX_AGE}


def create_public_session_id() -> str:
    return uuid.uuid4().hex


def _public_session_secret() -> bytes:
    secret = os.getenv("EC_PUBLIC_SESSION_SECRET", "").encode("utf-8")
    if len(secret) < 32:
        raise RuntimeError("EC_PUBLIC_SESSION_SECRET precisa ter pelo menos 32 caracteres.")
    return secret


def make_public_session_cookie(session_id: str) -> str:
    if not PUBLIC_SESSION_ID.fullmatch(session_id):
        raise ValueError("Identificador de sessão privada inválido.")
    issued = str(int(time.time()))
    payload = session_id + "." + issued
    signature = hmac.new(_public_session_secret(), payload.encode("ascii"), hashlib.sha256).hexdigest()
    return payload + "." + signature


def read_public_session_id(request: Request) -> str | None:
    raw = request.cookies.get(PUBLIC_COOKIE, "")
    try:
        session_id, issued_raw, signature = raw.split(".", 2)
        issued = int(issued_raw)
    except (ValueError, TypeError):
        return None
    now = int(time.time())
    if not PUBLIC_SESSION_ID.fullmatch(session_id) or issued > now + 60 or now - issued > PUBLIC_SESSION_MAX_AGE:
        return None
    payload = session_id + "." + str(issued)
    try:
        expected = hmac.new(_public_session_secret(), payload.encode("ascii"), hashlib.sha256).hexdigest()
    except RuntimeError:
        return None
    return session_id if hmac.compare_digest(signature, expected) else None


def public_profile_manager(project_root: Path, session_id: str):
    """Cada navegador recebe uma raiz de dados e uma lista de Pessoas independentes."""
    if not PUBLIC_SESSION_ID.fullmatch(session_id):
        raise HTTPException(401, "Sessão privada inválida.")
    from perfis import ProfileManager
    profiles_root = Path(os.getenv("EC_PROFILES_ROOT", str(Path(project_root) / ".dados_locais")))
    tenant_root = profiles_root / "public_sessions" / session_id
    tenant_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return ProfileManager(tenant_root, Path(project_root), public_session_id=session_id)
'''
    if helper not in source:
        if marker not in source:
            raise SystemExit("Constante PROFILE_ID não encontrada em mobile_app.py.")
        source = source.replace(marker, helper, 1)

    route_start = """    @app.api_route('/p/{profile_id}/{path:path}', methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'])
    async def profile_panel(profile_id: str, path: str, request: Request):
"""
    route_end_line = "            raise HTTPException(502, 'O painel desta pessoa está indisponível. Tente novamente; o histórico permanece salvo.') from exc\n"
    i = source.find(route_start)
    if i < 0:
        if "public_sessions = os.getenv('EC_PUBLIC_SESSIONS', '0') == '1'" in source:
            path.write_text(source, encoding="utf-8")
            return
        raise SystemExit("Rota do painel por perfil não encontrada em mobile_app.py.")
    j0 = source.find(route_end_line, i)
    if j0 < 0:
        raise SystemExit("Final da rota do painel não encontrado em mobile_app.py.")
    j = j0 + len(route_end_line)

    new_route = f'''    @app.api_route('/p/{{profile_id}}/{{path:path}}', methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'])
    async def profile_panel(profile_id: str, path: str, request: Request):
        if not config.enabled or not PROFILE_ID.fullmatch(profile_id):
            raise HTTPException(404, 'Painel não encontrado.')

        public_sessions = os.getenv('EC_PUBLIC_SESSIONS', '0') == '1'
        session_id = read_public_session_id(request) if public_sessions else None
        if public_sessions:
            if not session_id:
                if request.method in {'GET', 'HEAD'} and path == '':
                    return Response(status_code=303, headers={'Location': '/'})
                raise HTTPException(401, 'Sessão privada ausente ou expirada. Abra o endereço principal novamente.')
            if path == 'api/session/logout' and request.method == 'POST':
                response = Response(status_code=204)
                response.delete_cookie(PUBLIC_COOKIE, path='/', secure=True, httponly=True, samesite='lax')
                return response
            worker_session = os.getenv('EC_PUBLIC_SESSION_ID', '')
            if worker_session and not hmac.compare_digest(worker_session, session_id):
                raise HTTPException(403, 'Esta sessão pertence a outro navegador.')
            manager = public_profile_manager(root, session_id)
        else:
            manager = manager_factory()

        people = await asyncio.to_thread(manager.list)
        if profile_id not in {{person['id'] for person in people}}:
            raise HTTPException(404, 'Pessoa não encontrada nesta sessão.')
        if request.method in {{'GET', 'HEAD'}} and path == '':
            return FileResponse(root / 'web' / 'index.html', media_type='text/html', headers={{'Cache-Control': 'no-store'}})
        if not path.startswith('api/') or '..' in path or '\\\\' in path or '?' in path or '#' in path:
            raise HTTPException(404, 'Endereço não encontrado.')

        token = ''
        if not public_sessions:
            token = request.headers.get('x-ec-token', '')
            try:
                expected = (manager.data_dir(profile_id) / 'token_painel.txt').read_text('utf-8').strip()
            except OSError:
                expected = ''
            if not expected or not token or not hmac.compare_digest(token, expected):
                raise HTTPException(401, 'Token inválido para esta pessoa.')

        try:
            info = await asyncio.to_thread(manager.open, profile_id)
            parsed = urlsplit(info['url'])
            if parsed.hostname != '127.0.0.1' or not parsed.port:
                raise ValueError('Endereço interno inválido')
            if public_sessions:
                token = (manager.data_dir(profile_id) / 'token_painel.txt').read_text('utf-8').strip()
                if not token:
                    raise RuntimeError('Token privado do perfil não foi criado.')

            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 65536:
                    raise HTTPException(413, 'Solicitação muito grande.')
            headers = {{'X-EC-Token': token}}
            if request.headers.get('content-type'):
                headers['Content-Type'] = request.headers['content-type']
            async with httpx.AsyncClient(timeout=55, trust_env=False, follow_redirects=False) as client:
                response = await client.request(request.method, f'http://127.0.0.1:{{parsed.port}}/' + path,
                                                params=request.query_params, headers=headers, content=bytes(body))
            return Response(response.content, status_code=response.status_code,
                            media_type=response.headers.get('content-type'), headers={{'Cache-Control': 'no-store'}})
        except HTTPException:
            raise
        except (OSError, ValueError, RuntimeError, httpx.HTTPError) as exc:
            raise HTTPException(502, 'O painel desta pessoa está indisponível. Tente novamente; o histórico permanece salvo.') from exc
'''
    source = source[:i] + new_route + source[j:]
    path.write_text(source, encoding="utf-8")


def patch_profiles(root: Path) -> None:
    path = root / "perfis.py"
    old_init = """    def __init__(self, root: Path, project: Path):
        self.root, self.project = Path(root), Path(project)
        self.file = self.root / 'perfis.json'
"""
    new_init = """    def __init__(self, root: Path, project: Path, public_session_id: str | None = None):
        self.root, self.project = Path(root), Path(project)
        self.public_session_id = public_session_id or os.getenv('EC_PUBLIC_SESSION_ID', '')
        self.file = self.root / 'perfis.json'
"""
    replace_once(path, old_init, new_init, "isolamento de dados entre navegadores")

    old_env = """                env.update(EC_DATA_DIR=str(directory), EC_PROFILES_ROOT=str(self.root),
                           EC_PROFILE_ID=profile_id, EC_PORT=str(port))
"""
    new_env = """                env.update(EC_DATA_DIR=str(directory), EC_PROFILES_ROOT=str(self.root),
                           EC_PROFILE_ID=profile_id, EC_PORT=str(port))
                if self.public_session_id:
                    env['EC_PUBLIC_SESSION_ID'] = self.public_session_id
                    # A chave HMAC fica somente no processo público principal.
                    env.pop('EC_PUBLIC_SESSION_SECRET', None)
"""
    replace_once(path, old_env, new_env, "propagação da sessão privada sem propagar sua chave")

    
def patch_server(root: Path) -> None:
    path = root / "servidor.py"
    replace_once(path,
        "from fastapi import Depends, FastAPI, Header, HTTPException\n",
        "from fastapi import Depends, FastAPI, Header, HTTPException, Request\n",
        "Request para cookie privado")
    replace_once(path,
        "from mobile_app import RemoteConfig, install_mobile_routes\n",
        "from mobile_app import (RemoteConfig, install_mobile_routes, create_public_session_id,\n"
        "                         make_public_session_cookie, read_public_session_id, public_profile_manager, PUBLIC_COOKIE)\n",
        "helpers de sessão privada")

    old_home = """@app.api_route('/', methods=['GET', 'HEAD'])
async def home():
    return FileResponse(ROOT / 'web' / 'index.html', media_type='text/html', headers={'Cache-Control': 'no-store'})
"""
    new_home = f"""@app.api_route('/', methods=['GET', 'HEAD'])
async def home(request: Request):
    public_sessions = REMOTE_CONFIG.enabled and os.getenv('EC_PUBLIC_SESSIONS', '0') == '1'
    if public_sessions and not os.getenv('EC_PUBLIC_SESSION_ID'):
        from fastapi.responses import RedirectResponse
        session_id = read_public_session_id(request)
        if not session_id:
            session_id = create_public_session_id()
            manager = public_profile_manager(ROOT, session_id)
            await asyncio.to_thread(manager.list)
            response = RedirectResponse('/p/principal/', status_code=303)
            response.set_cookie(PUBLIC_COOKIE, make_public_session_cookie(session_id),
                                max_age={SESSION_MAX_AGE}, httponly=True, secure=True,
                                samesite='lax', path='/')
            return response
        manager = public_profile_manager(ROOT, session_id)
        await asyncio.to_thread(manager.list)
        response = RedirectResponse('/p/principal/', status_code=303)
        response.set_cookie(PUBLIC_COOKIE, make_public_session_cookie(session_id),
                            max_age=SESSION_MAX_AGE, httponly=True, secure=True,
                            samesite='lax', path='/')
        return response
    return FileResponse(ROOT / 'web' / 'index.html', media_type='text/html', headers={{'Cache-Control': 'no-store'}})
"""
    replace_once(path, old_home, new_home, "inicialização automática da sessão privada")
    
    old_profile_url = """        if REMOTE_CONFIG.enabled:
            # As sessões continuam separadas; o celular acessa todas pelo HTTPS
            # do painel, sem tentar abrir o próprio 127.0.0.1.
            fragment = urlparse(result['url']).fragment
            result['url'] = f'/p/{profile_id}/#{fragment}'
"""
    new_profile_url = """        if REMOTE_CONFIG.enabled:
            if os.getenv('EC_PUBLIC_SESSION_ID'):
                result['url'] = f'/p/{profile_id}/'
            else:
                fragment = urlparse(result['url']).fragment
                result['url'] = f'/p/{profile_id}/#{fragment}'
"""
    replace_once(path, old_profile_url, new_profile_url, "remover token da URL pública de perfis")


def patch_frontend(root: Path) -> None:
    path = root / "web" / "index.html"
    s = path.read_text(encoding="utf-8")

    def once(old: str, new: str, label: str) -> None:
        nonlocal s
        if new in s:
            return
        if old not in s:
            raise SystemExit(f"Não foi possível aplicar {label}: trecho original não encontrado em index.html.")
        s = s.replace(old, new, 1)

    # Preserve all existing UI state. Only change where the API base path comes from.
    if "const publicSession=" not in s:
        base_line_start = s.find("const panelBase=/")
        if base_line_start < 0:
            raise SystemExit("Linha panelBase original não encontrada; patch interrompido.")
        base_line_end = s.find("\n", base_line_start)
        if base_line_end < 0:
            raise SystemExit("Fim da declaração panelBase não encontrado.")
        original_base = s[base_line_start:base_line_end]
        if not original_base.startswith("const panelBase=/"):
            raise SystemExit("Declaração panelBase inesperada.")
        expression = original_base[len("const panelBase="):]
        replacement = (
            r"const publicSession=/^\/p\/(principal|pessoa(?:[2-9]|[1-9]\d+))\/$/.test(location.pathname);" + "\n"
            "const panelBase=publicSession?location.pathname:" + expression + "\n"
            "if(publicSession)token='public-session-cookie';"
        )
        s = s[:base_line_start] + replacement + s[base_line_end:]

    base_load = "try{$('rememberAccess').checked=localStorage.getItem(rememberKey)==='true';token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}\n"
    hosted_load = "try{$('rememberAccess').checked=!hostedBridgePage&&localStorage.getItem(rememberKey)==='true';if(!hostedBridgePage)token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}"
    new_load_base = "try{$('rememberAccess').checked=publicSession?true:localStorage.getItem(rememberKey)==='true';if(!publicSession)token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}\n"
    new_load_hosted = "try{$('rememberAccess').checked=publicSession?true:(!hostedBridgePage&&localStorage.getItem(rememberKey)==='true');if(!publicSession&&!hostedBridgePage)token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}"
    if new_load_base not in s and new_load_hosted not in s:
        if base_load in s:
            s = s.replace(base_load, new_load_base, 1)
        elif hosted_load in s:
            s = s.replace(hosted_load, new_load_hosted, 1)
        else:
            raise SystemExit("Leitura do token local não encontrada; patch interrompido.")

    # Do not save the sentinel or the real private token in browser storage.
    if "if(publicSession){text('deviceAccessStatus'" not in s:
        base_store = "function storeAccess(){\n try{if(token)sessionStorage.setItem(tokenKey,token);else sessionStorage.removeItem(tokenKey)}catch{}\n"
        hosted_store = "function storeAccess(){\n if(hostedBridgePage||localBridgeActive){text('deviceAccessStatus','O acesso ao conector local não é salvo neste navegador.');return}\n try{if(token)sessionStorage.setItem(tokenKey,token);else sessionStorage.removeItem(tokenKey)}catch{}"
        if base_store in s:
            s = s.replace(base_store,
                "function storeAccess(){\n if(publicSession){text('deviceAccessStatus','Sessão privada autenticada automaticamente pelo servidor neste navegador.');return}\n try{if(token)sessionStorage.setItem(tokenKey,token);else sessionStorage.removeItem(tokenKey)}catch{}\n",1)
        elif hosted_store in s:
            s = s.replace(hosted_store,
                "function storeAccess(){\n if(publicSession){text('deviceAccessStatus','Sessão privada autenticada automaticamente pelo servidor neste navegador.');return}\n if(hostedBridgePage||localBridgeActive){text('deviceAccessStatus','O acesso ao conector local não é salvo neste navegador.');return}\n try{if(token)sessionStorage.setItem(tokenKey,token);else sessionStorage.removeItem(tokenKey)}catch{}",1)
        else:
            raise SystemExit("Função storeAccess não encontrada; patch interrompido.")

    base_hash = "if(location.hash.startsWith('#token=')){try{token=decodeURIComponent(location.hash.substring(7));storeAccess();history.replaceState(null,'',location.pathname+location.search)}catch{}}"
    hosted_hash = "if(!hostedBridgePage&&location.hash.startsWith('#token=')){try{token=decodeURIComponent(location.hash.substring(7));storeAccess();history.replaceState(null,'',location.pathname+location.search)}catch{}}else if(hostedBridgePage&&location.hash){history.replaceState(null,'',location.pathname+location.search)"
    if not ("if(!publicSession" in s and "location.hash.startsWith('#token=')" in s):
        if base_hash in s:
            s = s.replace(base_hash,
                "if(!publicSession&&location.hash.startsWith('#token=')){try{token=decodeURIComponent(location.hash.substring(7));storeAccess();history.replaceState(null,'',location.pathname+location.search)}catch{}}",1)
        elif hosted_hash in s:
            s = s.replace(hosted_hash,
                "if(!publicSession&&!hostedBridgePage&&location.hash.startsWith('#token=')){try{token=decodeURIComponent(location.hash.substring(7));storeAccess();history.replaceState(null,'',location.pathname+location.search)}catch{}}else if(hostedBridgePage&&location.hash){history.replaceState(null,'',location.pathname+location.search)",1)
        else:
            raise SystemExit("Leitura de token via fragmento não encontrada; patch interrompido.")

    # The existing "Esquecer este acesso" action also clears the automatic session cookie.
    if "async function logoutPrivateSession" not in s:
        marker = "function text(id,value){"
        logout_js = "async function logoutPrivateSession(){try{await fetch(panelBase+'api/session/logout',{method:'POST',headers:{'Content-Type':'application/json'}})}finally{location.replace('/')}}\n"
        if marker not in s:
            raise SystemExit("Ponto de inserção das funções de interface não encontrado.")
        s = s.replace(marker, logout_js + marker, 1)
    forget_marker = "$('forgetDevice').onclick=()=>{"
    forget_new = "$('forgetDevice').onclick=async()=>{if(publicSession){await logoutPrivateSession();return}"
    once(forget_marker, forget_new, "botão Esquecer acesso")

    # In public-session mode, the HttpOnly cookie is the only browser credential.
    # The per-profile bearer token stays inside the gateway and local worker.
    old_api = """  const resp=await fetch(panelBase+'api/'+path,{method,headers:{'X-EC-Token':token,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,cache:'no-store',...(controller?{signal:controller.signal}:{})});
"""
    new_api = """  const headers={...(publicSession?{}:{'X-EC-Token':token}),...(data?{'Content-Type':'application/json'}:{})};
  const resp=await fetch(panelBase+'api/'+path,{method,credentials:'same-origin',headers,body:data?JSON.stringify(data):undefined,cache:'no-store',...(controller?{signal:controller.signal}:{})});
"""
    once(old_api, new_api, "API autenticada pelo cookie sem enviar bearer token")

    old_lane = "fetch(panelBase+'api/moodle/automation/lanes/'+encodeURIComponent(lane.id)+'/screenshot',{headers:{'X-EC-Token':token},cache:'no-store'})"
    new_lane = "fetch(panelBase+'api/moodle/automation/lanes/'+encodeURIComponent(lane.id)+'/screenshot',{credentials:'same-origin',headers:publicSession?{}:{'X-EC-Token':token},cache:'no-store'})"
    if new_lane not in s:
        if old_lane not in s: raise SystemExit("Screenshot dos agentes não encontrado.")
        s=s.replace(old_lane,new_lane,1)
    old_screen = "fetch(panelBase+'api/screenshot',{cache:'no-store',headers:{'X-EC-Token':token},signal:controller.signal})"
    new_screen = "fetch(panelBase+'api/screenshot',{credentials:'same-origin',cache:'no-store',headers:publicSession?{}:{'X-EC-Token':token},signal:controller.signal})"
    if new_screen not in s:
        if old_screen not in s: raise SystemExit("Screenshot principal não encontrado.")
        s=s.replace(old_screen,new_screen,1)

    # Remove obsolete panel tokens saved by earlier builds on this browser.
    marker = "if(publicSession)token='public-session-cookie';"
    cleanup = """if(publicSession){
    token='public-session-cookie';
    try{for(const storage of [localStorage,sessionStorage]){for(const key of Object.keys(storage)){if(key==='ec_token'||key==='ec_remember:/'||key.startsWith('ec_token:')||key.startsWith('ec_remember:'))storage.removeItem(key)}}}catch{}
}"""
    if cleanup not in s:
        if marker not in s: raise SystemExit("Estado inicial da sessão pública não encontrado.")
        s=s.replace(marker,cleanup,1)

    path.write_text(s, encoding="utf-8")


def main() -> None:
    root = Path(os.getenv("EC_SOURCE_ROOT", "/app")).resolve()
    if not (root / "servidor.py").is_file():
        raise SystemExit(f"Pasta do Studio inválida: {root}")
    patch_mobile(root)
    patch_profiles(root)
    patch_server(root)
    patch_frontend(root)

    for relative in ("servidor.py", "mobile_app.py", "perfis.py"):
        py_compile.compile(str(root / relative), doraise=True)

    server = (root / "servidor.py").read_text(encoding="utf-8")
    mobile = (root / "mobile_app.py").read_text(encoding="utf-8")
    profiles = (root / "perfis.py").read_text(encoding="utf-8")
    html = (root / "web" / "index.html").read_text(encoding="utf-8")
    checks = {
        "signed HttpOnly cookie route": "async def home(request: Request)" in server and "set_cookie(PUBLIC_COOKIE" in server,
        "server-side private token injection": "token_painel.txt" in mobile and "X-EC-Token" in mobile,
        "per-profile isolated tenant": "public_sessions" in mobile and "EC_PUBLIC_SESSION_ID" in profiles,
        "browser bearer token removed": "if(publicSession)token='public-session-cookie';" in html and ("if(!publicSession)token=sessionStorage" in html or "if(!publicSession&&!hostedBridgePage)token=sessionStorage" in html),
        "no token hash in public session": "if(!publicSession" in html and "location.hash.startsWith('#token=')" in html,
    }
    for label, ok in checks.items():
        print(("PASS" if ok else "FAIL") + ": " + label)
    if not all(checks.values()):
        raise SystemExit("A validação da autenticação automática não passou.")
    print(f"Autenticação automática instalada em {root}; nenhum outro módulo foi redesenhado.")


if __name__ == "__main__":
    main()
