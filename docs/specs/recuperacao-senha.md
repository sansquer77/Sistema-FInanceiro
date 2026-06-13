# Recuperacao de Senha

## Objetivo

Permitir que um usuario redefina a senha quando esquecer a credencial atual, usando codigo temporario enviado por email SMTP configurado localmente.

## Estado

Implementado.

## Jornada

1. Usuario clica em `Esqueci minha senha` na tela de login.
2. Usuario informa o email cadastrado.
3. O sistema gera um codigo temporario quando o email existe.
4. O codigo e enviado ao email cadastrado.
5. Usuario informa o codigo e a nova senha.
6. Sistema invalida o codigo, troca a senha e encerra sessoes ativas do usuario.

## Regras funcionais

- A nova senha deve ter pelo menos 8 caracteres.
- O codigo expira em 15 minutos.
- Apenas o ultimo codigo ativo de um usuario deve permanecer valido.
- O codigo deve ser marcado como usado apos a troca da senha.
- Sessoes existentes do usuario devem ser encerradas apos a redefinicao.
- A solicitacao retorna resposta generica, mesmo quando o email nao existe.

## Regras de seguranca

- O codigo nao deve ser salvo em texto puro; persistir somente hash.
- A confirmacao de redefinicao deve aceitar apenas codigos nao usados e nao expirados.
- A configuracao SMTP deve ficar fora do codigo fonte.
- `data/email_config.enc` e `data/email_config.key` sao arquivos locais de runtime.

## Criterios de aceite

- Usuario consegue solicitar codigo pela tela de login.
- Usuario recebe o codigo por email quando a configuracao SMTP existe.
- Usuario consegue redefinir a senha usando codigo valido.
- Login antigo deixa de funcionar apos a redefinicao.
- Login novo passa a funcionar.
- Codigo usado ou expirado nao pode redefinir senha novamente.
