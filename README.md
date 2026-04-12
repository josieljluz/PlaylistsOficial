# 📺 IPTV System

Plataforma completa de gerenciamento de playlists IPTV com autenticação de usuários, player integrado e API RESTful.

## ✨ Funcionalidades

- **Autenticação completa** — cadastro, login e sessões seguras com cookies httpOnly
- **Gerenciamento de playlists** — adicionar por URL ou colar conteúdo M3U/M3U8
- **Player integrado** — reprodução direta no browser com HLS.js + Video.js
- **Busca e filtros** — pesquisa por nome e filtro por grupo de canais
- **Download M3U** — exportar playlist para uso em players externos (VLC, Kodi, IPTV Smarters)
- **URL compatível** — endpoint `/get.php` para players IPTV tradicionais
- **Painel Admin** — gerenciar usuários, ver logs de acesso e estatísticas
- **EPG integrado** — suporte a múltiplas fontes de guia eletrônico de programação

## 🚀 Deploy Rápido (GitHub + Render)

### 1. Fork/Clone para o GitHub

```bash
# Clone este repositório
git clone https://github.com/SEU_USUARIO/iptv-system.git
cd iptv-system

# Ou faça fork pelo GitHub e clone o seu fork
```

### 2. Deploy no Render

1. Acesse [render.com](https://render.com) e faça login
2. Clique em **New → Web Service**
3. Conecte seu repositório GitHub
4. Configure:
   - **Name:** `iptv-system`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn api.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
5. Em **Environment Variables**, adicione:
   - `SECRET_KEY` → clique em "Generate" para gerar automaticamente
   - `DB_PATH` → `/tmp/iptv_system.db`
   - `FLASK_ENV` → `production`
6. Clique em **Create Web Service**

> **Nota:** No plano gratuito do Render, o banco de dados em `/tmp` é resetado a cada restart.
> Para dados persistentes, configure um disco ou use um banco externo.

### 3. Configurar Deploy Automático (opcional)

No Render, copie o **Deploy Hook URL** e adicione como variável no GitHub:
- Vá em **Settings → Variables and secrets → Variables**
- Adicione `RENDER_DEPLOY_HOOK` com a URL copiada

## 💻 Instalação Local

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/iptv-system.git
cd iptv-system

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 5. Execute a aplicação
python api/app.py
```

Acesse: [http://localhost:5000](http://localhost:5000)

**Credenciais padrão:** `admin` / `admin123`

## 📡 API Endpoints

### Autenticação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/login` | Login com username/password |
| POST | `/api/auth/register` | Cadastro de novo usuário |
| POST | `/api/auth/logout` | Encerrar sessão |
| GET | `/api/auth/me` | Dados do usuário logado |

### Playlists
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/playlists` | Listar playlists do usuário |
| POST | `/api/playlists` | Criar nova playlist |
| GET | `/api/playlists/:id` | Detalhes de uma playlist |
| PUT | `/api/playlists/:id` | Atualizar playlist |
| DELETE | `/api/playlists/:id` | Excluir playlist |
| GET | `/api/playlists/:id/channels` | Listar canais (paginado) |
| GET | `/api/playlists/:id/groups` | Listar grupos de canais |
| GET | `/api/playlists/:id/download` | Download do arquivo M3U |
| POST | `/api/playlists/:id/refresh` | Recarregar da URL de origem |

### Compatibilidade com Players IPTV
```
GET /get.php?username=USER&password=PASS&playlist_id=ID
```
Compatível com VLC, Kodi, IPTV Smarters, TiviMate e outros.

### Admin (requer conta admin)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/admin/users` | Listar todos os usuários |
| POST | `/api/admin/users` | Criar usuário |
| PUT | `/api/admin/users/:id` | Editar usuário |
| DELETE | `/api/admin/users/:id` | Excluir usuário |
| GET | `/api/admin/stats` | Estatísticas gerais |
| GET | `/api/admin/logs` | Logs de acesso |

## 🏗️ Estrutura do Projeto

```
iptv-system/
├── api/
│   ├── app.py              # Aplicação Flask principal
│   ├── models.py           # Modelos do banco de dados SQLite
│   └── m3u_processor.py    # Processador de playlists M3U
├── static/
│   ├── css/style.css       # Estilos (tema dark)
│   └── js/
│       ├── main.js         # Utilitários compartilhados
│       ├── dashboard.js    # Lógica do dashboard
│       ├── player.js       # Player HLS.js + Video.js
│       └── admin.js        # Painel administrativo
├── templates/
│   ├── base.html           # Template base
│   ├── login.html          # Página de login
│   ├── register.html       # Página de cadastro
│   ├── dashboard.html      # Dashboard de playlists
│   ├── player.html         # Player IPTV
│   └── admin.html          # Painel admin
├── .github/workflows/
│   └── deploy.yml          # CI/CD GitHub Actions
├── render.yaml             # Configuração Render
├── Procfile                # Comando de start
├── requirements.txt        # Dependências Python
└── .env.example            # Exemplo de variáveis de ambiente
```

## 🔧 Tecnologias

- **Backend:** Python 3.11 + Flask 3.0 + SQLite
- **Frontend:** HTML5 + CSS3 + JavaScript (vanilla)
- **Player:** HLS.js + Video.js
- **Deploy:** Render (free tier) + GitHub Actions
- **Auth:** Sessões com cookies httpOnly + hash SHA-256 com salt

## 📝 Licença

MIT License — use livremente.
