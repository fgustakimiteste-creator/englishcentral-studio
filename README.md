# EnglishCentral Studio

**Agente de automação e respostas para o EnglishCentral.**

O EnglishCentral Studio reúne em um único painel os recursos de operação do agente, organização de perfis e acompanhamento de rotinas automatizadas. A proposta é facilitar tarefas recorrentes no ambiente EnglishCentral, mantendo cada perfil e sua sessão de acesso separados.

<https://englishcentral-studio.onrender.com>

## O que o agente oferece

- **Automação de respostas e rotinas:** centraliza os fluxos de trabalho usados na operação do EnglishCentral.
- **Perfis independentes:** organiza o acesso por pessoa, com dados e credenciais mantidos separadamente.
- **Painel de acompanhamento:** apresenta o estado da aplicação e permite acompanhar atividades e capturas disponibilizadas pelo ambiente.
- **Integração com o Chrome no Windows:** quando necessária, a ponte local conecta o painel ao navegador deste computador para executar ações reais. A conexão é opcional e depende da autorização do usuário.
- **Acesso pela web:** o painel fica disponível pelo endereço hospedado, sem exigir que o usuário abra o projeto pelo GitHub.

## Acessar o agente

**Painel online:** https://englishcentral-studio.onrender.com

**Código-fonte e versões:** https://github.com/fgustakimiteste-creator/englishcentral-studio

## Sessão privada e proteção de acesso

No ambiente hospedado, o servidor cria ou recupera uma sessão própria para cada navegador. O navegador recebe apenas um cookie de sessão assinado, com as propriedades `HttpOnly`, `Secure` e `SameSite=Lax`.

O token privado de cada perfil permanece no servidor, no arquivo `token_painel.txt` correspondente. Ele não é colocado na URL, não é exposto ao JavaScript da página e não precisa ser copiado ou enviado pelo usuário. Cada navegador ou aparelho mantém uma sessão independente.

A validade da sessão é de 365 dias e é renovada quando o painel é aberto novamente. A opção **Esquecer acesso** encerra a sessão daquele navegador.

## Integração local com Chrome no Windows

A integração com o Chrome é um recurso opcional para fluxos que precisam atuar no navegador aberto no próprio computador. Quando utilizada, a ponte local deve ser iniciada no Windows e o acesso ao navegador precisa ser autorizado pelo usuário. Senhas e cookies do Chrome não são enviados ao serviço hospedado.

Consulte o arquivo `LEIA_PRIMEIRO_WINDOWS.txt` e o guia em `windows/GUIA_PC_BRIDGE.md` para configurar esse recurso.

## Versão

**EnglishCentral Studio 18.13.5**
