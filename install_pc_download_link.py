from pathlib import Path
p = Path('/app/web/index.html')
s = p.read_text(encoding='utf-8')
marker = '<button id="submitBrowserConnect" class="btn primary" type="submit">Conectar meu Chrome</button>'
replacement = marker + '<a id="downloadWindowsConnector" class="btn" href="https://github.com/fgustakimiteste-creator/englishcentral-studio/archive/refs/heads/main.zip" target="_blank" rel="noopener">Baixar conector Windows</a>'
if 'id="downloadWindowsConnector"' not in s:
    if marker not in s:
        raise SystemExit('Não encontrei o botão Conectar meu Chrome para inserir o download do conector.')
    s = s.replace(marker, replacement, 1)
p.write_text(s, encoding='utf-8')
