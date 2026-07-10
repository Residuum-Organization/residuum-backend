# Guia de Integração — Backend → Front

Documento de referência para o front integrar os endpoints entregues em resposta
às pendências (`PEDENCIAS-ENVIADAS-PELO-FRONT.md`).

- **Base URL:** a mesma da API (ex.: `https://<host>` / `http://localhost:8000`).
- **Autenticação:** `Authorization: Bearer <access_token>` em todas as rotas, exceto as marcadas como **Público**.
- **Admin:** rotas marcadas **Admin** exigem que o usuário logado tenha `role = "admin"` (senão retorna `403`).
- **Formato de erro** (padrão FastAPI): `{ "detail": "mensagem" }`. Códigos usados: `400` (regra de negócio), `401` (token ausente/inválido), `403` (sem permissão), `404` (não encontrado).

> ⚠️ **Atenção — mudança que quebra o comportamento atual:** a resposta do `POST /login`
> mudou (agora inclui `refresh_token`). Veja a seção **1. Autenticação**.

---

## 0. Checklist rápido do front

- [ ] Ler `refresh_token` no login e guardar (item da função "Lembre de mim").
- [ ] Implementar renovação automática via `POST /refresh` quando o access token expirar (401).
- [ ] Tela inicial do morador: consumir `GET /usuario/metricas` para o gráfico "Entregas do Ano".
- [ ] Tela de sorteios: `GET /sorteios` + botão comprar (`POST /sorteios/{id}/comprar-bilhete`).
- [ ] Tela de vouchers: `GET /vouchers` + resgatar (`POST /vouchers/{id}/resgatar`) e mostrar o **código promocional** retornado.
- [ ] Tela de campanhas: `GET /campanhas` + participar (`POST /campanhas/{id}/participar`).
- [ ] Painel admin: aprovação/rejeição de pontos de coleta, e cadastro de sorteios/vouchers/campanhas.

---

## 1. Autenticação e "Lembre de mim" (Refresh Token)

### 1.1. Login — resposta atualizada
`POST /login` — **Público**

Request:
```json
{ "email": "user@exemplo.com", "senha": "minhasenha" }
```

Response `200` (**mudou**, agora tem `refresh_token`):
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "usuario_id": 1
}
```

**Ajuste no front:**
- Guardar `access_token` (uso normal) e `refresh_token` (renovação).
- Se "Lembre de mim" estiver marcado, persistir o `refresh_token` em storage seguro/persistente. Se não, pode manter só em memória/sessão.

### 1.2. Renovar o access token
`POST /refresh` — **Público**

Request:
```json
{ "refresh_token": "eyJhbGciOi..." }
```

Response `200`:
```json
{
  "access_token": "novo_access...",
  "refresh_token": "novo_refresh...",
  "token_type": "bearer"
}
```

**Comportamento importante:**
- O `access_token` expira em **60 minutos**; o `refresh_token` em **30 dias** (configurável no backend).
- A cada `/refresh` é feita **rotação**: guarde sempre o novo `refresh_token` retornado.
- Um `refresh_token` **não funciona** como token de acesso em rotas normais (retorna `401`). Use-o só no `/refresh`.

**Fluxo sugerido no front:** ao receber `401` numa chamada, chamar `/refresh`; se der `200`, refazer a chamada original com o novo access token; se o `/refresh` também der `401`, mandar o usuário para o login.

---

## 2. Métricas do usuário — gráfico "Entregas do Ano"

`GET /usuario/metricas` — requer login

Query params:
- `ano` (opcional, default = ano atual). Ex.: `GET /usuario/metricas?ano=2026`

Response `200`:
```json
{
  "ano": 2026,
  "total_kg_ano": 42.5,
  "total_descartes_ano": 7,
  "pontuacao_total": 320,
  "por_mes": [
    { "mes": 1, "kg": 0.0, "descartes": 0 },
    { "mes": 2, "kg": 12.5, "descartes": 2 },
    { "mes": 3, "kg": 30.0, "descartes": 5 }
    // ... sempre os 12 meses (1 a 12), preenchidos com zero quando não há entregas
  ]
}
```

**Notas:**
- Considera apenas descartes com `status = "confirmado"` (kg realmente validado pela cooperativa).
- `por_mes` sempre traz os 12 meses em ordem — o front pode plotar direto sem preencher lacunas.

---

## 3. Sorteios

### 3.1. Listar sorteios ativos
`GET /sorteios` — **Público**

Response `200`: lista de sorteios
```json
[
  {
    "id": 1,
    "titulo": "Sorteio de Julho",
    "descricao": "Concorra a prêmios reciclando!",
    "premio": "R$ 500 em dinheiro",
    "custo_pontos": 100,
    "status": "ativo",
    "data_inicio": "2026-07-01T00:00:00Z",
    "data_fim": "2026-07-31T23:59:59Z",
    "criado_em": "2026-07-01T10:00:00Z",
    "atualizado_em": "2026-07-01T10:00:00Z"
  }
]
```

`GET /sorteios/{id}` — **Público** — detalhe de um sorteio.

### 3.2. Comprar bilhete (usuário)
`POST /sorteios/{id}/comprar-bilhete` — requer login

Sem corpo. Response `201`:
```json
{
  "id": 10,
  "sorteio_id": 1,
  "numero": 7,
  "pontos_utilizados": 100,
  "criado_em": "2026-07-09T14:00:00Z",
  "titulo": "Sorteio de Julho",
  "premio": "R$ 500 em dinheiro"
}
```

**Regras (o front deve tratar os erros `400`):**
- **1 bilhete por usuário por sorteio.** Se já tiver: `"Você já possui um bilhete neste sorteio."`
- **Critério de participação:** o usuário precisa ter **pelo menos 1 descarte confirmado com validação por presença (GPS)**. Senão: `"Você precisa ter um descarte confirmado com validação por presença (GPS) para participar."`
  - Sugestão de UX: só habilitar o botão "Participar" quando o usuário já tiver esse descarte (dá pra inferir por `total_descartes_ano > 0` em `/usuario/metricas`, mas o backend é a fonte da verdade).
- **Saldo:** precisa ter `pontuacao_total >= custo_pontos`. Senão: `"Pontuacao insuficiente para comprar o bilhete."`
- O `numero` é a **numeração do cupom** dentro do sorteio (sequencial), usada no sorteio manual via dashboard.

### 3.3. Meus bilhetes
`GET /sorteios/meus-bilhetes` — requer login — lista os bilhetes do usuário (mesmo formato do item 3.2).

### 3.4. Cadastrar sorteio (Admin)
`POST /sorteios` — **Admin**

Request:
```json
{
  "titulo": "Sorteio de Agosto",
  "descricao": "opcional",
  "premio": "Smartphone",
  "custo_pontos": 150,
  "status": "ativo",
  "data_inicio": "2026-08-01T00:00:00Z",
  "data_fim": "2026-08-31T23:59:59Z"
}
```
Response `201`: o sorteio criado (formato do item 3.1).

---

## 4. Vouchers

### 4.1. Listar vouchers disponíveis
`GET /vouchers` — **Público**

Response `200`:
```json
[
  {
    "id": 1,
    "titulo": "10% de desconto",
    "descricao": "Desconto na loja parceira",
    "parceiro": "Loja Verde",
    "custo_pontos": 50,
    "quantidade_disponivel": 20,
    "status": "ativo",
    "data_inicio": null,
    "data_fim": null,
    "criado_em": "2026-07-01T10:00:00Z",
    "atualizado_em": "2026-07-01T10:00:00Z"
  }
]
```
> Só retorna vouchers `ativo`, dentro da vigência e com `quantidade_disponivel > 0`.

### 4.2. Resgatar voucher (usuário)
`POST /vouchers/{id}/resgatar` — requer login

Sem corpo. Response `201`:
```json
{
  "id": 5,
  "voucher_id": 1,
  "codigo": "RSDM-9F3A2B10",
  "pontos_utilizados": 50,
  "status": "ativo",
  "criado_em": "2026-07-09T14:10:00Z",
  "titulo": "10% de desconto",
  "parceiro": "Loja Verde"
}
```

**O `codigo` é o código promocional** que o front deve exibir/entregar ao usuário.

**Regras (erros `400`):**
- Saldo insuficiente: `"Pontuacao insuficiente para resgatar este voucher."`
- Esgotado/expirado/indisponível: mensagens correspondentes.
- O backend debita os pontos e decrementa `quantidade_disponivel` de forma segura (à prova de concorrência).

### 4.3. Meus resgates
`GET /vouchers/meus-resgates` — requer login — lista os vouchers resgatados **com seus códigos** (mesmo formato do item 4.2).

### 4.4. Cadastrar voucher (Admin)
`POST /vouchers` — **Admin**

Request:
```json
{
  "titulo": "Frete grátis",
  "descricao": "opcional",
  "parceiro": "Loja Verde",
  "custo_pontos": 80,
  "quantidade_disponivel": 100,
  "status": "ativo",
  "data_inicio": null,
  "data_fim": null
}
```
Response `201`: o voucher criado (formato do item 4.1).

---

## 5. Campanhas

### 5.1. Listar campanhas ativas
`GET /campanhas` — **Público**

Response `200`:
```json
[
  {
    "id": 1,
    "titulo": "Recicle e ganhe",
    "descricao": "Participe da campanha e acumule pontos",
    "patrocinador": "EmpresaX",
    "patrocinador_logo_url": "https://.../logo.png",
    "pontos_recompensa": 30,
    "status": "ativa",
    "data_inicio": null,
    "data_fim": null,
    "criado_em": "2026-07-01T10:00:00Z",
    "atualizado_em": "2026-07-01T10:00:00Z"
  }
]
```
> `patrocinador` e `patrocinador_logo_url` são para dar **evidência à marca** do patrocinador na tela e no dashboard.

### 5.2. Participar da campanha (usuário)
`POST /campanhas/{id}/participar` — requer login

Sem corpo. Response `201`:
```json
{
  "id": 3,
  "campanha_id": 1,
  "pontos_concedidos": 30,
  "criado_em": "2026-07-09T14:20:00Z",
  "titulo": "Recicle e ganhe",
  "patrocinador": "EmpresaX"
}
```

**Regras:**
- Ao participar, os `pontos_recompensa` são **acumulados** na carteira do usuário (a `pontuacao_total` sobe).
- **1 participação por usuário por campanha.** Se repetir: `400 "Você já participa desta campanha."`

### 5.3. Minhas inscrições
`GET /campanhas/minhas-inscricoes` — requer login — lista as campanhas em que o usuário se inscreveu (formato do item 5.2).

### 5.4. Cadastrar campanha (Admin)
`POST /campanhas` — **Admin**

Request:
```json
{
  "titulo": "Setembro Verde",
  "descricao": "opcional",
  "patrocinador": "EmpresaX",
  "patrocinador_logo_url": "https://.../logo.png",
  "pontos_recompensa": 30,
  "status": "ativa",
  "data_inicio": null,
  "data_fim": null
}
```
Response `201`: a campanha criada (formato do item 5.1).

---

## 6. Painel Admin — Aprovação de Pontos de Coleta

> Fluxo: o usuário cria a solicitação em `POST /solicitacoes-pontos-coleta` (já existente).
> O admin lista as pendentes, aprova ou rejeita.

### 6.1. Listar solicitações
`GET /admin/solicitacoes-pontos-coleta` — **Admin**

Query params:
- `status` (default `pendente`; use `todas` para listar todos os status). Valores: `pendente`, `aprovada`, `rejeitada`, `cancelada`, `todas`.
- `page` (default 1), `page_size` (default 20, máx 100).

Response `200`:
```json
{
  "total": 3,
  "page": 1,
  "page_size": 20,
  "itens": [
    {
      "id": 12,
      "usuario_id": 8,
      "tipo_solicitante": "cooperativa",
      "documento": "12.345.678/0001-90",
      "responsavel_nome": "Maria",
      "responsavel_telefone": "11999999999",
      "email": "maria@exemplo.com",
      "nome_ponto": "Ponto Central",
      "endereco": "Rua X, 100",
      "latitude": -23.55,
      "longitude": -46.63,
      "horario_funcionamento": "08:00-18:00",
      "tipos_residuos_aceitos": ["plastico", "papel"],
      "capacidade_maxima": 500.0,
      "status": "pendente",
      "motivo_rejeicao": null,
      "observacao_admin": null,
      "ponto_coleta_id": null,
      "revisado_por_id": null,
      "criado_em": "2026-07-08T10:00:00Z",
      "revisado_em": null
    }
  ]
}
```

`GET /admin/solicitacoes-pontos-coleta/{id}` — **Admin** — detalhe de uma solicitação (mesmo objeto de `itens`).

### 6.2. Aprovar
`POST /admin/solicitacoes-pontos-coleta/{id}/aprovar` — **Admin**

Request (corpo opcional):
```json
{ "observacao": "Aprovado após visita" }
```

Response `200`: a solicitação atualizada (`status = "aprovada"`, `ponto_coleta_id` preenchido).

**O que o backend faz ao aprovar:**
1. Cria o **ponto de coleta real** (tabela `ponto_coleta`) com `status = "ativo"`, vinculado à cooperativa solicitante.
2. Marca a solicitação como `aprovada` e guarda o `ponto_coleta_id`.
3. **Promove o usuário solicitante para `role = "cooperativa"`.**

> Só é possível aprovar solicitações com `status = "pendente"` (senão `400`).

### 6.3. Rejeitar
`POST /admin/solicitacoes-pontos-coleta/{id}/rejeitar` — **Admin**

Request (**motivo obrigatório**, mín. 3 caracteres):
```json
{ "motivo": "Documentação incompleta" }
```

Response `200`: a solicitação atualizada (`status = "rejeitada"`, `motivo_rejeicao` preenchido).

> Só é possível rejeitar solicitações `pendente` (senão `400`).

---

## 7. Observações finais

- **Extrato de pontos:** resgates de voucher e compras de bilhete de sorteio já aparecem no extrato existente (`GET /pontuacao/extrato`), com o débito de pontos. Pontos de campanha entram como crédito na `pontuacao_total`.
- **Datas:** todos os campos de data/hora são ISO 8601 em UTC.
- **Documentação viva:** o Swagger da API (`/docs`) reflete todos esses endpoints e schemas — use como fonte para os tipos exatos.

### Pendências do backend ainda em aberto (aguardando alinhamento)
- Aplicação das migrations no ambiente (as tabelas novas: `resgate_voucher`, `bilhete_sorteio`, `campanhas`, `inscricao_campanha`).
- Rota de **execução do sorteio** (escolher vencedor a partir das numerações) — hoje o sorteio é manual via dashboard; a numeração já está pronta.
