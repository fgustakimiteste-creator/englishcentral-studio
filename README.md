# EnglishCentral Studio V18.13.3

O deploy usa o arquivo completo `EnglishCentral-Studio-18.13.3-G0DMOD3.zip`. A aplicação original — Pessoas, multiagente, Moodle/SEDUCTEC, histórico, fala, MiMi, configurações e automação — é extraída integralmente. O único acréscimo de hospedagem é o gateway de sessões públicas isoladas.

## Acesso público

- O endereço raiz cria uma sessão automaticamente e abre a Pessoa principal (`principal`, exibida como Pessoa principal/Pessoa 1).
- Cada navegador visitante recebe um cookie assinado, HttpOnly e Secure. Nenhum token de painel é colocado no link ou no armazenamento do navegador.
- Cada visitante recebe uma pasta de dados própria. Pessoas adicionais e multiagente continuam disponíveis dentro desse espaço, sem enxergar os dados de outros visitantes.
- Cada Pessoa mantém o navegador, login, preferências e histórico próprios.
- O limite simultâneo de sessões públicas é configurado por `EC_PUBLIC_MAX_SESSIONS` (padrão 3).

## Chrome já conectado

O botão original **Usar meu Chrome já aberto** foi restaurado. O mecanismo original usa CDP/localhost quando o Studio e o Chrome estão no mesmo computador/celular (por exemplo, execução local/Termux). Um site hospedado no Render não consegue anexar-se diretamente ao Chrome/Edge de outro aparelho; isso exigiria uma ponte local/ extensão instalada e conectada ao servidor. No modo Render, a sessão remota própria continua sendo a opção disponível.

## Implantação

O Render usa o Dockerfile e o ZIP original. Configure no Render o segredo `EC_PUBLIC_SESSION_SECRET` com pelo menos 32 caracteres aleatórios. Não coloque o segredo no repositório.
