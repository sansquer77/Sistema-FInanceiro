# Recuperacao de Senha

## Objetivo

Permitir que um usuario redefina a senha quando esquecer a credencial atual, mantendo o fluxo simples para uso local e sem exigir servico externo de email nesta fase.

## Jornada

1. Usuario clica em `Esqueci minha senha` na tela de login.
2. Usuario informa o email cadastrado.
3. O sistema gera um codigo temporario quando o email existe.
4. Como o app ainda roda localmente sem provedor de email, o codigo e exibido na propria tela.
5. Usuario informa o codigo e a nova senha.
6. Sistema invalida o codigo, troca a senha e encerra sessoes ativas do usuario.

## Regras Funcionais

- A nova senha deve ter pelo menos 8 caracteres.
- O codigo expira em 15 minutos.
- Apenas o ultimo codigo ativo de um usuario deve permanecer valido.
- O codigo deve ser marcado como usado apos a troca da senha.
- Sessoes existentes do usuario devem ser encerradas apos a redefinicao.

## Regras de Seguranca

- O codigo nao deve ser salvo em texto puro; persistir somente hash.
- A confirmacao de redefinicao deve aceitar apenas codigos nao usados e nao expirados.
- A resposta de solicitacao deve ser generica para emails inexistentes.
- Em ambiente com email real, o codigo deve deixar de ser exibido na tela e deve ser enviado por canal verificado.

## Criterios de Aceite

- Usuario consegue solicitar codigo pela tela de login.
- Usuario consegue redefinir a senha usando codigo valido.
- Login antigo deixa de funcionar apos a redefinicao.
- Login novo passa a funcionar.
- Codigo usado ou expirado nao pode redefinir senha novamente.
