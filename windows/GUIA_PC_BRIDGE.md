# Conectar o Chrome do Windows ao EnglishCentral Studio hospedado

Este pacote mantém o projeto V18.13.3 original e acrescenta uma ponte local real. O Render não tenta acessar o Chrome do computador: o painel HTTPS conversa com o servidor local em \`127.0.0.1:8765\`, e esse servidor usa Playwright CDP para anexar ao Chrome já aberto.

## Pré-requisitos

1. Windows 10/11 e Python 3.10 ou superior instalado com **Add Python to PATH**.
2. Google Chrome 144 ou superior.
3. Acesso à internet na primeira execução para instalar as dependências Playwright.

## Instalação e conexão

1. Extraia o ZIP inteiro para uma pasta. Não execute o BAT de dentro da visualização do ZIP.
2. Abra o Chrome e entre no EnglishCentral/SEDUCTEC normalmente.
3. Na mesma janela do Chrome, abra \`chrome://inspect/#remote-debugging\` e habilite **Allow remote debugging for this browser instance**.
4. Volte à pasta extraída e execute \`windows\\INICIAR_PC.bat\`.
5. Aguarde o ambiente Python e o Playwright serem preparados. Mantenha a janela preta aberta; ela é o servidor local do seu PC.
6. No mesmo computador, abra https://englishcentral-studio.onrender.com.
7. Clique em **Já estou conectado no Chrome**, marque a autorização de controle e depois clique em **Conectar meu Chrome**.
8. Permita o acesso à rede local/loopback quando o Chrome solicitar. O painel então chama o conector local; o backend conecta por CDP ao Chrome existente.

## Como confirmar uma conexão real

A conexão só é considerada concluída quando o backend termina \`playwright.chromium.connect_over_cdp(...)\`, encontra o contexto/aba e devolve a mensagem **Chrome/Edge conectado. A aba e o login existentes foram reutilizados.** Em seguida, a prévia deve mostrar uma captura do conteúdo real do Chrome. Se a conexão falhar, o painel mostra o tipo e o início do erro real do Playwright; não altera o estado para conectado.

O backend usa a assinatura Python compatível \`connect_over_cdp(endpoint, timeout=25000)\`. Não passa \`no_defaults\`, que não é um argumento da API Python.

## Privacidade e encerramento

- O token local é entregue somente à origem HTTPS oficial, em uma chamada de loopback.
- O token permanece na memória da página; não é inserido em URL, \`localStorage\` ou \`sessionStorage\`.
- Senhas, cookies e abas permanecem no Chrome deste computador.
- Para encerrar, pause o assistente e pressione \`Ctrl+C\` na janela do conector. O Studio desconecta o Playwright sem fechar o Chrome pessoal.

Cada computador precisa executar seu próprio conector. O Render não pode acessar um Chrome que esteja em outro PC, desligado ou sem o conector ativo.
