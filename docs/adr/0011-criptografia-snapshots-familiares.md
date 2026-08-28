---
tipo: adr
area: seguranca
status: rascunho
versao: 0.1
atualizado: 2026-08-28
relacionados:
  - "[[../specs/consolidacao-familiar]]"
  - "[[../specs/seguranca-autenticacao]]"
  - "[[../distribuição]]"
  - "[[0001-stack-local-sem-framework]]"
  - "[[0010-segredos-criptografados-sqlite]]"
  - "[[../arquitetura]]"
tags: [adr, "area/seguranca", "status/rascunho"]
aliases: ["ADR-0011", "Criptografia de snapshots familiares"]
---

# ADR-0011 — Criptografia transportável de snapshots familiares

> [!info] Status
> **rascunho** · área: `seguranca` · atualizado em 2026-08-28 · relacionados: [[../specs/consolidacao-familiar]], [[../specs/seguranca-autenticacao]], [[../distribuição]], [[0010-segredos-criptografados-sqlite]]

## Problema

A [[../specs/consolidacao-familiar]] propõe transportar snapshots financeiros mensais entre instalações independentes do Sistema Financeiro. O arquivo pode circular por e-mail, mensageiro, nuvem ou mídia removível, meios que não são controlados pelo app. O conteúdo precisa permanecer confidencial e qualquer alteração ou senha incorreta deve impedir integralmente a importação.

A biblioteca padrão do Python não oferece uma API moderna de criptografia autenticada adequada a esse arquivo transportável. Ampliar a construção criptográfica própria de `financeiro/secure_config.py` aumentaria o risco de erro e criaria um formato externo dependente de código criptográfico mantido pelo projeto.

## Decisão proposta

Adotar a dependência `cryptography` exclusivamente para o envelope transportável da Consolidação Familiar, com:

- `scrypt` para derivar uma chave de 32 bytes a partir da senha familiar;
- `AES-256-GCM` por meio da API `AESGCM` para confidencialidade e integridade autenticada;
- salt aleatório exclusivo por arquivo;
- nonce aleatório exclusivo por arquivo;
- envelope versionado com formato, versão e parâmetros criptográficos;
- cabeçalho autenticado como dados adicionais, sem expor integrante, grupo, mês ou valores financeiros;
- JSON financeiro integralmente contido no texto cifrado;
- autenticação completa antes de interpretar ou persistir qualquer campo.

Parâmetros iniciais candidatos do `scrypt`:

| Parâmetro | Valor candidato |
|---|---|
| Comprimento da chave | 32 bytes |
| Salt | 16 bytes aleatórios |
| `n` | `2^17` |
| `r` | `8` |
| `p` | `1` |

O nonce candidato para `AESGCM` é de 12 bytes aleatórios. Os valores finais permanecem condicionados a benchmark nos runtimes distribuídos e devem ser registrados na versão implementada deste ADR.

## Senha e ciclo da operação

- A senha é fornecida em cada exportação e importação.
- A exportação exige que o usuário confirme a senha antes de gerar o arquivo.
- A senha nunca é persistida pelo app.
- A senha existe somente em memória durante a operação e não é gravada em Preferências, SQLite, arquivos temporários, logs, respostas de API ou envelopes exportados.
- Não existe opção **Lembrar nesta máquina**, hash de verificação persistido ou recuperação da senha.
- A senha é compartilhada pelos integrantes por um meio externo, fora do controle do app.
- Senha incorreta e arquivo adulterado produzem falha integral e mensagem amigável equivalente, sem revelar detalhes do mecanismo.
- Senha esquecida torna aquele arquivo irrecuperável pelo app.

## Envelope proposto

```json
{
  "format": "sistema-financeiro-family",
  "version": 1,
  "kdf": {
    "name": "scrypt",
    "n": 131072,
    "r": 8,
    "p": 1,
    "salt": "base64"
  },
  "cipher": {
    "name": "aes-256-gcm",
    "nonce": "base64"
  },
  "ciphertext": "base64"
}
```

O importador aceita somente versões, algoritmos e faixas de parâmetros explicitamente suportados. Parâmetros declarados pelo arquivo não podem provocar consumo arbitrário de CPU ou memória antes da rejeição.

## Distribuição e compatibilidade

`cryptography` publica wheels com bibliotecas vinculadas para macOS, Windows e Linux. A dependência deve ser instalada durante os workflows oficiais e incorporada ao runtime one-folder do PyInstaller gerado no sistema operacional alvo.

A decisão somente pode mudar para `implementado` depois de comprovar:

1. build PyInstaller bem-sucedido em `macos-latest`, `windows-latest` e `ubuntu-latest`, usando a versão Python suportada pelos workflows;
2. execução em máquina limpa sem exigir Python, Rust ou OpenSSL instalados separadamente;
3. round-trip de exportação e importação dentro de cada runtime empacotado;
4. interoperabilidade bidirecional macOS ↔ Windows, Windows ↔ Linux e Linux ↔ macOS;
5. rejeição de senha incorreta e de arquivo com um byte alterado;
6. confirmação das arquiteturas de CPU efetivamente suportadas por plataforma;
7. inspeção dos pacotes para confirmar inclusão dos componentes necessários e ausência de dados, chaves ou segredos de build.

## Alternativas consideradas

### Reutilizar `secure_config.py`

Rejeitada para o formato transportável. A infraestrutura atual protege segredos locais com uma chave aleatória externa ao banco, enquanto o novo caso deriva a chave de uma senha humana compartilhada e exige interoperabilidade duradoura entre plataformas. Reutilizar a construção criptográfica própria ampliaria seu escopo e o risco de manutenção.

### PBKDF2 + AES-GCM

Mantida como fallback conceitual caso `scrypt` não seja operacional nos pacotes suportados. PBKDF2 possui ampla compatibilidade, mas oferece menor resistência baseada em memória contra tentativas offline de senha.

### Argon2id + AES-GCM

Não escolhida para a primeira versão porque exigiria dependência ou binding adicional além de `cryptography`. Pode ser reavaliada se a biblioteca adotada passar a oferecer suporte direto estável ou se os benchmarks mostrarem necessidade.

### `scrypt` + ChaCha20-Poly1305

Tecnicamente adequada, mas não escolhida para reduzir alternativas no contrato inicial. AES-GCM é amplamente suportado pela dependência e suficiente para snapshots pequenos processados integralmente em memória.

### ZIP protegido por senha

Rejeitada. O suporte e a segurança variam entre ferramentas, o formato pode expor nomes de arquivos/metadados e a biblioteca padrão não oferece uma solução AES interoperável adequada para gravação.

### Senha armazenada em Preferências

Rejeitada. A persistência facilitaria a operação, mas transformaria uma senha de transporte em segredo local recuperável e criaria ciclo de troca, revogação e sincronização entre instalações.

## Consequências

- O projeto passa a ter uma dependência externa de runtime com componentes nativos.
- Os builds oficiais precisam fixar e atualizar conscientemente a versão de `cryptography`.
- Cada plataforma continua sendo empacotada no próprio sistema operacional alvo.
- O arquivo pode ser aberto entre plataformas sem compartilhar chaves locais do app.
- Não há recuperação de arquivo quando a senha é perdida.
- Parâmetros do KDF precisam equilibrar resistência a tentativa offline e desempenho nas máquinas suportadas.
- A senha protege apenas o transporte; depois da importação, as métricas ficam em colunas analíticas normais do SQLite conforme a [[../specs/consolidacao-familiar]].
- Atualizações futuras do formato devem manter leitura das versões anteriores ou apresentar incompatibilidade explícita e segura.

## Critérios para aprovação

- Dado o mesmo snapshot e senha, quando o arquivo é gerado duas vezes, então salt, nonce e texto cifrado são diferentes.
- Dado um arquivo válido, quando aberto com a senha correta, então o conteúdo original é recuperado integralmente.
- Dado uma senha incorreta, quando o arquivo é aberto, então nenhum campo financeiro é entregue ao importador.
- Dado um arquivo alterado, quando a autenticação é executada, então nenhum campo financeiro é entregue ao importador.
- Dado um envelope com parâmetros fora das faixas aceitas, quando validado, então é rejeitado antes de alocar recursos excessivos.
- Dado o fim de uma exportação ou importação, quando persistências e logs são inspecionados, então a senha não está presente.
- Dado os runtimes oficiais das três plataformas, quando executam a matriz de interoperabilidade, então os arquivos são compatíveis entre si.

## Pendências

> [!question] Pendências
> Este ADR permanece em rascunho até as validações abaixo serem concluídas.

- [ ] Definir comprimento mínimo e máximo da senha e a orientação de frase-senha na interface.
- [ ] Executar benchmark de `scrypt` nos runtimes PyInstaller macOS, Windows e Linux e confirmar ou ajustar `n`, `r` e `p`.
- [ ] Definir e fixar a faixa inicial de versões de `cryptography` compatível com Python 3.13 e com os runners oficiais.
- [ ] Confirmar suporte de arquitetura macOS Intel e Apple Silicon, Windows x86-64 e Linux x86-64, ou reduzir explicitamente a matriz suportada.
- [ ] Executar a matriz completa de round-trip e interoperabilidade descrita neste ADR.
- [ ] Definir limite máximo do envelope antes da derivação e descriptografia.

## Changelog

- `0.1` — 2026-08-28 — Proposta inicial: dependência `cryptography`, derivação `scrypt`, criptografia autenticada `AES-256-GCM`, senha somente em memória e aprovação condicionada a PyInstaller e interoperabilidade entre macOS, Windows e Linux.

## Relacionados

- [[../specs/consolidacao-familiar]]
- [[../specs/seguranca-autenticacao]]
- [[../distribuição]]
- [[0001-stack-local-sem-framework]]
- [[0010-segredos-criptografados-sqlite]]
- [[../arquitetura]]
