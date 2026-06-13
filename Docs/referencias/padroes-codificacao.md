# Referência: Padrões de Codificação

Este documento define regras para que o Sistema Financeiro seja seguro, replicável, entendível e sustentável por outros analistas. Ele deve ser lido junto com o fluxo de SDD antes de qualquer implementação.

## Objetivos

- Código simples de entender e revisar.
- Comportamento especificado antes da implementação.
- Baixo acoplamento entre interface, API, regras de negócio e banco.
- Mudanças pequenas, verificáveis e reversíveis.
- Padrões repetíveis para novos módulos.
- Testes proporcionais ao risco da mudança.

## Princípios

### Clareza antes de abstração

Prefira funções pequenas, nomes explícitos e fluxo direto. Crie abstrações apenas quando reduzirem duplicação real ou isolarem uma regra de negócio importante.

### Uma responsabilidade por camada

- Interface: renderização, interação e chamadas de API.
- API: roteamento, autenticação, autorização e tradução HTTP.
- Domínio: regras de negócio.
- Banco: persistência, schema e consultas.

Regras financeiras não devem ficar espalhadas no front-end.

### Especificação antes do código

Cada funcionalidade relevante deve nascer em `Docs/specs/` com:

- Problema.
- Jornada.
- Dados.
- Regras.
- Critérios de aceite.
- Fora de escopo.

Se a spec não permite verificar sucesso, ela ainda não está pronta.

## Organização de código

### Back-end

- Um módulo de domínio por área funcional.
- Funções públicas com nomes de ação: `create_*`, `update_*`, `list_*`, `archive_*`.
- Validação de entrada no domínio ou em validadores explícitos.
- Erros de domínio com mensagens claras e status HTTP mapeável.
- Consultas parametrizadas sempre.
- Valores monetários em centavos.
- Datas em formato ISO no banco.

### Front-end

- Estado de tela centralizado.
- Renderização derivada do estado atual.
- Funções pequenas para eventos, API, formatação e renderização.
- Nunca confiar no front-end para regra de autorização.
- Textos de interface consistentes com a linguagem do produto.

### Banco de dados

- Tabelas com `created_at` e `updated_at` quando houver alteração ao longo do tempo.
- Arquivamento com `archived_at` para dados históricos.
- Chaves estrangeiras sempre que houver relação entre entidades.
- Índices para filtros frequentes.
- Migrações descritas antes de alterar schema.

## Convenções

### Nomes

- Use nomes em inglês no código.
- Use português na interface e documentação.
- Evite abreviações ambíguas.
- Nome de função deve revelar intenção, não implementação.

### Dinheiro

- Nunca armazenar dinheiro em ponto flutuante.
- Persistir valores monetários em centavos.
- Converter entrada do usuário no limite do domínio.
- Formatar valores apenas na interface ou serializer.

### Datas

- Persistir datas em ISO.
- Exibir datas em formato `pt-BR`.
- Separar data de competência, data de pagamento e data de criação quando forem conceitos diferentes.

## Qualidade e revisão

Antes de concluir uma mudança, conferir:

- A spec foi criada ou atualizada.
- A regra de negócio está no domínio.
- Entradas são validadas.
- Erros são claros.
- Não há duplicação óbvia de lógica.
- Não há dados sensíveis em logs.
- Fluxo principal foi testado manualmente ou automaticamente.
- Casos de erro foram considerados.

## Testes

### Prioridade

1. Testes de regras financeiras.
2. Testes de autorização e acesso a dados do usuário.
3. Testes de parsing de dinheiro e datas.
4. Testes de rotas críticas.
5. Testes manuais de interface.

### Casos mínimos por módulo

- Criação válida.
- Validação de campos obrigatórios.
- Atualização.
- Arquivamento.
- Listagem filtrada por usuário.
- Tentativa de acesso a registro de outro usuário.

## Observabilidade local

- Logs devem ajudar a depurar sem expor senha, sessão, tokens ou dados financeiros detalhados.
- Erros inesperados devem retornar mensagem genérica para o usuário.
- Erros de domínio podem retornar mensagens específicas e seguras.

## Checklist de implementação

- A alteração tem spec.
- A alteração respeita as camadas.
- O código usa padrões já existentes no projeto.
- Valores monetários usam centavos.
- Consultas SQL usam parâmetros.
- Operações por ID validam o dono do registro.
- Foi verificado o fluxo feliz.
- Foi verificado pelo menos um fluxo de erro.
