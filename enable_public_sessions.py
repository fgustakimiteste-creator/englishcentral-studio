from pathlib import Path
import os

ROOT = Path(os.getenv('EC_SOURCE_ROOT', '/app'))

def replace_once(path, old, new):
    p = ROOT / path
    source = p.read_text(encoding='utf-8')
    if old not in source:
        raise SystemExit(f'Expected patch target not found in {path}: {old[:100]!r}')
    p.write_text(source.replace(old, new, 1), encoding='utf-8')

replace_once('mobile_app.py',
'''import hmac
import os
import re
''',
'''import hmac
import hashlib
import os
import re
''')
replace_once('mobile_app.py',
'''PROFILE_ID = re.compile(r'principal|pessoa(?:[2-9]|[1-9]\\d+)')
''',
'''PROFILE_ID = re.compile(r'principal|pessoa(?:[2-9]|[1-9]\\d+)')
PUBLIC_COOKIE = 'ec_public_session'

def make_public_cookie(profile_id: str) -> str:
    secret = os.getenv('EC_PUBLIC_SESSION_SECRET', '').encode()
    if len(secret) < 32:
        raise RuntimeError('EC_PUBLIC_SESSION_SECRET precisa ter pelo menos 32 caracteres.')
    signature = hmac.new(secret, profile_id.encode(), hashlib.sha256).hexdigest()
    return profile_id + '.' + signature

def read_public_cookie(request: Request) -> str | None:
    secret = os.getenv('EC_PUBLIC_SESSION_SECRET', '').encode()
    if len(secret) < 32:
        return None
    raw = request.cookies.get(PUBLIC_COOKIE, '')
    try:
        profile_id, signature = raw.split('.', 1)
    except ValueError:
        return None
    if not PROFILE_ID.fullmatch(profile_id):
        return None
    expected = hmac.new(secret, profile_id.encode(), hashlib.sha256).hexdigest()
    return profile_id if hmac.compare_digest(signature, expected) else None
''')
replace_once('mobile_app.py',
'''        if profile_id not in {p['id'] for p in people}:
            raise HTTPException(404, 'Pessoa não encontrada.')
        if request.method in {'GET', 'HEAD'} and path == '':
            return FileResponse(root / 'web' / 'index.html', media_type='text/html', headers={'Cache-Control': 'no-store'})
        # Somente a API conhecida; nunca um proxy de destino ou arquivo arbitrário.
        if not path.startswith('api/') or '..' in path or '\\\\' in path or '?' in path or '#' in path:
            raise HTTPException(404, 'Endereço não encontrado.')
        token_file = manager.data_dir(profile_id) / 'token_painel.txt'
        try:
            expected = token_file.read_text('utf-8').strip()
        except OSError:
            expected = ''
        token = request.headers.get('x-ec-token', '')
        if not expected or not token or not hmac.compare_digest(token, expected):
            raise HTTPException(401, 'Token inválido para esta pessoa.')
''',
'''        if profile_id not in {p['id'] for p in people}:
            raise HTTPException(404, 'Pessoa não encontrada.')
        token_file = manager.data_dir(profile_id) / 'token_painel.txt'
        try:
            expected = token_file.read_text('utf-8').strip()
        except OSError:
            expected = ''
        # A sessão pública é vinculada ao cookie HttpOnly, nunca a um token enviado ao aparelho.
        cookie_profile = read_public_cookie(request)
        token = expected if cookie_profile == profile_id else request.headers.get('x-ec-token', '')
        if not expected or not token or not hmac.compare_digest(token, expected):
            raise HTTPException(401, 'Sessão pública inválida. Abra o endereço principal novamente.')
        if request.method in {'GET', 'HEAD'} and path == '':
            return FileResponse(root / 'web' / 'index.html', media_type='text/html', headers={'Cache-Control': 'no-store'})
        # Somente a API conhecida; nunca um proxy de destino ou arquivo arbitrário.
        if not path.startswith('api/') or '..' in path or '\\\\' in path or '?' in path or '#' in path:
            raise HTTPException(404, 'Endereço não encontrado.')
''')
replace_once('servidor.py',
'''from mobile_app import RemoteConfig, install_mobile_routes
''',
'''from mobile_app import RemoteConfig, install_mobile_routes, make_public_cookie, read_public_cookie, PUBLIC_COOKIE
''')
replace_once('servidor.py',
'''@app.api_route('/', methods=['GET', 'HEAD'])
async def home():
    return FileResponse(ROOT / 'web' / 'index.html', media_type='text/html', headers={'Cache-Control': 'no-store'})
''',
'''@app.api_route('/', methods=['GET', 'HEAD'])
async def home(request: Request):
    # Gateway público: cada navegador recebe seu próprio perfil remoto e cookie HttpOnly.
    if REMOTE_CONFIG.enabled and os.getenv('EC_PUBLIC_SESSIONS', '0') == '1' and PROFILE_ID == 'principal':
        from fastapi.responses import RedirectResponse, PlainTextResponse
        manager = profile_manager()
        people = await asyncio.to_thread(manager.list)
        existing = read_public_cookie(request)
        valid_ids = {person['id'] for person in people if person['id'] != 'principal'}
        if existing in valid_ids:
            return RedirectResponse(f'/p/{existing}/', status_code=303)
        maximum = max(1, min(12, int(os.getenv('EC_PUBLIC_MAX_SESSIONS', '8'))))
        if len(valid_ids) >= maximum:
            return PlainTextResponse('O servidor atingiu o limite de sessões simultâneas. Tente novamente mais tarde.', status_code=503)
        person = await asyncio.to_thread(manager.create, 'Visitante')
        response = RedirectResponse(f'/p/{person["id"]}/', status_code=303)
        response.set_cookie(PUBLIC_COOKIE, make_public_cookie(person['id']), max_age=2592000,
                            httponly=True, secure=True, samesite='lax', path='/')
        return response
    return FileResponse(ROOT / 'web' / 'index.html', media_type='text/html', headers={'Cache-Control': 'no-store'})
''')
replace_once('perfis.py',
'''                env.update(EC_DATA_DIR=str(directory), EC_PROFILES_ROOT=str(self.root),
                           EC_PROFILE_ID=profile_id, EC_PORT=str(port))
''',
'''                env.update(EC_DATA_DIR=str(directory), EC_PROFILES_ROOT=str(self.root),
                           EC_PROFILE_ID=profile_id, EC_PORT=str(port), EC_PUBLIC_SESSION_WORKER='1')
''')
replace_once('servidor.py',
'''async def profiles():
    try:
        return {'pessoas': await asyncio.to_thread(profile_manager().list), 'atual': PROFILE_ID}
''',
'''async def profiles():
    try:
        people = await asyncio.to_thread(profile_manager().list)
        if os.getenv('EC_PUBLIC_SESSION_WORKER') == '1':
            people = [person for person in people if person['id'] == PROFILE_ID]
        return {'pessoas': people, 'atual': PROFILE_ID}
''')
replace_once('servidor.py',
'''async def add_profile(name: ProfileName):
    try:
''',
'''async def add_profile(name: ProfileName):
    if os.getenv('EC_PUBLIC_SESSION_WORKER') == '1':
        raise HTTPException(403, 'O gerenciamento de outras sessões não está disponível no acesso público.')
    try:
''')
replace_once('servidor.py',
'''async def open_person(profile_id: str):
    return await open_profile_response(profile_id)
''',
'''async def open_person(profile_id: str):
    if os.getenv('EC_PUBLIC_SESSION_WORKER') == '1' and profile_id != PROFILE_ID:
        raise HTTPException(403, 'Cada visitante só pode acessar sua própria sessão.')
    return await open_profile_response(profile_id)
''')
replace_once('servidor.py',
'''async def rename_profile(profile_id: str, name: ProfileName):
    try:
''',
'''async def rename_profile(profile_id: str, name: ProfileName):
    if os.getenv('EC_PUBLIC_SESSION_WORKER') == '1' and profile_id != PROFILE_ID:
        raise HTTPException(403, 'Cada visitante só pode alterar sua própria sessão.')
    try:
''')
replace_once('servidor.py',
'''async def second_profile():
    # Compatibilidade com painéis antigos; os novos usam /api/profiles.
''',
'''async def second_profile():
    if os.getenv('EC_PUBLIC_SESSION_WORKER') == '1':
        raise HTTPException(403, 'Acesso público isolado: a sessão já pertence a este visitante.')
    # Compatibilidade com painéis antigos; os novos usam /api/profiles.
''')
replace_once('web/index.html',
'''let token='',connected=false,opened=false,running=false,busy=false,viewing=false,refreshing=false,courseRefreshing=false,lastCourseRefresh=0,lastCourseUrl='',lastUrl=null,manualPointerAt=0,platformType='';
const panelBase=/^\\/p\\/(principal|pessoa(?:[2-9]|[1-9]\\d+))\\/$/.test(location.pathname)?location.pathname:'/';
''',
'''let token='',connected=false,opened=false,running=false,busy=false,viewing=false,refreshing=false,courseRefreshing=false,lastCourseRefresh=0,lastCourseUrl='',lastUrl=null,manualPointerAt=0,platformType='';
const publicSession=/^\\/p\\/(principal|pessoa(?:[2-9]|[1-9]\\d+))\\/$/.test(location.pathname);
const panelBase=publicSession?location.pathname:'/';
if(publicSession)token='public-cookie-session';
''')
replace_once('web/index.html',
'''function showView(name){
 if(!viewText[name])return;
''',
'''function showView(name){
 if(!viewText[name] || (publicSession && name==='people'))return;
''')
replace_once('web/index.html',
'''updatePreset();setInterval(()=>{if(!busy&&!document.hidden)refresh()},1500);''',
'''if(publicSession){const peopleButton=document.querySelector('[data-view="people"]');if(peopleButton)peopleButton.hidden=true;const peopleSection=document.querySelector('.settingsSection');if(peopleSection)peopleSection.hidden=true;$('auth').classList.add('hide');}
updatePreset();setInterval(()=>{if(!busy&&!document.hidden)refresh()},1500);''')
