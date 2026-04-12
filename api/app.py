"""
IPTV System - Aplicação Flask Principal
Sistema completo de gerenciamento de playlists IPTV com autenticação
"""
import os
import json
import time
import sqlite3
from functools import wraps
from flask import (
    Flask, request, jsonify, render_template,
    redirect, url_for, session, send_from_directory,
    Response, make_response
)
from flask_cors import CORS

# Importações locais
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import (
    init_db, get_db, hash_password, verify_password,
    create_session_token, get_user_by_token, get_user_by_credentials
)
from m3u_processor import M3UProcessor

# ─── Configuração da aplicação ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32).hex())
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CORS(app, supports_credentials=True)

# Inicializar banco de dados
init_db()


# ─── Decoradores de autenticação ──────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("auth_token") or request.headers.get("X-Auth-Token")
        user = get_user_by_token(token) if token else None
        if not user:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Não autorizado"}), 401
            return redirect(url_for("login_page"))
        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("auth_token") or request.headers.get("X-Auth-Token")
        user = get_user_by_token(token) if token else None
        if not user or not user.get("is_admin"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Acesso negado"}), 403
            return redirect(url_for("dashboard_page"))
        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def log_action(user_id, action):
    """Registra ação no log de acesso"""
    try:
        ip = request.remote_addr or ""
        ua = request.headers.get("User-Agent", "")[:200]
        conn = get_db()
        conn.execute(
            "INSERT INTO access_logs (user_id, action, ip_address, user_agent) VALUES (?, ?, ?, ?)",
            (user_id, action, ip, ua)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ─── Páginas HTML ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    token = request.cookies.get("auth_token")
    user = get_user_by_token(token) if token else None
    if user:
        return redirect(url_for("dashboard_page"))
    return redirect(url_for("login_page"))


@app.route("/login")
def login_page():
    token = request.cookies.get("auth_token")
    user = get_user_by_token(token) if token else None
    if user:
        return redirect(url_for("dashboard_page"))
    return render_template("login.html")


@app.route("/register")
def register_page():
    token = request.cookies.get("auth_token")
    user = get_user_by_token(token) if token else None
    if user:
        return redirect(url_for("dashboard_page"))
    return render_template("register.html")


@app.route("/dashboard")
@login_required
def dashboard_page():
    return render_template("dashboard.html", user=request.current_user)


@app.route("/player")
@login_required
def player_page():
    return render_template("player.html", user=request.current_user)


@app.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html", user=request.current_user)


# ─── API de Autenticação ──────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400

    user = get_user_by_credentials(username, password)
    if not user:
        return jsonify({"error": "Usuário ou senha inválidos"}), 401

    token = create_session_token(user["id"])
    log_action(user["id"], "login")

    resp = make_response(jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "is_admin": bool(user["is_admin"])
        }
    }))
    resp.set_cookie(
        "auth_token", token,
        httponly=True, samesite="Lax",
        max_age=86400 * 7
    )
    return resp


@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip()

    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400
    if len(username) < 3:
        return jsonify({"error": "Usuário deve ter pelo menos 3 caracteres"}), 400
    if len(password) < 6:
        return jsonify({"error": "Senha deve ter pelo menos 6 caracteres"}), 400

    conn = get_db()
    try:
        # Verificar se usuário já existe
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR (email = ? AND email != '')",
            (username, email)
        ).fetchone()
        if existing:
            return jsonify({"error": "Usuário ou e-mail já cadastrado"}), 409

        pwd_hash = hash_password(password)
        conn.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, pwd_hash, email or None)
        )
        conn.commit()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        user = dict(user)

        token = create_session_token(user["id"])
        log_action(user["id"], "register")

        resp = make_response(jsonify({
            "success": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "is_admin": False
            }
        }))
        resp.set_cookie(
            "auth_token", token,
            httponly=True, samesite="Lax",
            max_age=86400 * 7
        )
        return resp
    except sqlite3.IntegrityError:
        return jsonify({"error": "Usuário ou e-mail já cadastrado"}), 409
    finally:
        conn.close()


@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    token = request.cookies.get("auth_token")
    if token:
        conn = get_db()
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
    resp = make_response(jsonify({"success": True}))
    resp.delete_cookie("auth_token")
    return resp


@app.route("/api/auth/me")
@login_required
def api_me():
    user = request.current_user
    return jsonify({
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "is_admin": bool(user["is_admin"]),
        "created_at": user["created_at"],
        "last_login": user["last_login"]
    })


# ─── Proxy Reverso (Antibloqueio / CORS Bypass) ───────────────────────────────
@app.route('/api/proxy')
@login_required
def stream_proxy():
    """
    Proxy reverso para streams e arquivos M3U8.
    Resolve problemas de CORS e oculta a origem real do stream.
    """
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL não fornecida"}), 400
    
    try:
        import requests
        # Headers para simular um player real e evitar bloqueios de User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # Fazer a requisição para a fonte original
        # stream=True para não carregar o vídeo inteiro na memória
        resp = requests.get(url, headers=headers, stream=True, timeout=15, verify=False)
        
        # Repassar os headers importantes (Content-Type é o principal)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'host', 'server']
        headers_to_forward = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
        
        # Adicionar headers de CORS para o navegador aceitar
        headers_to_forward['Access-Control-Allow-Origin'] = '*'
        headers_to_forward['Cache-Control'] = 'no-cache'
        
        # Gerador para transmitir o conteúdo em pedaços
        def generate():
            for chunk in resp.iter_content(chunk_size=1024*64):
                yield chunk

        return Response(generate(), status=resp.status_code, headers=headers_to_forward)
        
    except Exception as e:
        return jsonify({"error": f"Falha no proxy: {str(e)}"}), 500


# ─── API de Playlists ─────────────────────────────────────────────────────────
@app.route("/api/playlists", methods=["GET"])
@login_required
def api_list_playlists():
    user = request.current_user
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, name, description, source_url, is_public,
                   created_at, updated_at, channel_count
            FROM playlists
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (user["id"],)).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/playlists", methods=["POST"])
@login_required
def api_create_playlist():
    user = request.current_user
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    source_url = data.get("source_url", "").strip()
    content = data.get("content", "").strip()
    is_public = int(bool(data.get("is_public", False)))

    if not name:
        return jsonify({"error": "Nome da playlist é obrigatório"}), 400

    # Processar conteúdo M3U
    processor = M3UProcessor()
    canais = []

    if source_url:
        try:
            canais = processor.processar_url(source_url)
            content = processor.gerar_m3u(canais, name)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    elif content:
        canais = processor.processar_texto(content)

    conn = get_db()
    try:
        cur = conn.execute("""
            INSERT INTO playlists (user_id, name, description, content, source_url, is_public, channel_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user["id"], name, description, content, source_url, is_public, len(canais)))
        conn.commit()
        playlist_id = cur.lastrowid

        # Salvar canais
        if canais:
            for i, c in enumerate(canais):
                conn.execute("""
                    INSERT INTO channels (playlist_id, name, url, group_title, tvg_id, tvg_name, tvg_logo, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    playlist_id,
                    c.get("nome", "Sem Nome"),
                    c.get("url", ""),
                    c.get("group", "OUTROS"),
                    c.get("tvg_id", ""),
                    c.get("tvg_name", ""),
                    c.get("tvg_logo", ""),
                    i
                ))
            conn.commit()

        log_action(user["id"], f"create_playlist:{name}")
        return jsonify({"success": True, "id": playlist_id, "channel_count": len(canais)}), 201
    finally:
        conn.close()


@app.route("/api/playlists/<int:playlist_id>", methods=["GET"])
@login_required
def api_get_playlist(playlist_id):
    user = request.current_user
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT * FROM playlists
            WHERE id = ? AND (user_id = ? OR is_public = 1)
        """, (playlist_id, user["id"])).fetchone()
        if not row:
            return jsonify({"error": "Playlist não encontrada"}), 404
        return jsonify(dict(row))
    finally:
        conn.close()


@app.route("/api/playlists/<int:playlist_id>", methods=["PUT"])
@login_required
def api_update_playlist(playlist_id):
    user = request.current_user
    data = request.get_json() or {}
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM playlists WHERE id = ? AND user_id = ?",
            (playlist_id, user["id"])
        ).fetchone()
        if not row:
            return jsonify({"error": "Playlist não encontrada"}), 404

        name = data.get("name", row["name"]).strip()
        description = data.get("description", row["description"]).strip()
        source_url = data.get("source_url", row["source_url"]).strip()
        content = data.get("content", row["content"]).strip()
        is_public = int(bool(data.get("is_public", row["is_public"])))

        # Reprocessar se URL mudou
        processor = M3UProcessor()
        canais = []
        if source_url and source_url != row["source_url"]:
            try:
                canais = processor.processar_url(source_url)
                content = processor.gerar_m3u(canais, name)
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        elif content != row["content"]:
            canais = processor.processar_texto(content)

        channel_count = len(canais) if canais else row["channel_count"]

        conn.execute("""
            UPDATE playlists
            SET name=?, description=?, content=?, source_url=?, is_public=?,
                updated_at=datetime('now'), channel_count=?
            WHERE id=?
        """, (name, description, content, source_url, is_public, channel_count, playlist_id))

        if canais:
            conn.execute("DELETE FROM channels WHERE playlist_id = ?", (playlist_id,))
            for i, c in enumerate(canais):
                conn.execute("""
                    INSERT INTO channels (playlist_id, name, url, group_title, tvg_id, tvg_name, tvg_logo, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    playlist_id,
                    c.get("nome", "Sem Nome"),
                    c.get("url", ""),
                    c.get("group", "OUTROS"),
                    c.get("tvg_id", ""),
                    c.get("tvg_name", ""),
                    c.get("tvg_logo", ""),
                    i
                ))

        conn.commit()
        return jsonify({"success": True, "channel_count": channel_count})
    finally:
        conn.close()


@app.route("/api/playlists/<int:playlist_id>", methods=["DELETE"])
@login_required
def api_delete_playlist(playlist_id):
    user = request.current_user
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM playlists WHERE id = ? AND user_id = ?",
            (playlist_id, user["id"])
        ).fetchone()
        if not row:
            return jsonify({"error": "Playlist não encontrada"}), 404

        conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/playlists/<int:playlist_id>/channels", methods=["GET"])
@login_required
def api_get_channels(playlist_id):
    user = request.current_user
    group = request.args.get("group", "")
    search = request.args.get("search", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(200, int(request.args.get("per_page", 50)))

    conn = get_db()
    try:
        # Verificar acesso
        row = conn.execute(
            "SELECT id FROM playlists WHERE id = ? AND (user_id = ? OR is_public = 1)",
            (playlist_id, user["id"])
        ).fetchone()
        if not row:
            return jsonify({"error": "Playlist não encontrada"}), 404

        # Construir query
        conditions = ["playlist_id = ?"]
        params = [playlist_id]

        if group:
            conditions.append("group_title = ?")
            params.append(group)
        if search:
            conditions.append("(name LIKE ? OR group_title LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where = " AND ".join(conditions)

        total = conn.execute(
            f"SELECT COUNT(*) FROM channels WHERE {where}", params
        ).fetchone()[0]

        offset = (page - 1) * per_page
        channels = conn.execute(
            f"SELECT * FROM channels WHERE {where} ORDER BY position, name LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "channels": [dict(c) for c in channels]
        })
    finally:
        conn.close()


@app.route("/api/playlists/<int:playlist_id>/groups", methods=["GET"])
@login_required
def api_get_groups(playlist_id):
    user = request.current_user
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM playlists WHERE id = ? AND (user_id = ? OR is_public = 1)",
            (playlist_id, user["id"])
        ).fetchone()
        if not row:
            return jsonify({"error": "Playlist não encontrada"}), 404

        groups = conn.execute("""
            SELECT group_title, COUNT(*) as count
            FROM channels WHERE playlist_id = ?
            GROUP BY group_title ORDER BY group_title
        """, (playlist_id,)).fetchall()

        return jsonify([dict(g) for g in groups])
    finally:
        conn.close()


@app.route("/api/playlists/<int:playlist_id>/download")
@login_required
def api_download_single_playlist(playlist_id):
    user = request.current_user
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM playlists WHERE id = ? AND (user_id = ? OR is_public = 1)",
            (playlist_id, user["id"])
        ).fetchone()
        if not row:
            return jsonify({"error": "Playlist não encontrada"}), 404

        content = row["content"]
        if not content:
            # Gerar a partir dos canais
            channels = conn.execute(
                "SELECT * FROM channels WHERE playlist_id = ? ORDER BY position",
                (playlist_id,)
            ).fetchall()
            canais = []
            for c in channels:
                canais.append({
                    "nome": c["name"],
                    "url": c["url"],
                    "group": c["group_title"],
                    "tvg_id": c["tvg_id"],
                    "tvg_name": c["tvg_name"],
                    "tvg_logo": c["tvg_logo"]
                })
            processor = M3UProcessor()
            content = processor.gerar_m3u(canais, row["name"])

        filename = f"{row['name'].replace(' ', '_')}.m3u"
        return Response(
            content,
            mimetype="application/x-mpegurl",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    finally:
        conn.close()


@app.route("/api/playlists/<int:playlist_id>/refresh", methods=["POST"])
@login_required
def api_refresh_playlist(playlist_id):
    """Recarrega playlist a partir da URL de origem"""
    user = request.current_user
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM playlists WHERE id = ? AND user_id = ?",
            (playlist_id, user["id"])
        ).fetchone()
        if not row:
            return jsonify({"error": "Playlist não encontrada"}), 404

        if not row["source_url"]:
            return jsonify({"error": "Playlist não possui URL de origem"}), 400

        processor = M3UProcessor()
        canais = processor.processar_url(row["source_url"])
        content = processor.gerar_m3u(canais, row["name"])

        conn.execute("""
            UPDATE playlists
            SET content=?, channel_count=?, updated_at=datetime('now')
            WHERE id=?
        """, (content, len(canais), playlist_id))

        conn.execute("DELETE FROM channels WHERE playlist_id = ?", (playlist_id,))
        for i, c in enumerate(canais):
            conn.execute("""
                INSERT INTO channels (playlist_id, name, url, group_title, tvg_id, tvg_name, tvg_logo, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                playlist_id,
                c.get("nome", "Sem Nome"),
                c.get("url", ""),
                c.get("group", "OUTROS"),
                c.get("tvg_id", ""),
                c.get("tvg_name", ""),
                c.get("tvg_logo", ""),
                i
            ))
        conn.commit()

        log_action(user["id"], f"refresh_playlist:{playlist_id}")
        return jsonify({"success": True, "channel_count": len(canais)})
    finally:
        conn.close()


# ─── API compatível com formato antigo get.php ────────────────────────────────
@app.route("/get.php")
def get_php_compat():
    """Endpoint compatível com players IPTV (VLC, Kodi, IPTV Smarters)"""
    username = request.args.get("username", "")
    password = request.args.get("password", "")
    playlist_id = request.args.get("playlist_id", "")
    output = request.args.get("output", "m3u_plus")

    user = get_user_by_credentials(username, password)
    if not user:
        return Response("Unauthorized", status=401)

    conn = get_db()
    try:
        if playlist_id:
            row = conn.execute(
                "SELECT * FROM playlists WHERE id = ? AND (user_id = ? OR is_public = 1)",
                (playlist_id, user["id"])
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM playlists WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1",
                (user["id"],)
            ).fetchone()

        if not row:
            return Response("No playlist found", status=404)

        content = row["content"]
        if not content:
            channels = conn.execute(
                "SELECT * FROM channels WHERE playlist_id = ? ORDER BY position",
                (row["id"],)
            ).fetchall()
            canais = [{"nome": c["name"], "url": c["url"], "group": c["group_title"],
                       "tvg_id": c["tvg_id"], "tvg_name": c["tvg_name"], "tvg_logo": c["tvg_logo"]}
                      for c in channels]
            processor = M3UProcessor()
            content = processor.gerar_m3u(canais, row["name"])

        log_action(user["id"], f"get_php:{row['id']}")
        return Response(content, mimetype="application/x-mpegurl")
    finally:
        conn.close()


# ─── API Admin ────────────────────────────────────────────────────────────────
@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_admin_users():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT u.id, u.username, u.email, u.is_admin, u.is_active,
                   u.created_at, u.last_login,
                   COUNT(p.id) as playlist_count
            FROM users u
            LEFT JOIN playlists p ON p.user_id = u.id
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/admin/users/<int:user_id>", methods=["PUT"])
@admin_required
def api_admin_update_user(user_id):
    data = request.get_json() or {}
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return jsonify({"error": "Usuário não encontrado"}), 404

        is_active = int(bool(data.get("is_active", row["is_active"])))
        is_admin = int(bool(data.get("is_admin", row["is_admin"])))
        email = data.get("email", row["email"])

        updates = ["is_active = ?", "is_admin = ?", "email = ?"]
        params = [is_active, is_admin, email]

        if data.get("password"):
            updates.append("password_hash = ?")
            params.append(hash_password(data["password"]))

        params.append(user_id)
        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/admin/users", methods=["POST"])
@admin_required
def api_admin_create_user():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip()
    is_admin = int(bool(data.get("is_admin", False)))

    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, email, is_admin) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), email or None, is_admin)
        )
        conn.commit()
        return jsonify({"success": True}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Usuário ou e-mail já cadastrado"}), 409
    finally:
        conn.close()


@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def api_admin_delete_user(user_id):
    if user_id == request.current_user["id"]:
        return jsonify({"error": "Não é possível excluir o próprio usuário"}), 400
    conn = get_db()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/admin/stats")
@admin_required
def api_admin_stats():
    conn = get_db()
    try:
        stats = {
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "active_users": conn.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0],
            "playlists": conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0],
            "channels": conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0],
            "logs_today": conn.execute(
                "SELECT COUNT(*) FROM access_logs WHERE date(created_at) = date('now')"
            ).fetchone()[0],
        }
        return jsonify(stats)
    finally:
        conn.close()


@app.route("/api/admin/logs")
@admin_required
def api_admin_logs():
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, int(request.args.get("per_page", 50)))
    offset = (page - 1) * per_page

    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM access_logs").fetchone()[0]
        rows = conn.execute("""
            SELECT l.*, u.username
            FROM access_logs l
            LEFT JOIN users u ON u.id = l.user_id
            ORDER BY l.created_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset)).fetchall()
        return jsonify({"total": total, "logs": [dict(r) for r in rows]})
    finally:
        conn.close()


# ─── Endpoints de Compatibilidade (Xtream/M3U) ─────────────────────────────────
@app.route("/api/get.php")
def api_get_php():
    """
    Endpoint compatível com o formato Xtream Codes / Painéis antigos.
    Permite que players externos (VLC, Smarters) acessem a playlist unificada.
    """
    username = request.args.get("username")
    password = request.args.get("password")
    
    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400
    
    user = get_user_by_credentials(username, password)
    if not user:
        return jsonify({"error": "Credenciais inválidas"}), 401
    
    log_action(user["id"], "external_access_get_php")
    return download_user_playlist(user["id"])


@app.route("/api/playlist")
@login_required
def api_download_playlist():
    """Download da playlist unificada do usuário logado"""
    user = request.current_user
    log_action(user["id"], "download_playlist_m3u")
    return download_user_playlist(user["id"])


def download_user_playlist(user_id):
    """Gera e retorna a playlist M3U unificada de todas as listas do usuário"""
    conn = get_db()
    try:
        # Buscar todos os canais de todas as playlists do usuário
        rows = conn.execute("""
            SELECT c.*, p.name as playlist_name
            FROM channels c
            JOIN playlists p ON p.id = c.playlist_id
            WHERE p.user_id = ?
            ORDER BY p.id, c.position
        """, (user_id,)).fetchall()
        
        if not rows:
            content = "#EXTM3U\n# Nenhuma playlist encontrada para este usuário."
        else:
            processor = M3UProcessor()
            canais = []
            for r in rows:
                canais.append({
                    "nome": r["name"],
                    "url": r["url"],
                    "group": r["group_title"],
                    "tvg_id": r["tvg_id"],
                    "tvg_name": r["tvg_name"],
                    "tvg_logo": r["tvg_logo"]
                })
            content = processor.gerar_m3u(canais, "Minha Lista IPTV")
            
        response = Response(content, mimetype="application/vnd.apple.mpegurl")
        response.headers["Content-Disposition"] = "attachment; filename=playlist.m3u"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    finally:
        conn.close()


# ─── Inicialização ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
