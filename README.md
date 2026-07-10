# Residuum — Backend FastAPI

## Visão Geral

Este repositório contém o **backend da plataforma Residuum**, uma API desenvolvida com **FastAPI**, **SQLAlchemy**, **Alembic** e **PostgreSQL** para gerenciar o fluxo de cadastro, autenticação, inventário de resíduos do usuário, pontos de coleta, descarte, confirmação pela cooperativa/admin, pontuação e histórico.

A lógica central do sistema segue as regras de negócio do projeto:

- o usuário cadastra resíduos em seu inventário pessoal;
- o usuário solicita o descarte de parte ou totalidade desses resíduos em um ponto de coleta;
- a presença do usuário é validada por GPS ou QR Code;
- o descarte fica com status `pendente` até confirmação do administrador/cooperativa;
- a pontuação e a baixa do inventário do usuário só acontecem após a confirmação da quantidade real descartada;
- o inventário do ponto de coleta é atualizado apenas com a quantidade confirmada.

---

## Tecnologias

| Tecnologia | Uso no projeto |
|---|---|
| Python 3.10+ | Linguagem principal |
| FastAPI | Framework da API |
| Uvicorn | Servidor ASGI |
| SQLAlchemy | ORM e comunicação com o banco |
| Alembic | Versionamento de migrations |
| PostgreSQL | Banco de dados relacional |
| Pydantic | Validação de schemas |
| python-dotenv | Leitura das variáveis do `.env` |
| passlib/bcrypt | Hash de senhas |
| python-jose | Geração e validação de JWT |
| Docker Compose | Banco PostgreSQL local para desenvolvimento |

---

## Módulos Implementados

### 1. Cadastro e autenticação

Endpoints principais:

```txt
POST /usuarios
POST /login
GET  /me
GET  /perfil
PUT  /me/endereco
```

Funcionalidades:

- cadastro de usuário com nome, e-mail, telefone e senha;
- senha armazenada como hash;
- login com e-mail e senha;
- autenticação via token JWT;
- controle de perfil por `role`, com suporte a `usuario` e `admin`;
- endpoint `/perfil` consolidado com dados pessoais, pontuação, inventário, histórico resumido e descartes pendentes.

---

### 2. Inventário de resíduos do usuário — Task 11

Foi implementado o inventário pessoal do usuário, permitindo armazenar temporariamente resíduos antes da transferência para um ponto de coleta.

Endpoints:

```txt
POST   /me/inventario
GET    /me/inventario
GET    /me/inventario/{item_id}
PUT    /me/inventario/{item_id}
DELETE /me/inventario/{item_id}
POST   /me/inventario/{item_id}/descartar
```

Fluxo:

1. O usuário cadastra um resíduo em seu inventário.
2. O item permanece disponível para descarte.
3. O usuário solicita descarte parcial ou total em um ponto de coleta.
4. O descarte é criado com status `pendente`.
5. O item **não é baixado imediatamente** do inventário.
6. Após confirmação do admin/cooperativa, a quantidade confirmada é subtraída do inventário do usuário.
7. A mesma quantidade confirmada é adicionada ao inventário do ponto de coleta.
8. A pontuação do usuário é atualizada.

Essa regra evita que o usuário perca quantidade do inventário antes da confirmação real da entrega.

---

### 3. Pontos de coleta — Tasks 8 e 9

O módulo de pontos de coleta foi expandido para atender às tasks de detalhes do ponto e listagem filtrável.

Endpoints principais:

```txt
POST /pontos-coleta
GET  /pontos-coleta
GET  /pontos-coleta/{ponto_id}
PUT  /pontos-coleta/{ponto_id}
GET  /pontos
```

O endpoint `GET /pontos` funciona como alias para listagem de pontos, alinhado com a task do Word.

Campos adicionados ao ponto de coleta:

```txt
capacidade_maxima
tipos_residuos_aceitos
horario_funcionamento
status
```

Campos calculados no retorno:

```txt
total_inventario
percentual_ocupacao
status_calculado
```

Filtros disponíveis:

```txt
tipo_residuo
lat
long
distancia_km
incluir_inativos
```

Exemplo:

```txt
GET /pontos?tipo_residuo=plastico&lat=-3.1316&long=-60.0234&distancia_km=2
```

Regra de pontos inativos:

- usuário comum visualiza apenas pontos ativos/disponíveis;
- admin pode visualizar pontos ativos, cheios e inativos usando `incluir_inativos=true`;
- o parâmetro `incluir_inativos=true` só é respeitado para usuários com `role = admin`.

---

### 4. Descarte e confirmação

Endpoints:

```txt
POST /descarte/
GET  /descarte/historico
GET  /descarte/historico/geral
GET  /descarte/pendentes
PUT  /descarte/{id_descarte}/confirmar
```

Funcionalidades:

- criação de descarte com status `pendente`;
- validação de quantidade;
- validação do tipo de resíduo;
- validação de presença por GPS;
- validação alternativa por QR Code;
- vínculo com ponto de coleta;
- vínculo opcional com item do inventário do usuário;
- confirmação por admin/cooperativa;
- cálculo de pontuação proporcional à quantidade real confirmada;
- atualização do inventário do ponto;
- baixa do inventário do usuário apenas após confirmação.

Regra de pontuação:

```txt
10 pontos por 1 kg confirmado
```

Exemplo:

```txt
2.5 kg confirmados = 25 pontos
```

---

### 5. Histórico com nomes reais

Os endpoints de histórico e pendentes foram melhorados para retornar nomes reais, evitando que o frontend precise exibir apenas IDs.

Endpoints afetados:

```txt
GET /descarte/historico
GET /descarte/historico/geral
GET /descarte/pendentes
```

Campos adicionados no retorno:

```txt
usuario_nome
usuario_email
ponto_coleta_nome
ponto_coleta_endereco
```

Exemplo de retorno:

```json
{
  "id_descarte": 1,
  "usuario_id": 1,
  "usuario_nome": "Vitor Vieira Barbosa",
  "usuario_email": "vitor@email.com",
  "ponto_coleta_id": 2,
  "ponto_coleta_nome": "Ponto de Coleta Centro",
  "ponto_coleta_endereco": "Av. Eduardo Ribeiro, Centro",
  "tipo_residuo": "plastico",
  "quantidade": 2.0,
  "quantidade_confirmada": 2.0,
  "status": "confirmado"
}
```

---

### 6. QR Code

Endpoints:

```txt
POST /qrcode-tokens
GET  /qrcode-tokens/{ponto_id}
POST /qrcode-tokens/validar
```

Funcionalidades:

- geração de token QR Code para ponto de coleta;
- listagem de tokens ativos por ponto;
- validação de token para confirmar presença;
- uso do QR Code como alternativa ou complemento à validação por GPS.

---

## Banco de Dados

O banco é versionado por Alembic. As principais tabelas do sistema são:

```txt
usuario
endereco
descarte
ponto_coleta
qrcode_token
inventario_usuario
pontuacao
estoque
alembic_version
```

### Alterações relevantes no banco

#### Tabela `inventario_usuario`

Criada para armazenar o inventário pessoal do usuário.

Campos principais:

```txt
id
usuario_id
tipo_residuo
quantidade
descricao
observacao
status
data_cadastro
data_atualizacao
```

Uso:

- registra resíduos que o usuário possui;
- permite descarte parcial;
- mantém os itens até confirmação real da entrega;
- baixa a quantidade apenas depois da confirmação do admin/cooperativa.

#### Tabela `descarte`

Foi ajustada para permitir vínculo com:

```txt
ponto_coleta_id
qrcode_token_id
inventario_usuario_id
```

Uso:

- descarte pode vir diretamente do inventário do usuário;
- descarte fica pendente até confirmação;
- quantidade confirmada é registrada separadamente.

#### Tabela `ponto_coleta`

Foram adicionados dados operacionais:

```txt
capacidade_maxima
tipos_residuos_aceitos
horario_funcionamento
status
```

Uso:

- exibição detalhada do ponto;
- filtro por tipo aceito;
- cálculo de ocupação;
- controle de pontos ativos, cheios e inativos.

---

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do backend.

Exemplo com PostgreSQL local via Docker:

```env
DATABASE_URL=postgresql://residuum:residuum@localhost:5432/residuum
SECRET_KEY=troque-esta-chave-em-producao
```

Exemplo genérico:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/residuum
SECRET_KEY=sua_chave_secreta_aqui
```

> Não versionar `.env` no Git.

---

## Executando com Docker para o banco

Se o projeto tiver `docker-compose.yml`, suba o PostgreSQL:

```bash
docker compose up -d postgres
```

Verifique se o container está rodando:

```bash
docker ps
```

Para acessar o banco pelo terminal:

```bash
docker exec -it residuum-postgres psql -U residuum -d residuum
```

---

## Instalação do Backend

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd backend
```

### 2. Criar ambiente virtual

```bash
python -m venv venv
```

Ativar no Windows:

```bash
venv\Scripts\activate
```

Ativar no Linux/macOS:

```bash
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Aplicar migrations

```bash
python -m alembic upgrade head
```

### 5. Rodar a API

```bash
python -m uvicorn app.main:app --reload
```

Acesse:

```txt
http://127.0.0.1:8000/docs
```

---

## Comandos úteis do Alembic

| Comando | Descrição |
|---|---|
| `python -m alembic current` | Mostra a migration atual aplicada no banco |
| `python -m alembic history` | Lista o histórico de migrations |
| `python -m alembic upgrade head` | Aplica todas as migrations pendentes |
| `python -m alembic downgrade -1` | Reverte a última migration |
| `python -m alembic revision --autogenerate -m "mensagem"` | Gera migration automática |

> Observação: o campo `version_num` da tabela `alembic_version` aceita até 32 caracteres. Evite IDs de migration muito longos.

---

## Fluxo de Teste Principal

### 1. Criar usuário

```http
POST /usuarios
```

```json
{
  "nome": "Usuario Teste",
  "email": "usuario.teste@residuum.com",
  "telefone": "92999990000",
  "senha": "123456"
}
```

### 2. Fazer login

```http
POST /login
```

```json
{
  "email": "usuario.teste@residuum.com",
  "senha": "123456"
}
```

Copie o `access_token` e autorize no Swagger usando:

```txt
Bearer SEU_TOKEN_AQUI
```

### 3. Criar item no inventário do usuário

```http
POST /me/inventario
```

```json
{
  "tipo_residuo": "plastico",
  "quantidade": 6,
  "descricao": "Garrafas PET acumuladas em casa"
}
```

### 4. Criar ponto de coleta como admin

```http
POST /pontos-coleta
```

```json
{
  "nome": "Ponto Residuum Centro",
  "endereco": "Av. Eduardo Ribeiro, Centro, Manaus - AM",
  "latitude": -3.131633,
  "longitude": -60.023437,
  "raio_operacao": 1000,
  "capacidade_maxima": 500,
  "tipos_residuos_aceitos": ["plastico", "papel", "aluminio"],
  "horario_funcionamento": "Segunda a sábado, 08h às 18h",
  "status": "ativo"
}
```

### 5. Solicitar descarte a partir do inventário

```http
POST /me/inventario/{item_id}/descartar
```

```json
{
  "quantidade": 2,
  "observacao": "Descarte parcial do inventário",
  "usuario_lat": -3.131633,
  "usuario_long": -60.023437,
  "ponto_coleta_id": 1,
  "qrcode_token": null
}
```

Resultado esperado:

```txt
Descarte criado com status pendente.
Inventário do usuário ainda não diminui.
```

### 6. Confirmar descarte como admin

```http
PUT /descarte/{id_descarte}/confirmar
```

```json
{
  "quantidade_confirmada": 1.5
}
```

Resultado esperado:

```txt
Inventário do usuário diminui 1.5 kg.
Inventário do ponto aumenta 1.5 kg.
Usuário recebe 15 pontos.
Descarte muda para confirmado.
```

---

## Estrutura do Projeto

```txt
backend/
├── alembic/
│   ├── versions/
│   │   ├── task11_inventario_usuario.py
│   │   └── task8_task9_pontos.py
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── core/
│   │   ├── decorators.py
│   │   └── security.py
│   ├── dependencies/
│   │   └── auth.py
│   ├── models/
│   │   ├── descarte.py
│   │   ├── endereco.py
│   │   ├── inventario_usuario.py
│   │   ├── ponto_coleta.py
│   │   ├── pontuacao.py
│   │   ├── qrcode_token.py
│   │   └── usuario.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── descarte.py
│   │   ├── endereco.py
│   │   ├── inventario_usuario.py
│   │   ├── ponto_coleta.py
│   │   └── qrcode_token.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── descarte.py
│   │   ├── endereco.py
│   │   ├── inventario_usuario.py
│   │   ├── ponto_coleta.py
│   │   ├── pontuacao.py
│   │   └── usuario.py
│   ├── services/
│   │   ├── localizacao_service.py
│   │   ├── pontuacao_service.py
│   │   ├── serializacao_service.py
│   │   ├── transferencia_service.py
│   │   └── validacao_service.py
│   ├── database.py
│   └── main.py
├── alembic.ini
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Principais Endpoints

### Autenticação e perfil

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/usuarios` | Cria usuário |
| POST | `/login` | Realiza login |
| GET | `/me` | Retorna usuário autenticado |
| GET | `/perfil` | Retorna perfil completo |
| PUT | `/me/endereco` | Cria ou atualiza endereço |

### Inventário do usuário

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/me/inventario` | Cadastra item no inventário |
| GET | `/me/inventario` | Lista inventário do usuário |
| GET | `/me/inventario/{item_id}` | Detalha item |
| PUT | `/me/inventario/{item_id}` | Atualiza item |
| DELETE | `/me/inventario/{item_id}` | Remove/cancela item |
| POST | `/me/inventario/{item_id}/descartar` | Solicita descarte do item |

### Pontos de coleta

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/pontos` | Lista pontos com filtros |
| GET | `/pontos-coleta` | Lista pontos de coleta |
| POST | `/pontos-coleta` | Cria ponto de coleta |
| GET | `/pontos-coleta/{ponto_id}` | Detalha ponto |
| PUT | `/pontos-coleta/{ponto_id}` | Atualiza ponto |

### Descartes

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/descarte/` | Registra descarte manual/rápido |
| GET | `/descarte/historico` | Histórico do usuário |
| GET | `/descarte/historico/geral` | Histórico geral admin |
| GET | `/descarte/pendentes` | Lista descartes pendentes |
| PUT | `/descarte/{id_descarte}/confirmar` | Confirma descarte |

### QR Code

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/qrcode-tokens` | Gera token QR Code |
| GET | `/qrcode-tokens/{ponto_id}` | Lista tokens ativos do ponto |
| POST | `/qrcode-tokens/validar` | Valida QR Code |

---

## Regras de Negócio Importantes

- A pontuação não é creditada no momento da solicitação de descarte.
- A pontuação só é creditada após confirmação da quantidade real pelo admin/cooperativa.
- O inventário do usuário só é reduzido após confirmação.
- O inventário do ponto só é atualizado após confirmação.
- Usuário comum não vê pontos inativos.
- Admin vê pontos ativos, cheios e inativos.
- A validação de presença pode ocorrer por GPS ou QR Code.
- O sistema aceita múltiplos tipos de resíduos conforme configuração do backend.

---

## Branch de Desenvolvimento

As alterações recentes do backend contemplam:

- Task 7 — Perfil RF006;
- Task 8 — Detalhes do Ponto RF008;
- Task 9 — GET `/pontos` com filtros;
- Task 11 — Inventário de Resíduos do Usuário;
- histórico com nomes reais de usuário e ponto;
- visualização de pontos inativos para admin;
- melhorias na regra de transferência e confirmação.

Sugestão de nome de branch:

```txt
feature/backend-tasks-5-11
```

---

## Observações para o Git

Não versionar:

```txt
.env
venv/
__pycache__/
*.pyc
```

Versionar:

```txt
requirements.txt
alembic/versions/
app/models/
app/routes/
app/schemas/
app/services/
README.md
```


## Task 35 — Validação e Organização do Swagger

Foi realizada a validação da documentação automática da API utilizando o Swagger/OpenAPI disponibilizado pelo FastAPI.

### Verificações realizadas

- Conferência de todas as rotas registradas na aplicação;
- Validação da exibição das rotas em uma única instância do Swagger;
- Verificação da organização dos endpoints por grupos (tags);
- Conferência da disponibilidade da documentação em `/docs`.

### Resultado

A validação confirmou que todos os endpoints da aplicação estão sendo expostos corretamente em uma única documentação Swagger.

Grupos identificados:

- Autenticação
- Descarte
- Endereço
- Inventário do Usuário
- Notificações
- Ponto de Coleta
- QR Code
- Admin

Nenhuma inconsistência foi identificada durante a validação, não sendo necessária alteração estrutural nas rotas ou na configuração do FastAPI.