# Mudanças nesta branch — `feature/logica-descarte-herick`

Documento resumindo as alterações de arquitetura, segurança e infraestrutura aplicadas. Para cada item: **o que mudou**, **por que** e **como o time deve usar**.

---

## 1. Decorator `@public` para rotas sem autenticação

### O que mudou

- Criado `app/core/decorators.py` com o decorator `@public`, que apenas marca o endpoint com o atributo `_is_public = True`.
- Em `app/core/security.py`, criada a dependência global `require_auth_unless_public`, registrada em `main.py` via `dependencies=[Depends(require_auth_unless_public)]`.
- Toda rota da API agora **exige JWT por padrão**. Para liberar uma rota, basta decorá-la com `@public`.

### Por quê

O modelo anterior obrigava cada rota a importar `get_current_user` explicitamente, e era fácil esquecer de proteger uma rota nova. Invertemos: protegido por padrão, liberar é uma ação consciente.

### Como usar

```python
from app.core.decorators import public

@router.post("/login")
@public
def login(...): ...
```

Rotas atualmente públicas: `GET /`, `POST /usuarios`, `POST /login`. Todas as outras exigem `Authorization: Bearer <token>`.

---

## 2. Sistema de roles no usuário

### O que mudou

- Adicionada a coluna `role` em `app/models/usuario.py` (`String`, `NOT NULL`, default `"usuario"`, com `server_default` para cobrir registros antigos).
- Criada a fábrica de dependência `require_role(*roles)` em `app/dependencies/auth.py`, que retorna `403` se o usuário autenticado não tiver um dos perfis informados.
- Aplicada em `GET /descarte/historico/geral`, que agora exige `role="admin"`.

### Por quê

Antes a autorização era binária (autenticado vs. público). Agora dá pra restringir áreas administrativas (relatórios, gestão) sem precisar criar middleware novo.

### Como usar

```python
from app.dependencies.auth import require_role

@router.get("/admin/relatorios")
def relatorio(usuario = Depends(require_role("admin"))):
    ...
```

---

## 3. `GET /me` agora retorna `role`, `telefone` e `endereco`

### O que mudou

A resposta do `GET /me` foi expandida para incluir:

- `role` — para o frontend decidir o que renderizar (áreas admin, etc).
- `telefone` — campo já existente no modelo, antes não exposto.
- `endereco` — objeto completo (ou `null` se ainda não cadastrado).

### Por quê

O frontend precisa do `role` para mostrar/esconder funcionalidades, e do `endereco` para saber se o usuário precisa completar o cadastro antes de outras ações.

### Resposta atual

```json
{
  "id": 1,
  "nome": "Marcus",
  "email": "marcus@email.com",
  "telefone": "11999999999",
  "pontuacao_total": 0,
  "role": "usuario",
  "endereco": null
}
```

---

## 4. Separação: criação de usuário ≠ cadastro de endereço

### O que mudou

- `POST /usuarios` agora aceita **apenas** `nome`, `email`, `telefone`, `senha`. Sem endereço.
- Removido o `EnderecoCreate` duplicado de `app/schemas/usuario.py`.
- Criado `app/routes/endereco.py` com `PUT /me/endereco` (upsert: cria se não existe, atualiza se já existe).

### Por quê

Pedir endereço completo no cadastro inicial é ruim de UX (alta taxa de abandono) e mistura fluxos de jornada diferentes. Login social (Google, Apple) também não traz endereço — separar deixa a API pronta para esses cenários.

### Fluxo agora

1. **Tela de cadastro:**
   ```http
   POST /usuarios
   { "nome": "...", "email": "...", "telefone": "...", "senha": "..." }
   ```
2. **Login → recebe token.**
3. **Completar perfil (depois):**
   ```http
   PUT /me/endereco
   Authorization: Bearer <token>
   { "rua": "...", "bairro": "...", "numero": 100, "cep": "...", "cidade": "..." }
   ```
   O `id` do usuário sai do token. Mesma rota cobre criação e atualização.

---

## 5. Regra de segurança: id do usuário **sempre** vem do token

### O que mudou

- Documentação e revisão dos endpoints para garantir que id do usuário autenticado é obtido via `Depends(get_current_user)`, nunca de path/body/query.
- `PUT /me/endereco` segue essa regra estritamente.

### Por quê

Se o backend confia em `usuario_id` enviado pelo cliente, qualquer um trocando o número acessa/edita dados de outras pessoas (**IDOR** — Insecure Direct Object Reference, top 1 do OWASP API Security 2023). O `sub` do JWT é assinado pela `SECRET_KEY` do servidor — ninguém forja sem a chave.

### Regra prática para o time

| Caso                                           | Onde pegar o id                                            |
| ---------------------------------------------- | ---------------------------------------------------------- |
| "meus dados" / "meu perfil" / "meus descartes" | **Token**                                                  |
| Criar recurso que pertence ao usuário          | **Token** — nunca aceitar `usuario_id` no body             |
| Admin vendo dados de outro usuário             | URL (`/admin/usuarios/{id}`) **+** `require_role("admin")` |
| Apontar **outro recurso** (não o agente)       | URL é OK (ex.: `PUT /descarte/{id_descarte}/confirmar`)    |

---

## 6. Alembic — migrations versionadas

### O que mudou

- Alembic configurado na raiz do projeto: `alembic.ini` + pasta `alembic/`.
- `alembic/env.py` ajustado para:
  - carregar `DATABASE_URL` do `.env` automaticamente
  - importar `Base` + todos os modelos para autogenerate funcionar
  - sobrescrever a `sqlalchemy.url` (que ficou em branco no `.ini`)
- Primeira migration aplicada: `alembic/versions/cbd3c03713de_initial_schema.py` (cria `usuario`, `endereco`, `descarte` com índices e o campo `role`).
- **Removido o `Base.metadata.create_all(bind=engine)` do `main.py`** — schema é 100% controlado por Alembic agora.

### Por quê

`create_all` só **cria** tabelas que não existem; não detecta colunas novas, mudança de tipo, deleção. Em produção isso é receita pra divergência silenciosa entre código e banco. Alembic gera scripts versionados e auditáveis.

### Fluxo para o time

**Após dar `git pull` (sempre que houver migration nova):**

```bash
alembic upgrade head
```

Aplica todas as migrations pendentes em ordem. Se já estiver atualizado, não faz nada.

**Após mudar um modelo SQLAlchemy:**

```bash
alembic revision --autogenerate -m "descrição curta"
# REVISE o arquivo gerado em alembic/versions/ antes de aplicar
alembic upgrade head
```

**Comandos úteis:**
| Comando | Descrição |
|---|---|
| `alembic current` | Revision atual no banco |
| `alembic history` | Lista todas as migrations |
| `alembic downgrade -1` | Reverte a última |
| `alembic stamp head` | Marca como atualizado sem rodar (uso pontual) |

### Regras do time

1. PR que mexe em modelo **precisa** trazer a migration na mesma PR.
2. Code review do arquivo de migration é obrigatório (autogenerate erra em renomeações — interpreta como drop+add e perde dados).
3. PR com migration deve avisar no título/descrição: outros devs precisam rodar `alembic upgrade head` após pull.

---

## 7. Postgres via Docker Compose

### O que mudou

- Adicionado `docker-compose.yml` na raiz com o serviço `postgres` (imagem `postgres:16-alpine`).
- Credenciais e nome do banco vêm do `.env` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`).
- Container nomeado `residuum-postgres`. Healthcheck a cada 5s via `pg_isready`.
- Dados persistidos no volume Docker `postgres_data`.

### Por quê

Antes cada dev precisava ter Postgres instalado nativo no SO (versões diferentes, configurações diferentes). Com Compose, qualquer pessoa que clona o repo sobe o banco com **um comando** e todos rodam exatamente a mesma versão (`postgres:16-alpine`).

### Como usar

**Subir:**

```bash
docker compose up -d
docker compose ps        # confirmar status "healthy"
```

**Parar (mantém dados):**

```bash
docker compose down
```

**Resetar tudo (apaga dados — destrutivo):**

```bash
docker compose down -v
```

> ⚠️ **Pegadinha**: Postgres só lê `POSTGRES_USER`/`POSTGRES_PASSWORD` na **primeira** inicialização do volume. Se você mudar essas envs depois, o container ignora as novas a menos que você apague o volume (`down -v`). Por isso `docker compose down -v` é necessário ao mudar credenciais.

---

## 8. Padronização de nome: Residium → Residuum

### O que mudou

Nome correto do projeto é **Residuum** (não Residium nem Residum). Padronizado em:

- `.env` e `.env.example` (user, password, db, container)
- `docker-compose.yml` (`container_name: residuum-postgres`, defaults das envs)
- `app/main.py` (title, mensagem root)
- `app/services/pontuacao_service.py` (comentário)
- `README.md` (todas as ocorrências)
- Renomeado: `residum.sql` → `residuum.sql`

### Por quê

Consistência. Nome errado em config gera bugs como "role does not exist" e prejudica leitura/onboarding.

---

## 9. Outras mudanças menores

### `bcrypt` travado em `4.0.1`

Versão `5.x` tem incompatibilidade com `passlib==1.7.4` (passlib não recebe release há anos). Pinado em `requirements.txt`.

### `requirements.txt` criado

Antes não existia. Agora todas as deps (com versões) estão travadas: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `psycopg2-binary`, `alembic`, `pydantic`, `email_validator`, `python-jose[cryptography]`, `passlib`, `bcrypt`, `python-dotenv`.

### `.gitignore` reforçado

Adicionado `.claude/`. Removido tracking de arquivos `__pycache__/*.pyc` que tinham vazado para o repositório anteriormente.

### Tags do Swagger sem duplicação

Antes os endpoints de auth apareciam em duas seções (`Auth` + `Autenticação`) porque a tag estava definida tanto no `APIRouter` quanto no `include_router`. Padronizado: tag fica **só** no `include_router` (em `main.py`).

### `GET /descarte/historico/geral`

Novo endpoint que lista todos os descartes (não só do usuário logado), ordenado por `data_desc` decrescente. Restrito a `role="admin"`.

---

## Checklist para subir o ambiente do zero

```bash
# 1. Clonar e entrar no projeto
git clone <repo>
cd backend-residuum

# 2. Criar e ativar venv
python -m venv .venv
source .venv/Scripts/activate    # Git Bash
# .\.venv\Scripts\Activate.ps1   # PowerShell

# 3. Instalar deps
pip install -r requirements.txt

# 4. Criar .env (copiar do .env.example)
cp .env.example .env

# 5. Subir o Postgres
docker compose up -d

# 6. Aplicar migrations
alembic upgrade head

# 7. Subir a API
uvicorn app.main:app --reload
```

API em `http://127.0.0.1:8000`. Swagger em `/docs`.
