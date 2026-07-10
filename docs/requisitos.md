2. Requisitos Funcionais (RF)
Legenda de prioridade: Alta = essencial para o MVP | Média = importante, você pode entrar na
V1 | Baixa = interessante, para versões futuras.
Código Nome Descrição Prioridade
MÓDULO: Cadastro e Autenticação
RF
Cadastro de
Usuário (PF)
O sistema deve permitir que pessoas físicas se
cadastrem informando nome, e-mail, telefone e
endereço. O cadastro deve ser simples e de baixo
esforço para maximizar a conversão.
Alta
RF
Login e
Autenticação
O sistema deve oferecer autenticação segura por
e-mail/senha, com possibilidade de recuperação
de senha.
Alta
RF
Cadastro de
Ponto de Coleta
Pessoa física deve poder solicitar abertura de
ponto de coleta informando: endereço, horário de
funcionamento, tipos de resíduos aceitos e
capacidade estimada de armazenagem. O
cadastro fica pendente até aprovação do
administrador.
Alta
RF
Cadastro de
Ponto de Coleta
(CNPJ)
Empresas (supermercados, eventos,
condomínios) devem poder solicitar abertura de
ponto de coleta com dados de CNPJ, responsável,
endereço e informações operacionais. Aprovação
pelo administrador.
Alta
RF
Aprovação de
Pontos de Coleta
pelo Admin
Administrador deve revisar e aprovar ou rejeitar
solicitações de novos pontos de coleta, podendo
visualizar todas as informações submetidas antes
de tomar a decisão.
Alta
RF006 Perfil de Usuário
Usuário deve poder visualizar e editar seu perfil,
ver seu histórico de descartes, pontuação
acumuladas e recompensas obtidas.
Alta
MÓDULO: Mapa e Pontos de Coleta
RF
Mapa
Georreferenciado
de Pontos
O sistema deve exibir mapa interativo com todos
os pontos de coleta ativos, filtráveis por tipo de
descarte e distância do usuário.
Alta
RF
Visualização de
Ponto de Coleta
Ao selecionar um ponto no mapa, o usuário deve
ver: endereço, horário de funcionamento, tipos de
resíduos aceitos, quantidade acumulada atual e
status (ativo/cheio/inativo).
Alta
RF
Ponto de Coleta
Temporário
O sistema deve suportar criação de pontos de
coleta temporários (para eventos), com data de
início e fim definidas, que desaparecem
automaticamente do mapa após o período.
Mídia
MÓDULO: Registro de Descarte
Código Nome Descrição Prioridade
RF
Validação de
Presença no
Ponto
Ao chegar ao ponto de coleta, o sistema deve
validar a presença do usuário por geolocalização
(GPS do celular). O usuário só consegue transferir
o resíduo se estiver fisicamente próximo ao ponto
cadastrado.
Alta
RF
Transferência de
Resíduo ao Ponto
Após validação de presença, o usuário deve poder
registrar a transferência dos resíduos do seu
estoque para o ponto de coleta, informando tipo e
quantidade.
Alta
RF
Validação por QR
Código (alternativa)
Como alternativa ou complemento à
geolocalização, o ponto de coleta pode
disponibilizar QR Code que o usuário escaneia
para confirmar a presença e iniciar a transferência.
Mídia
MÓDULO: Gamificação e Recompensas
RF
Sistema de
Pontuação (Gift-
Voltar)
O sistema deve atribuir pontos ao usuário após a
confirmação da coleta pela cooperativa. A
pontuação é proporcional à quantidade real
coletada e distribuída entre os usuários que
desenvolvido para aquele ponto.
Alta
RF015 Resgate por
Sorteio/Vale-presente
Usuário deve poder participar de sorteios ou
resgatar vouchers/cupons de desconto usando os
pontos acumulados. No MVP, o foco é sorteio.
Cashback direto em dinheiro é funcionalidade
futura.
Alta
RF016 Histórico de
Pontuação
Usuário deve visualizar extrato completo de
pontos ganhos e resgatados, com data, ponto de
coleta e quantidade de destruição associada.
Mídia
RF
Ranking e
Competições
entre Pontos
O sistema deve permitir criar competições entre
pontos de coleta ou grupos de usuários, com
ranking público de quem mais
descartou/cadastrou em um período.
Funcionalidade futura.
Baixa
MÓDULO: Painel do Ponto de Coleta
RF
Dashboard do
Responsável pelo
Ponto
Responsável pelo ponto de coleta (CPF ou CNPJ)
deve ter painel com: quantidade de resíduos
acumulados por tipo, número de usuários que
usaram o ponto, histórico de coletas realizadas e
status atual (ativo/cheio).
Alta
RF
Notificação de
Ponto Cheio
Quando a quantidade de resíduos atingir o limite
configurado para o ponto, o sistema deve notificar
automaticamente a cooperativa/associação
responsável pela coleta.
Alta
RF
Gestão de
Horários e
Disponibilidade
Responsável pelo ponto deve poder atualizar
horários de funcionamento, pausar
temporariamente o recebimento e informar tipos
de resíduos aceitos a qualquer momento.
Mídia
MÓDULO: Painel da Cooperativa/Associação
Código Nome Descrição Prioridade
RF021 Visualização de
Rotas e Pontos
Cooperativa deve visualizar todos os pontos de
coleta sob sua responsabilidade em mapa, com
status de cada um (quantidade atual, nível de
preenchimento), para planejamento de rotas de
coleta.
Alta
RF
Registro de
Coleta e Pesagem
Após realizar a coleta, a cooperativa deve registrar
no sistema a quantidade real coletada (em kg) por
tipo de resíduo em cada ponto. Esse registro
dispara a distribuição de pontos aos usuários.
Alta
RF
Geração de
Nota/Certificado
de Coleta
O sistema deve gerar documento (nota/certificado)
registrando o volume coletado em cada ponto,
para fins de controle financeiro e eventual
pagamento ao responsável pelo ponto. No MVP,
esse processo pode ser manual.
Mídia
MÓDULO: Dashboard Administrativo (Resíduo)
Painel RF024
Consolidado
Administrador (Residuum) deve ter dashboard
completo com: total de usuários cadastrados, total
de resíduos movimentados por tipo e período,
mapa com todos os pontos ativos, ranking de
pontos mais ativos e indicadores de engajamento.
Alta
RF025 Gestão de
Usuários e Pontos
Administrador deve poder visualizar, editar,
aprovar, suspender e excluir cadastros de
usuários e pontos de coleta.
Alta
RF
Gestão de
Campanhas e
Promoções
Administrador deve poder criar campanhas
promocionais associadas a marcas parceiras (ex:
Heineken, Coca-Cola), definindo período, pontos
de coleta participantes, tipo de resíduo e
premiação.
Mídia
RF027 Exportação de
Dados
Administrador deve poder exportar relatórios de
dados de usuários, resíduos e pontos para fins de
venda de informações a parceiros ou análise
interna.
Mídia
3. Requisitos Não Funcionais (RNF)
Código Categoria Descrição
RNF001 Plataforma O sistema deve ser baseado na web, responsivo e funcional em
dispositivos móveis (smartphones), sem necessidade de
aplicativo nativo instalado. Prioritário para o usuário final.
RNF002 Infraestrutura O sistema deve estar hospedado em ambiente cloud (não
servidor dedicado), com capacidade de escalonamento
automático conforme crescimento da base de usuários.
RNF003 Escalabilidade A arquitetura deve ser projetada para suportar crescimento
significativo de dados e usuários. Embora o MVP comece com
volume baixo, a estrutura de banco de dados e serviços deve
ser desenhado para escalar.
RNF004 Usabilidade O fluxo de cadastro e descarte do usuário final deve ter o
mínimo de etapas possível. O sistema deve ser intuitivo o
suficiente para ser usado por pessoas com baixo letramento
digital, especialmente em comunidades periféricas.
RNF005 Segurança – Dados pessoais de usuários (CPF, telefone, localização) necessários
ser armazenados com criptografia e tratados em conformidade
com a LGPD (Lei Geral de Proteção de Dados).
RNF006 Segurança –
Transações
O módulo de registro de coleta e distribuição de pontos deve ter
controle de integridade para evitar manipulação ou duplicação
de registros.
RNF007 Geolocalização A validação de presença por GPS deve funcionar com precisão
razoável (raio configurável por ponto de coleta) e operar mesmo
em áreas com sinal de internet assustador.
RNF008 Desempenho Páginas principais (mapa, dashboard, perfil) devem carregar em
menos de 3 segundos na conexão 4G padrão.
RNF009 Identidade Visual O front-end deve seguir a identidade visual do Resíduo: fundo
branco, cor primária azul marinho (#1F4E79 ou similar), com
cinza e verde como cores de apoio. Tom visual de tecnologia,
não de empresa ambiental tradicional.
RNF010 Disponibilidade O sistema deve ter tempo de atividade mínimo de 99% em horário
comercial. Manutenções programadas devem ser notificadas
com.
RNF011 Integrações Futuras A arquitetura deve prever, sem necessariamente implementar
no MVP, integração futura com APIs de geolocalização (Google
Maps), sistemas de pagamento e reconhecimento de imagem
via IA.
4. Regras de Negócio (RN)
Código Descrição da Regra
RN001 Um ponto de coleta pode ser cadastrado por pessoa física (CPF) ou jurídica (CNPJ). Ó
tipo de responsável define o que o ponto recebe como contrapartida: CPF recebe
benefícios financeiros/prêmios; O CNPJ coleta dados de comportamento dos usuários.
RN002 Nenhum ponto de coleta entra no sistema sem aprovação manual do administrador
Resíduo, pelo menos no MVP.
RN003 A pontuação do usuário NÃO é creditada no momento do depósito no ponto, mas
somente após uma cooperativa realizar a coleta e registrar o peso real no sistema.
RN004 Os pontos distribuídos são proporcionais à quantidade real coletada. Veja o volume
coletado for menor que o registrado pelos usuários, os pontos são distribuídos
proporcionalmente ao que foi confirmado. Ex: 100 garrafas registradas, 50 coletadas →
cada usuário recebe metade dos pontos que esperava.
RN005 O usuário só pode confirmar um descarte num ponto de coleta se estiver fisicamente ativo
presente (validado por GPS ou QR Code). O sistema deve bloquear confirmações
remotas.
RN006 O objetivo do sistema NÃO é criar o usuário a gerar mais destruição, mas sim a
descartar corretamente o que já gera. A métrica de sucesso é a regularidade do
comportamento, não o volume por usuário.
RN007 Pontos de coleta temporária (eventos) têm dados de início e fim. Após o encerramento, o
ponto é desativado automaticamente e não aparece mais no mapa.
RN008 Campanhas promocionais de marcas parceiras podem ser associadas a pontos de
coleta específicos e períodos definidos. Durante a campanha, a interface exibe a marca
e as condições de promoção ao usuário.
RN009 No MVP, o módulo de pagamento ao responsável pelo ponto (por volume coletado) é
operado de forma manual pela Residuum. A automação desse fluxo é funcionalidade de
versão futura.
RN010 O sistema deve iniciar com foco exclusivo em garrafas PET. Além de novos tipos de
resíduos (papel, papelão, alumínio etc.) ocorre conforme a Residuum firma parcerias
com cooperativas habilitadas.
RN011 Uma cooperativa associada a um ponto de coleta é, no MVP, designada manualmente pelo
administrador. Em versão futura, o sistema vincula automaticamente a cooperativa ativa
mais próxima ao novo ponto.