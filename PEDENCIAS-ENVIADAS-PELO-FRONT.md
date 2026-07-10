# Pendências do backend para finalizar o app

## 1. Módulo de Campanhas

Criar do zero:

- Model/Banco de dados para `Campanhas`
- Rota `POST` para o admin cadastrar novas campanhas
- Rota `GET` para o app listar campanhas ativas
- Rota `POST` para o usuário se inscrever/participar da campanha

## 2. Sorteios

Faltam rotas de escrita:

- Rota `POST` para o admin cadastrar novos sorteios
- Rota `POST` para o usuário comprar bilhetes
- O backend deve deduzir o valor em pontos do saldo da carteira do usuário com segurança

## 3. Vouchers

Faltam rotas de escrita:

- Rota `POST` para o admin cadastrar novos vouchers
- Rota `POST` para o usuário resgatar um voucher
- O backend deve deduzir os pontos e devolver um código promocional

## 4. Autenticação e sessão

- Implementar fluxo de `Refresh Token` na API de login
- O app precisa disso para a função "Lembre de mim", mantendo o usuário logado no celular sem a sessão expirar

## 5. Métricas do dashboard

- Criar uma rota de consolidação/analytics, por exemplo `GET /usuario/metricas`
- A resposta deve trazer a soma de kg entregues por mês
- O app usa isso para desenhar o gráfico de "Entregas do Ano" na tela inicial do morador

## 6. Gestão e aprovação de pontos de coleta

Painel admin:

- Criar rota `GET` para listar solicitações com status `pendente`
- Criar rota `POST` ou `PUT` para aprovar um pedido
- Criar rota `POST` ou `PUT` para rejeitar um pedido

Ao aprovar, a rota deve:

- Alterar o status da solicitação
- Criar o ponto de coleta real na tabela `ponto_coleta` com status `ativo`
- Alterar a role/permissão do usuário solicitante para `cooperativa`

Ao rejeitar, a rota deve:

- Marcar a solicitação como rejeitada
- Salvar um motivo

## Informações alinhadas com o front

### Sorteios

- O usuário compra um cupom com os pontos adquiridos
- Assim que tiver pontos, o app deve mostrar que ele pode participar do sorteio
- O usuário concorre a um prêmio ao comprar o cupom
- Exemplos de prêmio: dinheiro, aparelhos eletrônicos, entre outros
- A frequência será de 1 sorteio mensal
- No primeiro momento, o sorteio pode ser manual via dashboard
- Sugestão esperada: cada cupom ter uma numeração e o sorteio ser feito a partir dessas numerações
- A regra é permitir somente 1 cupom por usuário
- O critério para participar é ter validado o descarte via presença por GPS

### Campanhas e promoções

- Campanha é uma forma de manipular os dados para gerar engajamento de usuários
- O patrocinador deve ter sua marca em evidência nas campanhas
- O dashboard deve exibir também as informações da campanha
- No momento, as campanhas acumulam pontos
- Futuramente, esses pontos poderão ser trocados por descontos e outras ofertas de parceiros
