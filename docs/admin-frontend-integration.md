# Guia de Integração Front-end — Painel Admin

Guia prático para o time de front consumir os endpoints administrativos do backend Residuum.

---

## 1. Base URL e ambiente

| Ambiente | Base URL |
|---|---|
| Local (Docker) | `http://localhost:8080` |
| Swagger / OpenAPI | `http://localhost:8080/docs` |

Todos os caminhos deste guia são relativos à base URL. Ex.: `GET /admin/usuarios` → `http://localhost:8080/admin/usuarios`.

---

## 2. Autenticação

O painel admin usa **JWT Bearer**. Fluxo:

### 2.1. Login
```http
POST /login
Content-Type: application/json

{ "email": "admin@residuum.com", "senha": "..." }
```
Resposta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "usuario_id": 1
}
```

### 2.2. Enviar o token
Em **toda** chamada `/admin/*`, envie o header:
```http
Authorization: Bearer <access_token>
```

> O token expira em **60 minutos**. Ao receber **401**, redirecione para login (ou faça refresh via novo login).

### 2.3. Como saber se o usuário é admin
Depois do login, chame `GET /me` ou `GET /perfil` e verifique o campo `role`. Só mostre o painel admin quando `role === "admin"`. Endpoints `/admin/*` retornam **403** para não-admins.

### Exemplo de cliente (fetch)
```js
const api = (path, opts = {}) =>
  fetch(`${BASE_URL}${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...opts.headers,
    },
  }).then(async (res) => {
    if (res.status === 401) throw redirectToLogin();
    if (res.status === 403) throw new Error("Sem permissão de admin");
    if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
    return res.status === 204 ? null : res.json();
  });
```

---

## 3. Convenções

- **Erros**: corpo `{ "detail": "mensagem" }`. Mapeie `detail` para a UI.
- **Paginação**: endpoints de listagem aceitam `page` (≥1) e `page_size`, e retornam `{ total, page, page_size, itens: [...] }`.
- **Datas**: enviadas/recebidas em ISO 8601 (`2026-06-15T13:00:00`). Filtros `data_inicio`/`data_fim` aceitam ISO via querystring.
- **204**: sem corpo de resposta (delete/desativar).

---

## 4. Endpoints por área

### 4.1. Usuários

| Método | Path | Descrição |
|---|---|---|
| GET | `/admin/usuarios` | Lista paginada. Filtros: `role`, `email`, `nome`, `page`, `page_size`. |
| GET | `/admin/usuarios/{id}` | Detalhe + estatísticas (`total_descartes`, `kg_confirmados`). |
| PATCH | `/admin/usuarios/{id}` | Atualiza `nome`, `telefone`, `email`. |
| PATCH | `/admin/usuarios/{id}/role` | Body `{ "role": "usuario" \| "cooperativa" \| "admin" }`. |
| POST | `/admin/usuarios/{id}/ajuste-pontuacao` | Body `{ "delta": int, "motivo": "..." }`. Não permite saldo negativo. |
| DELETE | `/admin/usuarios/{id}` | Remove usuário (204). Não pode remover a si mesmo. |

> Regras: o admin não pode **rebaixar o próprio role** nem **remover a si mesmo** (retorna 400).

### 4.2. Descartes

| Método | Path | Descrição |
|---|---|---|
| GET | `/admin/descartes` | Lista paginada. Filtros: `status`, `usuario_id`, `ponto_coleta_id`, `tipo_residuo`, `data_inicio`, `data_fim`. |
| GET | `/admin/descartes/{id}` | Detalhe do descarte. |
| POST | `/admin/descartes/{id}/rejeitar` | Body `{ "motivo": "..." }`. Só para `pendente`. |
| POST | `/admin/descartes/{id}/reverter` | Body `{ "motivo": "..." }`. Só para `confirmado`. Estorna pontos e estoque. |

**Ciclo de vida do descarte (para a UI):**
```
pendente ──confirmar──▶ confirmado ──reverter──▶ revertido
   │
   └──rejeitar──▶ rejeitado
```
- Botões "Rejeitar" só fazem sentido quando `status === "pendente"`.
- Botão "Reverter" só quando `status === "confirmado"`.
- Ambos exigem **motivo** (mínimo 3 caracteres) — valide no form antes de enviar.

**Exemplo — rejeitar:**
```js
await api(`/admin/descartes/${id}/rejeitar`, {
  method: "POST",
  body: JSON.stringify({ motivo: "Foto não confere com a quantidade" }),
});
```

### 4.3. Pontos de Coleta

| Método | Path | Descrição |
|---|---|---|
| POST | `/pontos-coleta` | Criar ponto (admin). |
| PUT | `/pontos-coleta/{id}` | Atualizar / reativar (`ativo=1` ou `status="ativo"`). |
| DELETE | `/admin/pontos-coleta/{id}` | **Desativar** (soft-delete, 204). |
| GET | `/pontos-coleta?incluir_inativos=true` | Listar incluindo inativos (só admin enxerga inativos). |

> Desativar **não apaga** o ponto: ele fica `ativo=0`/`status="inativo"`. Para listar os desativados no painel, use `incluir_inativos=true`.

### 4.4. Estoque

| Método | Path | Descrição |
|---|---|---|
| GET | `/admin/estoque` | Total por tipo de resíduo (todos os pontos). |
| GET | `/admin/estoque/por-ponto` | Estoque por ponto + `percentual_ocupacao`. |

### 4.5. Métricas / Dashboard

| Método | Path | Descrição |
|---|---|---|
| GET | `/admin/metrics/resumo` | Cards do dashboard (usuários, pontos, descartes, kg, pontos distribuídos). |
| GET | `/admin/metrics/por-tipo-residuo` | Kg confirmados por tipo (gráfico de pizza/barras). |
| GET | `/admin/metrics/ranking-usuarios?limit=10` | Top N por pontuação. |
| GET | `/admin/metrics/descartes-por-periodo?dias=30` | Série temporal diária (gráfico de linha). |
| GET | `/admin/metrics/ocupacao-pontos?alerta_pct=90` | Ocupação por ponto, com flag `alerta`. |

### 4.6. Relatórios (CSV)

| Método | Path | Filtros |
|---|---|---|
| GET | `/admin/relatorios/descartes.csv` | `status`, `usuario_id`, `ponto_coleta_id`, `tipo_residuo`, `data_inicio`, `data_fim` |
| GET | `/admin/relatorios/usuarios.csv` | — |
| GET | `/admin/relatorios/auditoria.csv` | `data_inicio`, `data_fim` |

**Como baixar no front** (precisa enviar o header de auth, então não use `<a href>` puro):
```js
async function baixarCSV(path, filename) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

baixarCSV("/admin/relatorios/descartes.csv?status=confirmado", "descartes.csv");
```

### 4.7. Auditoria

| Método | Path | Descrição |
|---|---|---|
| GET | `/admin/auditoria` | Log de ações admin. Filtros: `admin_id`, `action`, `target_type`, `target_id`, `data_inicio`, `data_fim`, `page`, `page_size`. |

Cada item traz `admin_nome`, `action`, `target_type`, `target_id`, `motivo`, `payload` (diff antes/depois) e `created_at` — útil para uma tela de histórico/timeline.

---

## 5. Códigos de status (resumo)

| Código | Significado | Ação na UI |
|---|---|---|
| 200 | OK | — |
| 204 | Sucesso sem corpo (delete/desativar) | Atualizar lista localmente |
| 400 | Regra de negócio violada (ex.: estado inválido, saldo negativo) | Mostrar `detail` ao usuário |
| 401 | Token ausente/expirado | Redirecionar para login |
| 403 | Não é admin | Esconder/bloquear painel |
| 404 | Recurso não encontrado | Mensagem "não encontrado" |
| 422 | Validação de payload (Pydantic) | Mostrar erros de campo |

---

## 6. Checklist de integração

- [ ] Guardar `access_token` após login e injetar em todas as chamadas `/admin/*`.
- [ ] Esconder o painel admin quando `role !== "admin"`.
- [ ] Tratar 401 (logout/refresh) e 403 globalmente no client HTTP.
- [ ] Confirmar motivo (mín. 3 chars) nos fluxos de rejeitar/reverter.
- [ ] Usar paginação (`page`/`page_size`) nas listagens.
- [ ] Download de CSV via `fetch` + `Blob` (com header Authorization).
- [ ] Refletir o ciclo de vida do descarte nos botões de ação.
