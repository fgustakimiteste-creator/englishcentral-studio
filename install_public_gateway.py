from pathlib import Path
import os

ROOT = Path(os.getenv('EC_SOURCE_ROOT', '/app'))

def replace_once(path: str, old: str, new: str) -> None:
    file_path = ROOT / path
    source = file_path.read_text(encoding='utf-8')
    if old not in source:
        raise SystemExit(f'Patch target not found in {path}: {old[:160]!r}')
    file_path.write_text(source.replace(old, new, 1), encoding='utf-8')

# --- Server-side public sessions: one tenant folder and one browser cookie per visitor. ---
replace_once('mobile_app.py',
'''import asyncio
import hmac
import os
import re
''',
'''import asyncio
import hashlib
import hmac
import os
import re
import uuid
''')

replace_once('mobile_app.py',
'''PROFILE_ID = re.compile(r'principal|pessoa(?:[2-9]|[1-9]\\d+)')
''',
'''PROFILE_ID = re.compile(r'principal|pessoa(?:[2-9]|[1-9]\\d+)')
PUBLIC_COOKIE = 'ec_public_session'
PUBLIC_SESSION_ID = re.compile(r'[a-f0-9]{32}')


def create_public_session_id() -> str:
    return uuid.uuid4().hex


def _public_session_secret() -> bytes:
    secret = os.getenv('EC_PUBLIC_SESSION_SECRET', '').encode('utf-8')
    if len(secret) < 32:
        raise RuntimeError('EC_PUBLIC_SESSION_SECRET precisa ter pelo menos 32 caracteres.')
    return secret


def make_public_session_cookie(session_id: str) -> str:
    if not PUBLIC_SESSION_ID.fullmatch(session_id):
        raise ValueError('Identificador de sessão pública inválido.')
    signature = hmac.new(_public_session_secret(), session_id.encode('ascii'), hashlib.sha256).hexdigest()
    return session_id + '.' + signature


def read_public_session_id(request: Request) -> str | None:
    raw = request.cookies.get(PUBLIC_COOKIE, '')
    try:
        session_id, signature = raw.split('.', 1)
    except ValueError:
        return None
    if not PUBLIC_SESSION_ID.fullmatch(session_id):
        return None
    try:
        expected = hmac.new(_public_session_secret(), session_id.encode('ascii'), hashlib.sha256).hexdigest()
    except RuntimeError:
        return None
    return session_id if hmac.compare_digest(signature, expected) else None


def public_profile_manager(project_root: Path, session_id: str):
    """Cada visitante tem uma raiz ProfileManager própria; a Pessoa principal é seu perfil inicial."""
    if not PUBLIC_SESSION_ID.fullmatch(session_id):
        raise HTTPException(401, 'Sessão pública inválida.')
    from perfis import ProfileManager
    profiles_root = Path(os.getenv('EC_PROFILES_ROOT', str(Path(project_root) / '.dados_locais')))
    tenant_root = profiles_root / 'public_sessions' / session_id
    tenant_root.mkdir(parents=True, exist_ok=True)
    return ProfileManager(tenant_root, Path(project_root), public_session_id=session_id)
''')

# Replace the profile proxy: a signed HttpOnly cookie selects the visitor tenant,
# and the private profile token stays inside the server.
start = '''    @app.api_route('/p/{profile_id}/{path:path}', methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'])
    async def profile_panel(profile_id: str, path: str, request: Request):
'''
end = '''            raise HTTPException(502, 'O painel desta pessoa está indisponível. Tente novamente; o histórico permanece salvo.') from exc
'''
mobile = ROOT / 'mobile_app.py'
s = mobile.read_text(encoding='utf-8')
i = s.find(start)
if i < 0:
    raise SystemExit('Could not locate profile_panel route start')
j = s.find(end, i)
if j < 0:
    raise SystemExit('Could not locate profile_panel route end')
j += len(end)
new_block = '''    @app.api_route('/p/{profile_id}/{path:path}', methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'])
    async def profile_panel(profile_id: str, path: str, request: Request):
        if not config.enabled or not PROFILE_ID.fullmatch(profile_id):
            raise HTTPException(404, 'Painel não encontrado.')

        public_sessions = os.getenv('EC_PUBLIC_SESSIONS', '0') == '1'
        session_id = read_public_session_id(request) if public_sessions else None
        if public_sessions:
            if not session_id:
                raise HTTPException(401, 'Sessão pública ausente ou inválida. Abra o endereço principal novamente.')
            worker_session = os.getenv('EC_PUBLIC_SESSION_ID', '')
            if worker_session and not hmac.compare_digest(worker_session, session_id):
                raise HTTPException(403, 'Esta sessão pertence a outro visitante.')
            manager = public_profile_manager(root, session_id)
        else:
            manager = manager_factory()

        people = await asyncio.to_thread(manager.list)
        if profile_id not in {person['id'] for person in people}:
            raise HTTPException(404, 'Pessoa não encontrada nesta sessão.')
        if request.method in {'GET', 'HEAD'} and path == '':
            return FileResponse(root / 'web' / 'index.html', media_type='text/html', headers={'Cache-Control': 'no-store'})
        # No proxy de destinos arbitrários: apenas a API interna do perfil solicitado.
        if not path.startswith('api/') or '..' in path or '\\\\' in path or '?' in path or '#' in path:
            raise HTTPException(404, 'Endereço não encontrado.')

        # No modo legado, autentique antes de iniciar qualquer subprocesso.
        token = ''
        if not public_sessions:
            token = request.headers.get('x-ec-token', '')
            try:
                expected = (manager.data_dir(profile_id) / 'token_painel.txt').read_text('utf-8').strip()
            except OSError:
                expected = ''
            if not token or not expected or not hmac.compare_digest(token, expected):
                raise HTTPException(401, 'Token inválido para esta pessoa.')

        try:
            # Abre/inicia o worker após autenticar o cookie. A senha do painel nunca sai do servidor.
            info = await asyncio.to_thread(manager.open, profile_id)
            parsed = urlsplit(info['url'])
            if parsed.hostname != '127.0.0.1' or not parsed.port:
                raise ValueError('Endereço interno inválido')
            if public_sessions:
                token = (manager.data_dir(profile_id) / 'token_painel.txt').read_text('utf-8').strip()

            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 65536:
                    raise HTTPException(413, 'Solicitação muito grande.')
            headers = {'X-EC-Token': token}
            if request.headers.get('content-type'):
                headers['Content-Type'] = request.headers['content-type']
            async with httpx.AsyncClient(timeout=55, trust_env=False, follow_redirects=False) as client:
                response = await client.request(request.method, f'http://127.0.0.1:{parsed.port}/' + path,
                                                params=request.query_params, headers=headers, content=bytes(body))
            return Response(response.content, status_code=response.status_code,
                            media_type=response.headers.get('content-type'), headers={'Cache-Control': 'no-store'})
        except HTTPException:
            raise
        except (OSError, ValueError, RuntimeError, httpx.HTTPError) as exc:
            raise HTTPException(502, 'O painel desta pessoa está indisponível. Tente novamente; o histórico permanece salvo.') from exc
'''
mobile.write_text(s[:i] + new_block + s[j:], encoding='utf-8')

# Each worker receives the tenant ID so its own profile manager continues to manage
# all profiles inside this visitor's tenant. This restores People and multi-agent.
replace_once('perfis.py',
'''    def __init__(self, root: Path, project: Path):
        self.root, self.project = Path(root), Path(project)
        self.file = self.root / 'perfis.json'
''',
'''    def __init__(self, root: Path, project: Path, public_session_id: str | None = None):
        self.root, self.project = Path(root), Path(project)
        self.public_session_id = public_session_id or os.getenv('EC_PUBLIC_SESSION_ID', '')
        self.file = self.root / 'perfis.json'
''')
replace_once('perfis.py',
'''                env.update(EC_DATA_DIR=str(directory), EC_PROFILES_ROOT=str(self.root),
                           EC_PROFILE_ID=profile_id, EC_PORT=str(port))
''',
'''                env.update(EC_DATA_DIR=str(directory), EC_PROFILES_ROOT=str(self.root),
                           EC_PROFILE_ID=profile_id, EC_PORT=str(port))
                if self.public_session_id:
                    env['EC_PUBLIC_SESSION_ID'] = self.public_session_id
''')

# Public visitors start at the original principal profile (Pessoa 1) and receive
# a signed, HttpOnly, 30-day cookie. No bearer token is placed in a URL or localStorage.
replace_once('servidor.py',
'''from fastapi import Depends, FastAPI, Header, HTTPException
''',
'''from fastapi import Depends, FastAPI, Header, HTTPException, Request
''')
replace_once('servidor.py',
'''from mobile_app import RemoteConfig, install_mobile_routes
''',
'''from mobile_app import (RemoteConfig, install_mobile_routes, create_public_session_id,
                         make_public_session_cookie, read_public_session_id, public_profile_manager, PUBLIC_COOKIE)
''')
replace_once('servidor.py',
'''@app.api_route('/', methods=['GET', 'HEAD'])
async def home():
    return FileResponse(ROOT / 'web' / 'index.html', media_type='text/html', headers={'Cache-Control': 'no-store'})
''',
'''@app.api_route('/', methods=['GET', 'HEAD'])
async def home(request: Request):
    if (REMOTE_CONFIG.enabled and os.getenv('EC_PUBLIC_SESSIONS', '0') == '1'
            and not os.getenv('EC_PUBLIC_SESSION_ID')):
        from fastapi.responses import RedirectResponse, PlainTextResponse
        session_id = read_public_session_id(request)
        if not session_id:
            try:
                max_sessions = max(1, min(12, int(os.getenv('EC_PUBLIC_MAX_SESSIONS', '3'))))
            except ValueError:
                max_sessions = 3
            sessions_root = PROFILES_ROOT / 'public_sessions'
            try:
                count = sum(1 for item in sessions_root.iterdir() if item.is_dir())
            except OSError:
                count = 0
            if count >= max_sessions:
                return PlainTextResponse('O servidor atingiu o limite de sessões públicas simultâneas. Tente novamente mais tarde.', status_code=503)
            session_id = create_public_session_id()
            manager = public_profile_manager(ROOT, session_id)
            # Cria a pasta e o cadastro começando sempre na Pessoa principal (Pessoa 1).
            await asyncio.to_thread(manager.list)
            response = RedirectResponse('/p/principal/', status_code=303)
            response.set_cookie(PUBLIC_COOKIE, make_public_session_cookie(session_id), max_age=2592000,
                                httponly=True, secure=True, samesite='lax', path='/')
            return response
        manager = public_profile_manager(ROOT, session_id)
        await asyncio.to_thread(manager.list)
        return RedirectResponse('/p/principal/', status_code=303)
    return FileResponse(ROOT / 'web' / 'index.html', media_type='text/html', headers={'Cache-Control': 'no-store'})
''')

# Opening a person inside a public tenant returns a path only; token fragments stay server-side.
replace_once('servidor.py',
'''        if REMOTE_CONFIG.enabled:
            # As sessões continuam separadas; o celular acessa todas pelo HTTPS
            # do painel, sem tentar abrir o próprio 127.0.0.1.
            fragment = urlparse(result['url']).fragment
            result['url'] = f'/p/{profile_id}/#{fragment}'
''',
'''        if REMOTE_CONFIG.enabled:
            if os.getenv('EC_PUBLIC_SESSION_ID'):
                result['url'] = f'/p/{profile_id}/'
            else:
                fragment = urlparse(result['url']).fragment
                result['url'] = f'/p/{profile_id}/#{fragment}'
''')

# Front-end: public tenant auth is carried by the HttpOnly cookie. Keep full People/multi-agent UI.
replace_once('web/index.html',
'''let token='',connected=false,opened=false,running=false,busy=false,viewing=false,refreshing=false,courseRefreshing=false,lastCourseRefresh=0,lastCourseUrl='',lastUrl=null,manualPointerAt=0,platformType='';
const panelBase=/^\\/p\\/(principal|pessoa(?:[2-9]|[1-9]\\d+))\\/$/.test(location.pathname)?location.pathname:'/';
''',
'''let token='',connected=false,opened=false,running=false,busy=false,viewing=false,refreshing=false,courseRefreshing=false,lastCourseRefresh=0,lastCourseUrl='',lastUrl=null,manualPointerAt=0,platformType='';
const publicSession=/^\\/p\\/(principal|pessoa(?:[2-9]|[1-9]\\d+))\\/$/.test(location.pathname);
const panelBase=publicSession?location.pathname:'/';
if(publicSession)token='public-session-cookie';
''')
replace_once('web/index.html',
'''try{$('rememberAccess').checked=localStorage.getItem(rememberKey)==='true';token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}
''',
'''try{$('rememberAccess').checked=publicSession?true:localStorage.getItem(rememberKey)==='true';if(!publicSession)token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}
''')
replace_once('web/index.html',
'''function storeAccess(){
 try{if(token)sessionStorage.setItem(tokenKey,token);else sessionStorage.removeItem(tokenKey)}catch{}
''',
'''function storeAccess(){
 if(publicSession){text('deviceAccessStatus','A sessão é autenticada e mantida pelo servidor neste navegador.');return}
 try{if(token)sessionStorage.setItem(tokenKey,token);else sessionStorage.removeItem(tokenKey)}catch{}
''')
replace_once('web/index.html',
'''if(location.hash.startsWith('#token=')){try{token=decodeURIComponent(location.hash.substring(7));storeAccess();history.replaceState(null,'',location.pathname+location.search)}catch{}}
''',
'''if(!publicSession&&location.hash.startsWith('#token=')){try{token=decodeURIComponent(location.hash.substring(7));storeAccess();history.replaceState(null,'',location.pathname+location.search)}catch{}}
''')


# The Chrome button must not disappear in a Render-hosted panel. It opens a
# truthful guide to the required on-device Termux bridge; the Render process
# cannot reach Android localhost directly.
page = ROOT / 'web' / 'index.html'
html = page.read_text(encoding='utf-8')
hidden_rule = "for(const id of ['connectChrome','emptyConnectChrome'])$(id).hidden=remoteMode;"
if hidden_rule in html:
    html = html.replace(hidden_rule, "for(const id of ['connectChrome','emptyConnectChrome'])$(id).hidden=false;", 1)
elif "for(const id of ['connectChrome','emptyConnectChrome'])$(id).hidden=false;" not in html:
    raise SystemExit('Could not find Chrome connect button visibility rule')

# Identify the dialog elements so the mobile/Render guidance can be changed safely.
html = html.replace(
    '<p class="note">O assistente pode reutilizar uma aba do EnglishCentral ou do SEDUCTEC já aberta no seu Chrome, sem copiar senhas ou cookies para outro perfil.</p>',
    '<p id="browserDialogIntro" class="note">O assistente pode reutilizar uma aba do EnglishCentral ou do SEDUCTEC já aberta no seu Chrome, sem copiar senhas ou cookies para outro perfil.</p>',
    1
)
html = html.replace(
    '<ol class="browserSteps">',
    '<ol id="browserSteps" class="browserSteps">',
    1
)
html = html.replace(
    '<button id="submitBrowserConnect" class="btn primary" type="submit">Conectar meu Chrome</button>',
    '<button id="submitBrowserConnect" class="btn primary" type="submit">Conectar meu Chrome</button><a id="localStudioLink" class="btn" href="http://127.0.0.1:8765/" target="_blank" rel="noopener" hidden>Abrir Studio local</a><a id="termuxPackageLink" class="btn" href="https://github.com/fgustakimiteste-creator/englishcentral-studio/raw/refs/heads/main/EnglishCentral-Studio-18.13.3-G0DMOD3.zip" target="_blank" rel="noopener" hidden>Baixar pacote Termux</a>',
    1
)

old_help_prefix = "text('browserSessionHelp',remoteMode?"
lines = html.splitlines(keepends=True)
for index, line in enumerate(lines):
    if old_help_prefix in line:
        indent = line[:len(line) - len(line.lstrip())]
        lines[index] = indent + "text('browserSessionHelp',remoteMode?'Para conectar o Chrome deste Android, abra o Studio localmente pelo Termux. O site do Render não consegue acessar o Chrome/localhost do seu aparelho. Veja as instruções em “Usar meu Chrome já aberto”.':'Seu Chrome usa as contas já conectadas nele. Para contas simultâneas independentes, use uma pessoa e uma sessão do assistente para cada conta.');\n"
        break
else:
    raise SystemExit('Could not find browserSessionHelp runtime line')
html = ''.join(lines)

old_function = "function showBrowserConnect(){text('browserConnectMessage','');$('browserConsent').checked=false;$('browserDialog').showModal()}"
new_function = r'''function showBrowserConnect(){
 text('browserConnectMessage','');
 $('browserConsent').checked=false;
 $('submitBrowserConnect').hidden=remoteMode;
 $('localStudioLink').hidden=!remoteMode;
 $('termuxPackageLink').hidden=!remoteMode;
 const steps=$('browserSteps');steps.replaceChildren();
 if(remoteMode){
  text('browserDialogTitle','Conectar o Chrome deste Android');
  text('browserDialogIntro','Este painel está hospedado no Render. Por segurança, um servidor na nuvem não consegue acessar diretamente o Chrome instalado no seu celular. Para reaproveitar o login do Chrome, o motor do Studio precisa rodar no próprio Android.');
  const items=[
   'Baixe o pacote completo do Studio e extraia a pasta EnglishCentral-Studio no armazenamento do celular.',
   'Abra o Termux e instale as ferramentas: pkg update -y && pkg install python nodejs-lts android-tools unzip -y.',
   'No Android, ative Opções do desenvolvedor → Depuração sem fio → Parear dispositivo com código. No Termux, execute adb pair IP:PORTA e informe o código mostrado no Android; depois execute adb connect IP:PORTA usando o endereço/porta principal exibidos na tela de Depuração sem fio.',
   'Com o Chrome aberto no curso, no Termux execute: adb forward tcp:9222 localabstract:chrome_devtools_remote.',
   'No Termux, entre na pasta EnglishCentral-Studio e execute bash TERMUX_INICIAR.sh. Depois abra http://127.0.0.1:8765 no Edge deste mesmo celular e conecte o Chrome por esse painel local.'
  ];
  for(const value of items){const li=document.createElement('li');li.textContent=value;steps.append(li)}
 }else{
  text('browserDialogTitle','Usar o Chrome já aberto');
  text('browserDialogIntro','O assistente pode reutilizar uma aba do EnglishCentral ou do SEDUCTEC já aberta no seu Chrome, sem copiar senhas ou cookies para outro perfil.');
  const items=[
   'No Chrome 144 ou superior, abra chrome://inspect/#remote-debugging e habilite a conexão.',
   'Abra o curso no mesmo Chrome e faça o login diretamente no site.',
   'Clique em Conectar e aceite a solicitação que o próprio Chrome mostrar.'
  ];
  for(const value of items){const li=document.createElement('li');li.textContent=value;steps.append(li)}
 }
 $('browserDialog').showModal()
}'''
if old_function not in html:
    raise SystemExit('Could not find the browser connect dialog function')
html = html.replace(old_function, new_function, 1)
page.write_text(html, encoding='utf-8')
