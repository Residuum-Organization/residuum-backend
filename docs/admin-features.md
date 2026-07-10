# Painel Administrativo — Novas Features

Documentação das funcionalidades administrativas/gestão adicionadas ao backend Residuum.

Todos os endpoints abaixo:

- Têm prefixo **`/admin`**.
- Exigem **JWT válido** + usuário com **`role = admin`** (dependência global `require_role("admin")`).
- Sem permissão → **403 `Permissão insuficiente`**. Sem token → **401**.
- Ações que alteram estado gravam uma entrada no **audit log** (`audit_log`), consultável em `GET /admin/auditoria`.

> Nenhuma das features novas exige migração de banco. A única tabela necessária
> (`audit_log`) é criada pela migração `admin_audit_log` (`alembic upgrade head`).

---

## 1. Gestão de Descartes

### `GET /admin/descartes/{id_descarte}`
Retorna o detalhe de um descarte específico (serializado com nome do usuário e do ponto de coleta).

- **404** se o descarte não existir.

### `POST /admin/descartes/{id_descarte}/rejeitar`
Rejeita um descarte que está **pendente**.

- Body: `{ "motivo": "texto (3–255 chars)" }`
- Efeitos:
  - `status` → `"rejeitado"`.
  - Se o descarte veio do inventário do usuário, **libera a quantidade reservada** no item (`InventarioUsuario`).
  - Registra ação `descarte.rejeitar` na auditoria.
- **400** se o descarte não estiver com status `pendente`.

### `POST /admin/descartes/{id_descarte}/reverter`
Reverte um descarte já **confirmado** (correção de confirmação indevida).

- Body: `{ "motivo": "texto (3–255 chars)" }`
- Efeitos:
  - **Estorna a pontuação** concedida (10 pontos por kg confirmado). O saldo do usuário nunca fica negativo, e uma entrada negativa é gravada no histórico `Pontuacao`.
  - **Debita** a quantidade confirmada do inventário do ponto de coleta (`PontoColeta.inventario`), sem deixar estoque negativo.
  - `status` → `"revertido"` e `quantidade_confirmada` → `null`.
  - Registra ação `descarte.reverter` na auditoria.
- **400** se o descarte não estiver com status `confirmado`.

**Estados de um descarte:** `pendente` → `confirmado` | `rejeitado`; `confirmado` → `revertido`.

---

## 2. Gestão de Pontos de Coleta

### `DELETE /admin/pontos-coleta/{ponto_id}`
**Soft-delete** de um ponto de coleta (não apaga o registro).

- Efeitos: `ativo` → `0`, `status` → `"inativo"`. O ponto deixa de aparecer nas listagens comuns de usuário.
- Registra ação `ponto_coleta.desativar` na auditoria.
- Retorna **204 No Content**.
- **404** se o ponto não existir.

> Para **criar/atualizar/reativar** pontos, continue usando os endpoints existentes
> `POST /pontos-coleta`, `PUT /pontos-coleta/{id}` (reativar = `PUT` com `ativo=1` ou `status="ativo"`).

---

## 3. Estoque (consolidado)

O estoque "real" é mantido no inventário de cada ponto de coleta (`PontoColeta.inventario`),
populado quando um descarte é confirmado. Estes endpoints agregam essa informação.

### `GET /admin/estoque`
Estoque total por tipo de resíduo, somando todos os pontos de coleta.

```json
{
  "total_geral": 1240.5,
  "itens": [
    { "tipo_residuo": "plastico", "quantidade_total": 800.0 },
    { "tipo_residuo": "vidro", "quantidade_total": 440.5 }
  ]
}
```

### `GET /admin/estoque/por-ponto`
Estoque detalhado por ponto, com percentual de ocupação.

```json
[
  {
    "ponto_coleta_id": 1,
    "nome": "Ecoponto Centro",
    "capacidade_maxima": 1000.0,
    "total_inventario": 820.0,
    "percentual_ocupacao": 82.0,
    "inventario": { "plastico": 600.0, "vidro": 220.0 },
    "ativo": 1
  }
]
```

> `percentual_ocupacao` é `null` quando o ponto não tem `capacidade_maxima` definida.

---

## 4. Métricas e Relatórios

### `GET /admin/metrics/ocupacao-pontos`
Ocupação dos pontos, ordenada do mais cheio ao mais vazio, com flag de alerta.

- Query param opcional: `alerta_pct` (default `90`, faixa 0–100).
- Cada item traz `alerta: true` quando `percentual_ocupacao >= alerta_pct`.

```json
[
  {
    "ponto_coleta_id": 1,
    "nome": "Ecoponto Centro",
    "capacidade_maxima": 1000.0,
    "total_inventario": 950.0,
    "percentual_ocupacao": 95.0,
    "alerta": true
  }
]
```

### Exports CSV

Retornam `text/csv` com `Content-Disposition: attachment` (download direto).

| Endpoint | Conteúdo | Colunas |
|---|---|---|
| `GET /admin/relatorios/descartes.csv` | Descartes (aceita filtros) | id_descarte, data_desc, status, tipo_residuo, quantidade, quantidade_confirmada, usuario_id, ponto_coleta_id |
| `GET /admin/relatorios/usuarios.csv` | Usuários | id, nome, email, telefone, role, pontuacao_total |
| `GET /admin/relatorios/auditoria.csv` | Audit log (aceita período) | id, created_at, admin_id, action, target_type, target_id, motivo |

**Filtros de `descartes.csv`** (todos opcionais, querystring): `status`, `usuario_id`, `ponto_coleta_id`, `tipo_residuo`, `data_inicio`, `data_fim`.

**Filtros de `auditoria.csv`**: `data_inicio`, `data_fim`.

---

## Auditoria

Toda ação administrativa que altera estado é registrada em `audit_log` com:
`admin_id`, `action`, `target_type`, `target_id`, `motivo` (quando aplicável) e `payload` (antes/depois).

Ações geradas pelas features acima:

| Action | Disparada por |
|---|---|
| `descarte.rejeitar` | rejeitar descarte |
| `descarte.reverter` | reverter descarte |
| `ponto_coleta.desativar` | desativar ponto de coleta |

Consulta: `GET /admin/auditoria` (filtros: `admin_id`, `action`, `target_type`, `target_id`, `data_inicio`, `data_fim`, paginação).

---

## Arquivos relacionados (referência para devs)

- `app/routes/admin.py` — endpoints.
- `app/schemas/admin.py` — `RejeitarDescarteRequest`, `ReverterDescarteRequest`.
- `app/services/transferencia_service.py` — `debitar_residuo_do_ponto_coleta()` (estorno de estoque).
- `app/services/audit_service.py` — `registrar_acao()`.
- `app/services/serializacao_service.py` — serialização de descartes/usuários.
