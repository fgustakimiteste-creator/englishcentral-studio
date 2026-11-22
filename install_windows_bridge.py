"""Instala a ponte Windows real no EnglishCentral Studio original (V18.13.3).

O Render hospeda somente o painel. Cada visitante executa este servidor local,
que conecta o Playwright ao Chrome já aberto em 127.0.0.1:8765.
"""
from __future__ import annotations
import os
import py_compile
import re
import sys
from pathlib import Path

ORIGIN = "https://englishcentral-studio.onrender.com"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    if new in source:
        return
    if old not in source:
        raise SystemExit(f"Patch não aplicado ({label}): trecho original não encontrado em {path.name}.")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def patch_server(root: Path) -> None:
    p = root / "servidor.py"
    s = p.read_text(encoding="utf-8")

    # Request precisa estar no namespace para FastAPI resolver a anotação da rota.
    import_line = "from fastapi import Depends, FastAPI, Header, HTTPException\n"
    if "from fastapi import Depends, FastAPI, Header, HTTPException, Request" not in s:
        if import_line not in s:
            raise SystemExit("Import FastAPI original não encontrado em servidor.py")
        s = s.replace(import_line, "from fastapi import Depends, FastAPI, Header, HTTPException, Request\n", 1)

    marker = "REMOTE_CONFIG = load_remote_config()\n"
    injected = marker + (
        "LOCAL_PC_BRIDGE = os.getenv('EC_PC_BRIDGE', '0') == '1'\n"
        f"LOCAL_PANEL_ORIGIN = os.getenv('EC_LOCAL_PANEL_ORIGIN', '{ORIGIN}').strip().rstrip('/')\n"
    )
    if "LOCAL_PC_BRIDGE = os.getenv('EC_PC_BRIDGE'" not in s:
        if marker not in s:
            raise SystemExit("REMOTE_CONFIG marker não encontrado em servidor.py")
        s = s.replace(marker, injected, 1)

    app_marker = "app = FastAPI(title='EnglishCentral Studio — V18.13.1 Automação paralela SEDUCTEC', docs_url=None, redoc_url=None, lifespan=lifespan)\n"
    cors = app_marker + '''

@app.middleware('http')
async def pc_bridge_cors(request: Request, call_next):
    """CORS estrito: só o painel HTTPS oficial pode chamar o conector local."""
    origin = request.headers.get('origin', '').rstrip('/')
    if not LOCAL_PC_BRIDGE or origin != LOCAL_PANEL_ORIGIN:
        return await call_next(request)
    if request.method == 'OPTIONS':
        response = Response(status_code=204)
    else:
        response = await call_next(request)
    response.headers['Access-Control-Allow-Origin'] = LOCAL_PANEL_ORIGIN
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-EC-Token'
    response.headers['Access-Control-Max-Age'] = '600'
    response.headers['Access-Control-Allow-Private-Network'] = 'true'
    response.headers['Vary'] = 'Origin'
    return response
'''
    if "async def pc_bridge_cors" not in s:
        if app_marker not in s:
            raise SystemExit("FastAPI app marker não encontrado em servidor.py")
        s = s.replace(app_marker, cors, 1)

    token_marker = "    return local_token(TOKEN_FILE)\n\n\ndef require_auth(x_ec_token: str | None = Header(default=None)):\n"
    bootstrap = """    return local_token(TOKEN_FILE)


@app.get('/api/bridge/bootstrap')
async def pc_bridge_bootstrap(request: Request):
    # Token entregue somente ao painel oficial, por conexão loopback neste PC.
    if not LOCAL_PC_BRIDGE:
        raise HTTPException(404, 'Ponte Windows desativada.')
    origin = request.headers.get('origin', '').rstrip('/')
    if origin != LOCAL_PANEL_ORIGIN:
        raise HTTPException(403, 'Origem não autorizada para a ponte local.')
    peer = request.client.host if request.client else ''
    if peer not in {'127.0.0.1', '::1'}:
        raise HTTPException(403, 'A ponte aceita apenas conexões locais neste computador.')
    return Response(
        content=json.dumps({'ok': True, 'token': get_token(), 'agent': 'EnglishCentral Studio PC'}),
        media_type='application/json',
        headers={'Cache-Control': 'no-store, max-age=0', 'Pragma': 'no-cache', 'Vary': 'Origin'},
    )


def require_auth(x_ec_token: str | None = Header(default=None)):
"""
    if "async def pc_bridge_bootstrap" not in s:
        if token_marker not in s:
            raise SystemExit("get_token/require_auth marker não encontrado em servidor.py")
        s = s.replace(token_marker, bootstrap, 1)

    # Keep this: no_defaults is supported by Playwright Python >=1.60 and protects
    # the user's everyday Chrome context from Playwright default overrides.
    cdp_call = "connect_over_cdp(endpoint,timeout=25000,no_defaults=True)"
    if cdp_call not in s:
        old_cdp = "connect_over_cdp(endpoint,timeout=25000)"
        if old_cdp not in s:
            raise SystemExit("Chamada Playwright connect_over_cdp original não encontrada.")
        s = s.replace(old_cdp, cdp_call, 1)

    p.write_text(s, encoding="utf-8")
    s = p.read_text(encoding="utf-8")
    old = """            'mensagem':('Sessão do servidor; o login permanece salvo por pessoa.' if REMOTE_CONFIG.enabled else 'Usando o login do seu Chrome/Edge.' if mode=='existente' else
                        'Sessão do assistente; o login permanece salvo por pessoa.'),
"""
    new = """            'mensagem':('Conector local online; Chrome ainda não anexado.' if LOCAL_PC_BRIDGE and not active else
                        'Usando o login do seu Chrome/Edge.' if mode=='existente' and active else
                        'Sessão do servidor; o login permanece salvo por pessoa.' if REMOTE_CONFIG.enabled else
                        'Sessão do assistente; o login permanece salvo por pessoa.'),
"""
    if old in s and new not in s:
        s = s.replace(old, new, 1)
        p.write_text(s, encoding="utf-8")


def patch_mobile_boundary(root: Path) -> None:
    p = root / "mobile_app.py"
    old = "        expected = self.config.origin if self.config.enabled and not local else str(request.base_url).rstrip('/')\n"
    new = (
        "        bridge_origin = os.getenv('EC_LOCAL_PANEL_ORIGIN', "
        f"'{ORIGIN}').strip().rstrip('/')\n"
        "        bridge_request = (os.getenv('EC_PC_BRIDGE', '0') == '1' and local and origin == bridge_origin)\n"
        "        expected = bridge_origin if bridge_request else (self.config.origin if self.config.enabled and not local else str(request.base_url).rstrip('/'))\n"
    )
    replace_once(p, old, new, "origem do painel na ponte local")


def patch_launcher(root: Path) -> None:
    p = root / "iniciar.py"
    old = """        print(f'Painel aberto em http://127.0.0.1:{PORT}', flush=True)
        webbrowser.open(url)
"""
    new = """        if os.getenv('EC_PC_BRIDGE', '0') == '1':
            print(f'Ponte Windows ativa em http://127.0.0.1:{PORT}', flush=True)
            print('Abra https://englishcentral-studio.onrender.com e clique em “Já estou conectado no Chrome”.', flush=True)
            print('Mantenha esta janela aberta enquanto usar a automação.', flush=True)
        else:
            print(f'Painel aberto em http://127.0.0.1:{PORT}', flush=True)
            webbrowser.open(url)
"""
    replace_once(p, old, new, "iniciador sem abrir a UI local")
    old_browser = "    if not _installed_browser():\n        print('[2/3] Preparando Chromium para o Playwright...', flush=True)\n        command(PY, '-m', 'playwright', 'install', 'chromium')\n"
    new_browser = "    if not _installed_browser() and os.getenv('EC_PC_BRIDGE', '0') != '1':\n        print('[2/3] Preparando Chromium para o Playwright...', flush=True)\n        command(PY, '-m', 'playwright', 'install', 'chromium')\n"
    replace_once(p, old_browser, new_browser, "não baixar Chromium separado na ponte do Chrome existente")


def patch_frontend(root: Path) -> None:
    p = root / "web" / "index.html"
    s = p.read_text(encoding="utf-8")

    # The Render URL is a public shell; each browser operation must go to the PC connector.
    old_state = """let token='',connected=false,opened=false,running=false,busy=false,viewing=false,refreshing=false,courseRefreshing=false,lastCourseRefresh=0,lastCourseUrl='',lastUrl=null,manualPointerAt=0,platformType='';
const panelBase=/^\\/p\\/(principal|pessoa(?:[2-9]|[1-9]\\d+))\\/$/.test(location.pathname)?location.pathname:'/';
"""
    new_state = f"""let token='',connected=false,opened=false,running=false,busy=false,viewing=false,refreshing=false,courseRefreshing=false,lastCourseRefresh=0,lastCourseUrl='',lastUrl=null,manualPointerAt=0,platformType='';
const hostedBridgePage=location.origin==='{ORIGIN}';
let localBridgeActive=false;
const localBridgeBase='http://127.0.0.1:8765/';
function apiUrl(path){{return (localBridgeActive?localBridgeBase:panelBase)+'api/'+path}}
function apiTargetOptions(){{return localBridgeActive?{{targetAddressSpace:'loopback'}}:{{}}}}
const panelBase=/^\\/p\\/(principal|pessoa(?:[2-9]|[1-9]\\d+))\\/$/.test(location.pathname)?location.pathname:'/';
"""
    if "const hostedBridgePage=" not in s:
        if old_state not in s:
            raise SystemExit("Estado inicial do front-end não encontrado")
        s = s.replace(old_state, new_state, 1)

    s = s.replace("let remoteMode=false;", "let remoteMode=hostedBridgePage;", 1)
    hosted_marker = f"const hostedBridgePage=location.origin==='{ORIGIN}';\n"
    if "if(hostedBridgePage)$('useManagedBrowser').hidden=true;" not in s:
        if hosted_marker not in s:
            raise SystemExit("Marcador hostedBridgePage não encontrado")
        s = s.replace(hosted_marker, hosted_marker + "if(hostedBridgePage)$('useManagedBrowser').hidden=true;\n", 1)

    old_token_load = "try{$('rememberAccess').checked=localStorage.getItem(rememberKey)==='true';token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}"
    new_token_load = "try{$('rememberAccess').checked=!hostedBridgePage&&localStorage.getItem(rememberKey)==='true';if(!hostedBridgePage)token=sessionStorage.getItem(tokenKey)||($('rememberAccess').checked?localStorage.getItem(tokenKey):'')||''}catch{}"
    if old_token_load in s:
        s = s.replace(old_token_load, new_token_load, 1)

    old_hash = "if(location.hash.startsWith('#token=')){try{token=decodeURIComponent(location.hash.substring(7));storeAccess();history.replaceState(null,'',location.pathname+location.search)}catch{}}"
    new_hash = "if(!hostedBridgePage&&location.hash.startsWith('#token=')){try{token=decodeURIComponent(location.hash.substring(7));storeAccess();history.replaceState(null,'',location.pathname+location.search)}catch{}}else if(hostedBridgePage&&location.hash){history.replaceState(null,'',location.pathname+location.search)"
    if old_hash in s:
        s = s.replace(old_hash, new_hash, 1)

    old_store = "function storeAccess(){\n try{if(token)sessionStorage.setItem(tokenKey,token);else sessionStorage.removeItem(tokenKey)}catch{}"
    new_store = "function storeAccess(){\n if(hostedBridgePage||localBridgeActive){text('deviceAccessStatus','O acesso ao conector local não é salvo neste navegador.');return}\n try{if(token)sessionStorage.setItem(tokenKey,token);else sessionStorage.removeItem(tokenKey)}catch{}"
    if old_store in s:
        s = s.replace(old_store, new_store, 1)

    bootstrap = f'''async function connectLocalPCBridge(){{
 if(localBridgeActive)return true;
 if(!hostedBridgePage)throw Error('A ponte local só é necessária para o painel hospedado.');
 text('browserConnectMessage','Procurando o conector deste PC…');
 let response;
 try{{response=await fetch(localBridgeBase+'api/bridge/bootstrap',{{method:'GET',mode:'cors',cache:'no-store',targetAddressSpace:'loopback'}})}}
 catch(error){{throw Error('Não encontrei o conector neste PC. Execute windows\\\\INICIAR_PC.bat, mantenha a janela aberta e permita o acesso à rede local quando o Chrome perguntar.')}}
 if(!response.ok)throw Error('O conector local respondeu HTTP '+response.status+'. Atualize o conector Windows e tente novamente.');
 const data=await response.json();
 if(!data.ok||!data.token)throw Error('O conector local não devolveu uma credencial válida. Reinicie INICIAR_PC.bat.');
 token=data.token;localBridgeActive=true;remoteMode=false;
 try{{await api('health')}}catch(error){{token='';localBridgeActive=false;remoteMode=hostedBridgePage;throw Error('O servidor local não passou na autenticação: '+(error.message||String(error)))}}
 text('browserConnectMessage','Conector local verificado. Anexando ao Chrome existente…');
 return true;
}}
'''
    if "async function connectLocalPCBridge()" not in s:
        api_marker = "async function api(path,method='GET',data){\n"
        if api_marker not in s:
            raise SystemExit("Função api() não encontrada")
        s = s.replace(api_marker, bootstrap + "\n" + api_marker, 1)

    # Add only the connection action; leave all original course/automation modules and API handlers intact.
    old_fetch = "const resp=await fetch(panelBase+'api/'+path,{method,headers:{'X-EC-Token':token,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,cache:'no-store',...(controller?{signal:controller.signal}:{})});"
    new_fetch = "const resp=await fetch(apiUrl(path),{method,mode:localBridgeActive?'cors':'same-origin',headers:{'X-EC-Token':token,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,cache:'no-store',...(controller?{signal:controller.signal}:{}),...apiTargetOptions()});"
    if new_fetch not in s:
        if old_fetch not in s:
            raise SystemExit("Fetch principal da API não encontrado")
        s = s.replace(old_fetch, new_fetch, 1)

    s = s.replace("fetch(panelBase+'api/moodle/automation/lanes/'+encodeURIComponent(lane.id)+'/screenshot',{headers:{'X-EC-Token':token},cache:'no-store'})",
                  "fetch(apiUrl('moodle/automation/lanes/'+encodeURIComponent(lane.id)+'/screenshot'),{mode:localBridgeActive?'cors':'same-origin',headers:{'X-EC-Token':token},cache:'no-store',...apiTargetOptions()})")
    s = s.replace("fetch(panelBase+'api/screenshot',{cache:'no-store',headers:{'X-EC-Token':token},signal:controller.signal})",
                  "fetch(apiUrl('screenshot'),{mode:localBridgeActive?'cors':'same-origin',cache:'no-store',headers:{'X-EC-Token':token},signal:controller.signal,...apiTargetOptions()})")

    # No cloud-managed browser on hosted page; users connect their own PC through the local bridge.
    s = s.replace("for(const id of ['connectChrome','emptyConnectChrome'])$(id).hidden=remoteMode;",
                  "for(const id of ['connectChrome','emptyConnectChrome'])$(id).hidden=false;", 1)
    runtime_marker = " text('useManagedBrowser',remoteMode?'Usar sessão do servidor':'Usar sessão do assistente');\n"
    if runtime_marker in s and "if(hostedBridgePage)$('useManagedBrowser').hidden=true;" not in s:
        s = s.replace(runtime_marker, runtime_marker + " if(hostedBridgePage)$('useManagedBrowser').hidden=true;\n", 1)

    dialog_start = s.find('<dialog id="browserDialog"')
    dialog_end = s.find('</dialog>', dialog_start)
    if dialog_start < 0 or dialog_end < 0:
        raise SystemExit("Diálogo de conexão Chrome não encontrado")
    dialog = s[dialog_start:dialog_end]
    if 'id="browserDialogIntro"' not in dialog:
        dialog, n = re.subn(r'<p class="note">', '<p id="browserDialogIntro" class="note">', dialog, count=1)
        if n != 1:
            raise SystemExit("Parágrafo de instruções não encontrado")
    if 'id="browserSteps"' not in dialog:
        dialog, n = re.subn(r'<ol class="browserSteps">', '<ol id="browserSteps" class="browserSteps">', dialog, count=1)
        if n != 1:
            raise SystemExit("Lista de instruções não encontrada")
    s = s[:dialog_start] + dialog + s[dialog_end:]

    show_start = s.find('function showBrowserConnect(){')
    show_end = s.find("$('closeBrowserDialog').onclick=", show_start)
    if show_start < 0 or show_end < 0:
        raise SystemExit("Função showBrowserConnect não encontrada")
    show = '''function showBrowserConnect(){
 text('browserConnectMessage','');$('browserConsent').checked=false;
 text('browserDialogTitle','Já estou conectado no Chrome');
 text('browserDialogIntro',hostedBridgePage?'Execute windows\\\\INICIAR_PC.bat neste PC, mantenha a janela aberta e deixe o curso aberto no Chrome. Ao confirmar abaixo, o painel se conecta ao serviço local e o Playwright anexa ao Chrome existente. Senhas e cookies ficam neste PC.':'O assistente reutiliza a aba e o login do Chrome já aberto.');
 const steps=$('browserSteps');steps.replaceChildren();
 const items=hostedBridgePage?[
  'Baixe e extraia o pacote completo do conector Windows. Execute windows\\\\INICIAR_PC.bat e mantenha a janela aberta.',
  'No Chrome 144+, abra chrome://inspect/#remote-debugging e habilite “Allow remote debugging for this browser instance”.',
  'Deixe o EnglishCentral aberto e conectado na mesma janela do Chrome.',
  'Marque a autorização abaixo e clique em Conectar meu Chrome. Permita o acesso à rede local/loopback quando o Chrome solicitar.'
 ]:[
  'Abra seu Chrome e entre no curso desejado.',
  'Habilite a conexão em chrome://inspect/#remote-debugging.',
  'Marque a autorização e clique em Conectar meu Chrome.'
 ];
 for(const value of items){const li=document.createElement('li');li.textContent=value;steps.append(li)}
 $('browserDialog').showModal()
}
'''
    if "text('browserDialogTitle','Já estou conectado no Chrome')" not in s:
        s = s[:show_start] + show + s[show_end:]

    # ORIGINAL V18.13.3 contained the dialog function but did not wire the two visible buttons.
    close_anchor = "$('closeBrowserDialog').onclick="
    button_wiring = "$('connectChrome').onclick=showBrowserConnect;\n$('emptyConnectChrome').onclick=showBrowserConnect;\n"
    if "$('connectChrome').onclick=showBrowserConnect;" not in s:
        if close_anchor not in s:
            raise SystemExit("Ponto de inserção dos eventos do botão Chrome não encontrado")
        s = s.replace(close_anchor, button_wiring + close_anchor, 1)

    form_start = s.find("$('browserConnectForm').onsubmit=async event=>{")
    form_end = s.find(" const raw=$('chromePort').value.trim()", form_start)
    if form_start < 0 or form_end < 0:
        raise SystemExit("Formulário de conexão não encontrado")
    new_prefix = """$('browserConnectForm').onsubmit=async event=>{
 event.preventDefault();
 if(!$('browserConsent').checked){text('browserConnectMessage','Marque a autorização para controlar a sessão do Chrome.');return}
 if(hostedBridgePage&&!localBridgeActive){$('submitBrowserConnect').disabled=true;try{await connectLocalPCBridge()}catch(error){text('browserConnectMessage',error.message||String(error));$('submitBrowserConnect').disabled=false;return}}
"""
    s = s[:form_start] + new_prefix + s[form_end:]

    old_no_token = "if(!token){connected=false;$('dot').classList.remove('active','reconnecting');text('connection','Sem conexão');text('sideCaption','Curso ainda não identificado');$('auth').classList.remove('hide');$('extraDrawer').open=true;if(!missingTokenNotified){notify('Conecte o painel com seu token privado para começar.','tools');missingTokenNotified=true}return}"
    new_no_token = "if(!token){connected=false;$('dot').classList.remove('active','reconnecting');if(hostedBridgePage){text('connection','Aguardando seu PC');text('sideCaption','Chrome local não conectado');text('browserSessionState','Conector Windows não iniciado ou Chrome ainda não anexado.');text('screenStatus','Execute windows\\\\INICIAR_PC.bat e clique em Já estou conectado no Chrome.');text('activityTitle','Conecte seu Chrome');text('activityMsg','O site está pronto. A automação só começa depois que o conector local anexar ao Chrome real.');$('auth').classList.add('hide');$('extraDrawer').open=false;$('connectChrome').hidden=$('emptyConnectChrome').hidden=false;return}text('connection','Sem conexão');text('sideCaption','Curso ainda não identificado');$('auth').classList.remove('hide');$('extraDrawer').open=true;if(!missingTokenNotified){notify('Conecte o painel com seu token privado para começar.','tools');missingTokenNotified=true}return}"
    if new_no_token not in s:
        if old_no_token not in s:
            raise SystemExit("Bloco refresh() sem token não encontrado")
        s = s.replace(old_no_token, new_no_token, 1)

    p.write_text(s, encoding="utf-8")


def main() -> None:
    if len(sys.argv) > 1:
        root = Path(sys.argv[1]).resolve()
    else:
        root = Path(os.getenv("EC_SOURCE_ROOT", "/app")).resolve()
    if not (root / "servidor.py").is_file():
        raise SystemExit(f"Pasta do Studio inválida: {root}")
    patch_server(root)
    patch_mobile_boundary(root)
    patch_launcher(root)
    patch_frontend(root)
    for relative in ("servidor.py", "mobile_app.py", "iniciar.py"):
        py_compile.compile(str(root / relative), doraise=True)
    html = (root / "web" / "index.html").read_text(encoding="utf-8")
    if "connect_over_cdp(endpoint,timeout=25000,no_defaults=True)" not in (root / "servidor.py").read_text(encoding="utf-8"):
        raise SystemExit("A ligação CDP real do Playwright não foi instalada.")
    if "fetch(apiUrl(path)" not in html or "fetch(apiUrl('screenshot')" not in html:
        raise SystemExit("As operações do painel não estão roteadas ao conector local.")
    print(f"Ponte Windows real instalada em {root}")


if __name__ == "__main__":
    main()
