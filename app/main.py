"""
Aplicação Principal - Residuum
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.routes import admin, auth, campanha, cooperativa, descarte, endereco, ponto_coleta, inventario_usuario, notificacao, pontuacao, solicitacao_ponto_coleta, sorteio, usuario_metricas, voucher, agenda
from app.core.decorators import public
from app.core.security import require_auth_unless_public

app = FastAPI(
    title="Residuum API",
    description="API para gerenciamento de descarte sustentável de resíduos.",
    version="1.0.0",
    dependencies=[Depends(require_auth_unless_public)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro das rotas
app.include_router(auth.router)
app.include_router(descarte.router)
app.include_router(endereco.router)
app.include_router(ponto_coleta.router)
app.include_router(inventario_usuario.router)
app.include_router(pontuacao.router)
app.include_router(usuario_metricas.router)
app.include_router(solicitacao_ponto_coleta.router)
app.include_router(sorteio.router)
app.include_router(voucher.router)
app.include_router(campanha.router)
app.include_router(admin.router)
app.include_router(cooperativa.router)
app.include_router(agenda.router)
app.include_router(notificacao.router, tags=["Notificações"])

@app.get("/")
@public
def root():
    return {"msg": "Residuum API rodando com sucesso!"}

@app.get("/painel-testes", response_class=HTMLResponse)
@public
def painel_testes():
    """
    Painel de testes visual integrado para a API Residuum.
    
    Uma Single Page Application (SPA) com Tailwind CSS para testar:
    - Autenticação de usuários
    - Registro de descartes
    - Simulação de GPS e QR Code
    - Confirmação de descartes pela cooperativa
    - Painel de auditoria com dados atualizados
    """
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Residuum - Painel de Testes</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .section-card { @apply bg-white rounded-lg shadow-lg p-6 mb-6; }
        .btn-primary { @apply bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded transition; }
        .btn-secondary { @apply bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded transition; }
        .btn-danger { @apply bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded transition; }
        .input-field { @apply w-full px-4 py-2 border border-gray-300 rounded mb-3 focus:outline-none focus:border-green-500; }
        .alert { @apply p-4 rounded mb-3; }
        .alert-success { @apply bg-green-100 text-green-800 border border-green-300; }
        .alert-error { @apply bg-red-100 text-red-800 border border-red-300; }
        .alert-info { @apply bg-blue-100 text-blue-800 border border-blue-300; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto p-6">
        <h1 class="text-4xl font-bold text-green-600 mb-2">🌱 Residuum - Painel de Testes</h1>
        <p class="text-gray-600 mb-8">Sistema de gestão de resíduos com gamificação</p>

        <div id="alerts"></div>

        <!-- ==================== SEÇÃO 1: SIMULADOR DO USUÁRIO ==================== -->
        <div class="section-card">
            <h2 class="text-2xl font-bold text-blue-600 mb-4">👤 Seção 1: Simulador do Usuário (Cliente)</h2>

            <!-- Autenticação -->
            <div class="mb-6 p-4 bg-gray-50 rounded">
                <h3 class="text-xl font-bold text-blue-500 mb-3">🔐 Autenticação</h3>
                
                <input type="text" id="authNome" class="input-field" placeholder="Nome completo" value="João Silva">
                <input type="email" id="authEmail" class="input-field" placeholder="Email" value="joao@example.com">
                <input type="password" id="authSenha" class="input-field" placeholder="Senha (qualquer uma)" value="senha123">
                
                <div class="flex gap-2">
                    <button class="btn-primary" onclick="registrarUsuario()">📝 Registrar/Fazer Login</button>
                    <button class="btn-secondary" onclick="apagarToken()">❌ Limpar Token</button>
                </div>
                
                <div id="authStatus" class="mt-3 text-sm text-gray-600"></div>
            </div>

            <!-- Registrar Descarte -->
            <div class="mb-6 p-4 bg-gray-50 rounded">
                <h3 class="text-xl font-bold text-blue-500 mb-3">♻️ Registrar Descarte</h3>
                
                <input type="number" id="descarteQuantidade" class="input-field" placeholder="Peso (kg)" value="5.5" step="0.1" min="0.1">
                
                <label class="block font-bold mb-2">Tipo de Resíduo:</label>
                <select id="descarteResiduoTipo" class="input-field">
                    <option value="garrafa pet">Garrafa PET</option>
                    <option value="lata aluminio">Lata Alumínio</option>
                    <option value="papel">Papel</option>
                </select>

                <input type="number" id="descarteObservacao" class="input-field" placeholder="Observações (opcional)" value="">

                <input type="number" id="pontoColeataId" class="input-field" placeholder="ID do Ponto de Coleta" value="1" min="1">

                <label class="block font-bold mb-2">📍 Simular Localização GPS:</label>
                <div class="flex gap-2 mb-3">
                    <button class="btn-secondary flex-1" onclick="setarGPSPerto()">✅ GPS Perto (Válido)</button>
                    <button class="btn-danger flex-1" onclick="setarGPSLonge()">❌ GPS Longe (Inválido)</button>
                </div>
                <input type="text" id="descarteGPS" class="input-field" placeholder="Coordenadas (lat, lon)" value="-23.550520, -46.633309" readonly>

                <label class="block font-bold mb-2">🎫 QR Code Token (Opcional):</label>
                <input type="text" id="descarteQRCode" class="input-field" placeholder="Cole o token QR Code aqui">
                <button class="btn-secondary w-full mb-3" onclick="gerarQRCodeMock()">🔄 Gerar QR Code Mock</button>

                <button class="btn-primary w-full" onclick="registrarDescarte()">🚀 Enviar Descarte</button>
            </div>
        </div>

        <!-- ==================== SEÇÃO 2: SIMULADOR DA COOPERATIVA ==================== -->
        <div class="section-card">
            <h2 class="text-2xl font-bold text-purple-600 mb-4">🏢 Seção 2: Simulador da Cooperativa (Administrador)</h2>

            <button class="btn-secondary w-full mb-4" onclick="carregarDescartesPendentes()">🔄 Atualizar Descartes Pendentes</button>

            <div id="descartesPendentes" class="space-y-3"></div>
            
            <div id="descartesPendentesVazio" class="text-center text-gray-600 py-8">
                Nenhum descarte pendente no momento
            </div>
        </div>

        <!-- ==================== SEÇÃO 3: PAINEL DE AUDITORIA ==================== -->
        <div class="section-card">
            <h2 class="text-2xl font-bold text-orange-600 mb-4">📊 Seção 3: Painel de Auditoria (Base de Dados)</h2>

            <button class="btn-secondary w-full mb-4" onclick="carregarDadosAuditoria()">🔄 Atualizar Dados</button>

            <!-- Dados do Usuário -->
            <div class="mb-6 p-4 bg-blue-50 rounded">
                <h3 class="text-lg font-bold text-blue-600 mb-3">👤 Dados do Usuário Logado</h3>
                <div id="usuarioDados" class="text-sm space-y-2">
                    <p><strong>Nome:</strong> <span id="usuarioNome">Não autenticado</span></p>
                    <p><strong>Email:</strong> <span id="usuarioEmail">-</span></p>
                    <p><strong>Pontuação Total:</strong> <span id="usuarioPontuacao" class="text-2xl font-bold text-green-600">0</span> pts</p>
                </div>
            </div>

            <!-- Estoque do Ponto -->
            <div class="p-4 bg-green-50 rounded">
                <h3 class="text-lg font-bold text-green-600 mb-3">📦 Estoque do Ponto de Coleta (ID: <span id="pontoIdDisplay">1</span>)</h3>
                <div id="pontoEstoque" class="text-sm space-y-2">
                    <p class="text-gray-600">Carregando inventário...</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_URL = window.location.origin;
        let token = localStorage.getItem('token');
        let usuarioId = localStorage.getItem('usuarioId');
        let usuarioNomeStored = localStorage.getItem('usuarioNome');
        let usuarioEmailStored = localStorage.getItem('usuarioEmail');

        function mostrarAlerta(mensagem, tipo = 'info') {
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-' + tipo;
            alertDiv.textContent = mensagem;
            document.getElementById('alerts').appendChild(alertDiv);
            setTimeout(() => alertDiv.remove(), 5000);
        }

        // ============ AUTENTICAÇÃO ============
        async function registrarUsuario() {
            const nome = document.getElementById('authNome').value;
            const email = document.getElementById('authEmail').value;
            const senha = document.getElementById('authSenha').value;
            const telefone = '11999999999';

            if (!nome || !email || !senha) {
                mostrarAlerta('Preencha todos os campos', 'error');
                return;
            }

            try {
                // Tenta fazer login
                let response = await fetch(API_URL + '/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, senha })
                });

                // Se falhar (usuário não existe), cria novo
                if (response.status === 401) {
                    response = await fetch(API_URL + '/usuarios', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ nome, email, telefone, senha })
                    });

                    if (!response.ok) {
                        throw new Error('Erro ao criar usuário');
                    }

                    mostrarAlerta('Usuário criado! Faça login novamente.', 'success');
                    return;
                }

                const dados = await response.json();
                token = dados.access_token;
                usuarioId = dados.usuario_id || '1'; // Ajustar conforme resposta real
                usuarioNomeStored = nome;
                usuarioEmailStored = email;

                localStorage.setItem('token', token);
                localStorage.setItem('usuarioId', usuarioId);
                localStorage.setItem('usuarioNome', nome);
                localStorage.setItem('usuarioEmail', email);

                document.getElementById('authStatus').innerHTML = 
                    `<div class="alert alert-success">✅ Autenticado como: <strong>${nome}</strong></div>`;

                mostrarAlerta('Login realizado com sucesso!', 'success');
                carregarDadosAuditoria();
            } catch (error) {
                mostrarAlerta('Erro: ' + error.message, 'error');
            }
        }

        function apagarToken() {
            localStorage.removeItem('token');
            localStorage.removeItem('usuarioId');
            localStorage.removeItem('usuarioNome');
            localStorage.removeItem('usuarioEmail');
            token = null;
            usuarioId = null;
            document.getElementById('authStatus').innerHTML = '';
            mostrarAlerta('Token removido', 'info');
        }

        // ============ GPS ============
        function setarGPSPerto() {
            // São Paulo (Av. Paulista) - Próximo ao padrão
            document.getElementById('descarteGPS').value = '-23.561414, -46.656139';
            mostrarAlerta('GPS definido para LOCAL PRÓXIMO (válido)', 'success');
        }

        function setarGPSLonge() {
            // Rio de Janeiro (muito longe de São Paulo)
            document.getElementById('descarteGPS').value = '-22.906847, -43.192537';
            mostrarAlerta('GPS definido para LOCAL DISTANTE (inválido)', 'error');
        }

        // ============ QR CODE ============
        function gerarQRCodeMock() {
            const tokenMock = 'qr_' + Math.random().toString(36).substring(7);
            document.getElementById('descarteQRCode').value = tokenMock;
            mostrarAlerta('QR Code Mock gerado: ' + tokenMock, 'info');
        }

        // ============ DESCARTE ============
        async function registrarDescarte() {
            if (!token) {
                mostrarAlerta('Faça login primeiro!', 'error');
                return;
            }

            const gps = document.getElementById('descarteGPS').value.split(',');
            const [lat, lon] = [parseFloat(gps[0]), parseFloat(gps[1])];

            const dados = {
                quantidade: parseFloat(document.getElementById('descarteQuantidade').value),
                tipo_residuo: document.getElementById('descarteResiduoTipo').value,
                observacao: document.getElementById('descarteObservacao').value || 'Descarte via painel',
                usuario_lat: lat,
                usuario_long: lon,
                ponto_coleta_id: parseInt(document.getElementById('pontoColeataId').value),
                qrcode_token: document.getElementById('descarteQRCode').value || null
            };

            try {
                const response = await fetch(API_URL + '/descarte/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify(dados)
                });

                if (!response.ok) {
                    const erro = await response.json();
                    throw new Error(erro.detail || 'Erro ao registrar descarte');
                }

                const descarte = await response.json();
                mostrarAlerta('✅ Descarte registrado com sucesso (ID: ' + descarte.id_descarte + ')', 'success');
                carregarDescartesPendentes();
                carregarDadosAuditoria();
            } catch (error) {
                mostrarAlerta('❌ Erro: ' + error.message, 'error');
            }
        }

        // ============ DESCARTES PENDENTES (COOPERATIVA) ============
        async function carregarDescartesPendentes() {
            if (!token) return;

            try {
                const response = await fetch(API_URL + '/descarte/pendentes', {
                    method: 'GET',
                    headers: { 'Authorization': 'Bearer ' + token }
                });

                if (!response.ok) throw new Error('Erro ao carregar descartes');

                const descartes = await response.json();
                const container = document.getElementById('descartesPendentes');
                container.innerHTML = '';

                if (descartes.length === 0) {
                    document.getElementById('descartesPendentesVazio').style.display = 'block';
                    return;
                }

                document.getElementById('descartesPendentesVazio').style.display = 'none';

                descartes.forEach(descarte => {
                    const div = document.createElement('div');
                    div.className = 'p-4 bg-yellow-50 rounded border-l-4 border-yellow-500';
                    div.innerHTML = `
                        <div class="flex justify-between items-center mb-2">
                            <strong>ID: ${descarte.id_descarte} | ${descarte.tipo_residuo}</strong>
                            <span class="text-sm bg-yellow-200 px-3 py-1 rounded">PENDENTE</span>
                        </div>
                        <p class="text-sm mb-2">Quantidade: <strong>${descarte.quantidade} kg</strong></p>
                        <p class="text-sm mb-3 text-gray-600">Usuário: ${descarte.usuario_id}</p>
                        <div class="flex gap-2">
                            <input type="number" placeholder="Qty confirmada (kg)" id="qty_${descarte.id_descarte}" 
                                   class="flex-1 px-3 py-2 border rounded text-sm" value="${descarte.quantidade}" step="0.1">
                            <button class="btn-primary text-sm" onclick="confirmarDescarte(${descarte.id_descarte})">
                                ✅ Confirmar
                            </button>
                        </div>
                    `;
                    container.appendChild(div);
                });
            } catch (error) {
                mostrarAlerta('Erro ao carregar descartes: ' + error.message, 'error');
            }
        }

        async function confirmarDescarte(id) {
            const qtyConfirmada = parseFloat(document.getElementById('qty_' + id).value);

            if (!token || !qtyConfirmada) {
                mostrarAlerta('Preencha a quantidade confirmada', 'error');
                return;
            }

            try {
                const response = await fetch(API_URL + '/descarte/' + id + '/confirmar', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({ quantidade_confirmada: qtyConfirmada })
                });

                if (!response.ok) throw new Error('Erro ao confirmar');

                const resultado = await response.json();
                mostrarAlerta(`✅ Descarte confirmado! ${resultado.pontos_gerados} pontos gerados!`, 'success');
                carregarDescartesPendentes();
                carregarDadosAuditoria();
            } catch (error) {
                mostrarAlerta('Erro: ' + error.message, 'error');
            }
        }

        // ============ AUDITORIA ============
        async function carregarDadosAuditoria() {
            // Atualizar dados do usuário logado
            if (token) {
                try {
                    const response = await fetch(API_URL + '/me', {
                        method: 'GET',
                        headers: { 'Authorization': 'Bearer ' + token }
                    });

                    if (response.ok) {
                        const usuario = await response.json();
                        document.getElementById('usuarioNome').textContent = usuario.nome;
                        document.getElementById('usuarioEmail').textContent = usuario.email;
                        document.getElementById('usuarioPontuacao').textContent = usuario.pontuacao_total || 0;
                    }
                } catch (error) {
                    console.error('Erro ao carregar dados do usuário:', error);
                }
            } else {
                if (usuarioNomeStored) {
                    document.getElementById('usuarioNome').textContent = usuarioNomeStored;
                    document.getElementById('usuarioEmail').textContent = usuarioEmailStored;
                }
            }

            // Carregar estoque do ponto
            const pontoId = document.getElementById('pontoColeataId').value;
            document.getElementById('pontoIdDisplay').textContent = pontoId;

            try {
                const response = await fetch(API_URL + '/pontos-coleta/' + pontoId);
                if (response.ok) {
                    const ponto = await response.json();
                    const estoqueDiv = document.getElementById('pontoEstoque');
                    
                    if (!ponto.inventario || Object.keys(ponto.inventario).length === 0) {
                        estoqueDiv.innerHTML = '<p class="text-gray-600">Inventário vazio</p>';
                    } else {
                        let html = '';
                        for (const [tipo, qtd] of Object.entries(ponto.inventario)) {
                            html += `<p><strong>${tipo}:</strong> ${qtd} kg</p>`;
                        }
                        estoqueDiv.innerHTML = html;
                    }
                } else {
                    document.getElementById('pontoEstoque').innerHTML = 
                        '<p class="text-red-600">Erro ao carregar ponto de coleta</p>';
                }
            } catch (error) {
                console.error('Erro ao carregar estoque:', error);
            }
        }

        // Carregar ao iniciar
        window.addEventListener('load', () => {
            if (token) {
                document.getElementById('authStatus').innerHTML = 
                    `<div class="alert alert-success">✅ Autenticado como: <strong>${usuarioNomeStored}</strong></div>`;
            }
            carregarDadosAuditoria();
        });
    </script>
</body>
</html>
""")
