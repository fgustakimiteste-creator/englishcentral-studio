# EnglishCentral Studio V18.13.5

O Render extrai o ZIP completo `EnglishCentral-Studio-18.13.5-G0DMOD3.zip` sem redesenhar a interface nem substituir os módulos originais. O único ajuste de hospedagem é a ativação automática da sessão privada do painel.

## Acesso privado automático

- Ao entrar pelo endereço principal, o servidor cria ou recupera a sessão daquele navegador e abre a Pessoa principal.
- O navegador recebe apenas um cookie assinado `HttpOnly`, `Secure` e `SameSite=Lax`. A validade é de 365 dias e é renovada quando o painel é aberto novamente.
- O token privado real continua no servidor, no arquivo `token_painel.txt` de cada perfil. O navegador não recebe esse token, não precisa copiá-lo nem enviá-lo a ninguém.
- O token não aparece na URL, no JavaScript, em `localStorage`/`sessionStorage` nem nos cabeçalhos das chamadas do painel. As requisições usam o cookie privado automaticamente.
- Cada navegador/aparelho recebe uma sessão independente; dentro dela, cada Pessoa mantém seu token e seus dados próprios.
- **Esquecer acesso** encerra a sessão daquele navegador. Na próxima entrada, outra sessão privada é criada automaticamente.

## Configuração do Render

O serviço usa `EC_REMOTE_MODE=1`, `EC_PUBLIC_SESSIONS=1` e `EC_PUBLIC_URL=https://englishcentral-studio.onrender.com`. A assinatura do cookie usa `EC_PUBLIC_SESSION_SECRET`, definido como segredo no ambiente do Render (mínimo de 32 caracteres). Esse segredo não deve ser incluído no repositório.
