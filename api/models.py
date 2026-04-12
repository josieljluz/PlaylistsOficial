"""
Modelos do banco de dados SQLite para o IPTV System
"""
import sqlite3
import os
import hashlib
import secrets
import time

DB_PATH = os.environ.get("DB_PATH", "iptv_system.db")


def get_db():
    """Retorna conexão com o banco de dados"""
    # Garantir que o diretório do banco de dados existe (importante para o Render Disk)
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Erro ao criar diretório do banco: {e}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    conn = get_db()
    cur = conn.cursor()

    # Tabela de usuários
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            last_login TEXT,
            token TEXT UNIQUE
        )
    """)

    # Tabela de playlists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            content TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            is_public INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            channel_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Tabela de canais (cache de canais processados)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            group_title TEXT DEFAULT 'OUTROS',
            tvg_id TEXT DEFAULT '',
            tvg_name TEXT DEFAULT '',
            tvg_logo TEXT DEFAULT '',
            position INTEGER DEFAULT 0,
            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
        )
    """)

    # Tabela de logs de acesso
    cur.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            ip_address TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    # Tabela de sessões
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()

    # Criar admin padrão se não existir
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        admin_pass = hash_password("admin123")
        cur.execute("""
            INSERT INTO users (username, password_hash, email, is_admin, is_active)
            VALUES (?, ?, ?, 1, 1)
        """, ("admin", admin_pass, "admin@iptvsystem.com"))
        conn.commit()
        print("✅ Usuário admin criado: admin / admin123")

    conn.close()
    print("✅ Banco de dados inicializado")


def hash_password(password: str) -> str:
    """Gera hash seguro da senha"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash armazenado"""
    try:
        salt, pwd_hash = stored_hash.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == pwd_hash
    except Exception:
        return False


def create_session_token(user_id: int) -> str:
    """Cria token de sessão para o usuário"""
    token = secrets.token_urlsafe(32)
    expires_at = time.strftime(
        "%Y-%m-%d %H:%M:%S",
        time.gmtime(time.time() + 86400 * 7)  # 7 dias
    )
    conn = get_db()
    try:
        # Limpar sessões antigas do usuário
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("""
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, token, expires_at))
        conn.commit()
    finally:
        conn.close()
    return token


def get_user_by_token(token: str):
    """Retorna usuário pelo token de sessão"""
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT u.* FROM users u
            JOIN sessions s ON s.user_id = u.id
            WHERE s.token = ?
              AND s.expires_at > datetime('now')
              AND u.is_active = 1
        """, (token,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_credentials(username: str, password: str):
    """Autentica usuário por username/senha"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,)
        ).fetchone()
        if row and verify_password(password, row["password_hash"]):
            # Atualizar último login
            conn.execute(
                "UPDATE users SET last_login = datetime('now') WHERE id = ?",
                (row["id"],)
            )
            conn.commit()
            return dict(row)
        return None
    finally:
        conn.close()
