# Conectar o Chrome do Windows ao EnglishCentral Studio hospedado

Este pacote mantém o projeto V18.13.3 original e acrescenta uma ponte local real. O Render não tenta acessar localhost do seu computador: o navegador abre uma conexão local com o conector Windows, e o servidor do próprio PC conecta o Playwright ao Chrome já aberto.

## Instalação

1. Baixe o ZIP completo do repositório e extraia tudo para uma pasta do Windows.
2. Instale Python 3.10 ou superior em https://www.python.org/downloads/windows/ e marque **Add Python to PATH**.
3. No Chrome do PC, abra `chrome://inspect/#remote-debugging` e habilite **Allow remote debugging for this browser instance**. O modo por canal `chrome` exige Chrome 144+ e Playwright 1.62+.
4. Deixe o EnglishCentral aberto e entre na sua conta normalmente.
5. Execute `windows\INICIAR_PC.bat`. Na primeira execução, o Studio cria o ambiente virtual e instala as dependências do `requirements.txt`. Mantenha a janela aberta.
6. No mesmo computador e no mesmo Chrome, abra https://englishcentral-studio.onrender.com.
7. Clique em **Já estou conectado no Chrome**. Quando o Chrome pedir permissão para o site acessar o loopback/rede local, permita.
8. Marque **Quero permitir que este assistente controle a sessão do meu Chrome** e clique em **Conectar meu Chrome**. O Playwright chama `connect_over_cdp('chrome', no_defaults=True)` e seleciona uma aba existente.

## O que é realmente executado

- `INICIAR_PC.bat` inicia o servidor FastAPI original no próprio PC, limitado a `127.0.0.1:8765`.
- `/api/bridge/bootstrap` só entrega o token à origem HTTPS oficial, através de uma conexão local.
- O token fica em memória no painel; não vai para URL, localStorage ou sessionStorage.
- `/api/browser/connect` conecta por CDP ao Chrome já aberto.
- As operações e capturas seguem do navegador para o conector local; não usam um Chrome simulado no Render.
- Cada computador executa sua própria ponte e usa seu próprio login. O Render não consegue acessar o Chrome de um PC desligado ou sem o conector ativo.

## Encerrar

Pause o assistente no painel e pressione `Ctrl+C` na janela do conector. As abas do Chrome continuam abertas.

A ligação final com sua conta real deve ser autorizada no Chrome do Windows; não é possível confirmar remotamente o consentimento ou o estado da sessão do computador.
