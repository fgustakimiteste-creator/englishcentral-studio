"""Apply the authenticated Windows-to-hosted-panel bridge to original V18.13.3 source."""
from __future__ import annotations
import sys
from pathlib import Path

def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    if new in source:
        return
    if old not in source:
        raise SystemExit(f"Patch target not found: {path.name}: {old[:100]!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: py -3 apply_pc_bridge.py CAMINHO_DA_PASTA_EnglishCentral-Studio")
    root = Path(sys.argv[1]).resolve()
    if not (root / "servidor.py").is_file() or not (root / "web" / "index.html").is_file():
        raise SystemExit("A pasta informada não contém o projeto EnglishCentral Studio V18.13.3.")

    replace_once(root / "servidor.py",
        "from fastapi import Depends, FastAPI, Header, HTTPException\n",
        "from fastapi import Depends, FastAPI, Header, HTTPException, Request\n")
    replace_once(root / "servidor.py",
        "REMOTE_CONFIG = load_remote_config()\n",
        "REMOTE_CONFIG = load_remote_config()\n"
        "LOCAL_PC_BRIDGE = os.getenv('EC_PC_BRIDGE', '0') == '1'\n"
        "LOCAL_PANEL_ORIGIN = os.getenv('EC_LOCAL_PANEL_ORIGIN', 'https://englishcentral-studio.onrender.com').strip().rstrip('/')\n")
    replace_once(root / "servidor.py",
        "app = FastAPI(title='EnglishCentral Studio — V18.13.1 Automação paralela SEDUCTEC', docs_url=None, redoc_url=None, lifespan=lifespan)\n",
        "app = FastAPI(title='EnglishCentral Studio — V18.13.1 Automação paralela SEDUCTEC', docs_url=None, redoc_url=None, lifespan=lifespan)\n\n"
        "@app.middleware('http')\n"
        "async def pc_bridge_cors(request: Request, call_next):\n"
        "    origin = request.headers.get('origin', '').rstrip('/')\n"
        "    if not LOCAL_PC_BRIDGE or origin != LOCAL_PANEL_ORIGIN:\n"
        "        return await call_next(request)\n"
        "    if request.method == 'OPTIONS':\n"
        "        response = Response(status_code=204)\n"
        "    else:\n"
        "        response = await call_next(request)\n"
        "    response.headers['Access-Control-Allow-Origin'] = LOCAL_PANEL_ORIGIN\n"
        "    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'\n"
        "    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-EC-Token'\n"
        "    response.headers['Access-Control-Max-Age'] = '600'\n"
        "    response.headers['Vary'] = 'Origin'\n"
        "    if request.headers.get('access-control-request-private-network') == 'true':\n"
        "        response.headers['Access-Control-Allow-Private-Network'] = 'true'\n"
        "    return response\n")
    replace_once(root / "servidor.py",
        "    return local_token(TOKEN_FILE)\n\n\ndef require_auth(x_ec_token: str | None = Header(default=None)):\n",
        "    return local_token(TOKEN_FILE)\n\n\n"
        "@app.get('/api/bridge/bootstrap')\n"
        "async def pc_bridge_bootstrap(request: Request):\n"
        "    if not LOCAL_PC_BRIDGE:\n"
        "        raise HTTPException(404, 'Ponte Windows desativada.')\n"
        "    origin = request.headers.get('origin', '').rstrip('/')\n"
        "    if origin != LOCAL_PANEL_ORIGIN:\n"
        "        raise HTTPException(403, 'Origem não autorizada para a ponte local.')\n"
        "    peer = request.client.host if request.client else ''\n"
        "    if peer not in {'127.0.0.1', '::1'}:\n"
        "        raise HTTPException(403, 'A ponte aceita apenas conexões locais neste computador.')\n"
        "    return Response(content=json.dumps({'ok': True, 'token': get_token(), 'agent': 'EnglishCentral Studio PC'}),\n"
        "                    media_type='application/json',\n"
        "                    headers={'Cache-Control': 'no-store, max-age=0', 'Pragma': 'no-cache', 'Vary': 'Origin'})\n\n\n"
        "def require_auth(x_ec_token: str | None = Header(default=None)):\n")
    # Playwright Python rejects the no_defaults keyword on connect_over_cdp.
    replace_once(root / "servidor.py",
        "connect_over_cdp(endpoint,timeout=25000,no_defaults=True)",
        "connect_over_cdp(endpoint,timeout=25000)")
    old_error = "raise HTTPException(409,TERMUX_CHROME_HELP if TERMUX else 'Não consegui conectar ao Chrome/Edge aberto. No Chrome 144 ou superior, abra chrome://inspect/#remote-debugging, habilite a conexão e aceite a solicitação no próprio Chrome. O assistente não abriu outro perfil.') from exc"
    new_error = "raise HTTPException(409,TERMUX_CHROME_HELP if TERMUX else ('Não consegui conectar ao Chrome/Edge aberto. No Chrome 144 ou superior, abra chrome://inspect/#remote-debugging, habilite a conexão e aceite a solicitação no próprio Chrome. Detalhe real: '+type(exc).__name__+': '+((str(exc).strip().splitlines() or [''])[0][:220]))) from exc"
    replace_once(root / "servidor.py", old_error, new_error)

    replace_once(root / "mobile_app.py",
        "        expected = self.config.origin if self.config.enabled and not local else str(request.base_url).rstrip('/')\n",
        "        bridge_origin = os.getenv('EC_LOCAL_PANEL_ORIGIN', 'https://englishcentral-studio.onrender.com').strip().rstrip('/')\n"
        "        bridge_request = (os.getenv('EC_PC_BRIDGE', '0') == '1' and local and origin == bridge_origin)\n"
        "        expected = bridge_origin if bridge_request else (self.config.origin if self.config.enabled and not local else str(request.base_url).rstrip('/'))\n")
    replace_once(root / "iniciar.py",
        "        print(f'Painel aberto em http://127.0.0.1:{PORT}', flush=True)\n"
        "        print('Para encerrar, feche esta janela ou pressione Ctrl+C.', flush=True)\n"
        "        webbrowser.open(url)\n",
        "        if os.getenv('EC_PC_BRIDGE', '0') == '1':\n"
        "            print('Ponte Windows ativa em http://127.0.0.1:%s' % PORT, flush=True)\n"
        "            print('Abra https://englishcentral-studio.onrender.com e escolha “Já estou conectado no Chrome”.', flush=True)\n"
        "            print('Mantenha esta janela aberta enquanto usar a automação.', flush=True)\n"
        "        else:\n"
        "            print(f'Painel aberto em http://127.0.0.1:{PORT}', flush=True)\n"
        "            webbrowser.open(url)\n"
        "        print('Para encerrar, pressione Ctrl+C.', flush=True)\n")

    import py_compile
    for relative in ("servidor.py", "mobile_app.py", "iniciar.py"):
        py_compile.compile(str(root / relative), doraise=True)
    source = (root / "servidor.py").read_text(encoding="utf-8")
    if "connect_over_cdp(endpoint,timeout=25000,no_defaults=True)" in source:
        raise SystemExit("O argumento incompatível no_defaults=True permaneceu.")
    print("Ponte local aplicada; conexão Playwright CDP corrigida e compilada. Abra INICIAR_PC.bat.")

if __name__ == "__main__":
    main()
