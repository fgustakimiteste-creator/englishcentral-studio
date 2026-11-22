# EnglishCentral Studio — conexão real com o Chrome do Windows

Este pacote mantém o ZIP original V18.13.3 e aplica uma pequena ponte local. O Render serve a interface pública; o servidor local neste PC usa Playwright/CDP para anexar ao Chrome já aberto. Não é aberto um perfil novo e não se copiam cookies ou senhas para a nuvem.

## Pré-requisitos

- Windows 10 ou 11.
- Python 3.10 ou superior e Python Launcher (com **Add Python to PATH** marcado).
- Google Chrome 144 ou superior.
- Conexão à internet na primeira execução para instalar as dependências.

## Instalar e conectar

1. Extraia o pacote inteiro para uma pasta normal do Windows. Não execute o BAT de dentro do ZIP.
2. Abra o Google Chrome normalmente, entre no EnglishCentral e deixe a página do curso aberta.
3. Na mesma janela do Chrome, abra `chrome://inspect/#remote-debugging` e marque **Allow remote debugging for this browser instance**.
4. Na pasta extraída, execute `windows\INICIAR_PC.bat`.
5. Na primeira execução, aguarde a criação do ambiente Python e a instalação do Playwright. Isso pode levar alguns minutos. Não feche a janela preta.
6. No mesmo PC e no mesmo Chrome, abra https://englishcentral-studio.onrender.com.
7. Clique em **Já estou conectado no Chrome**, marque a autorização de controle e clique em **Conectar meu Chrome**.
8. Quando o Chrome pedir permissão para acessar o computador/rede local, permita. A ponte busca a credencial no servidor local e a mantém somente em memória no painel.
9. A conexão só termina quando o backend anexar ao Chrome e retornar **Chrome/Edge conectado. A aba e o login existentes foram reutilizados.** A prévia mostrará a página real do curso.

## O que o conector realmente faz

- Inicia o servidor local em `127.0.0.1:8765`, sem publicar essa porta na internet.
- O endpoint `/api/bridge/bootstrap` libera o token apenas para a origem oficial do painel e para conexões loopback.
- O painel encaminha API, captura de tela e cliques para o servidor local depois do bootstrap.
- O endpoint original `/api/browser/connect` usa `playwright.chromium.connect_over_cdp('chrome', no_defaults=True)` para anexar ao Chrome existente.
- O Playwright não fecha o Chrome pessoal quando a sessão é desconectada.
- O token não vai para URL, `localStorage` ou `sessionStorage`. Cookies e senha do EnglishCentral continuam no perfil local do Chrome.

## Encerrar

Pause o assistente no painel e pressione `Ctrl+C` na janela preta. O Chrome e as abas continuam abertos. Para utilizar novamente, execute o BAT outra vez.

Cada PC precisa executar o próprio conector e usar seu próprio login. O Render não consegue controlar o Chrome de um computador que esteja desligado ou sem o conector ativo.
