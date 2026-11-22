from pathlib import Path
p = Path('/app/servidor.py')
s = p.read_text(encoding='utf-8')
old = """        person = await asyncio.to_thread(manager.create, 'Visitante')
        response = RedirectResponse(f'/p/{person["id"]}/', status_code=303)
"""
new = """        person = await asyncio.to_thread(manager.create, 'Visitante')
        # Gere o token privado no servidor sem iniciar o worker até a primeira chamada da API.
        await asyncio.to_thread(local_token, manager.data_dir(person['id']) / 'token_painel.txt')
        response = RedirectResponse(f'/p/{person["id"]}/', status_code=303)
"""
if old not in s:
    raise SystemExit('Could not find public session creation block in servidor.py')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
