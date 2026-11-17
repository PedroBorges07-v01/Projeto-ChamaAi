import os
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        caminho = current_app.config["DATABASE"]
        g.db = sqlite3.connect(caminho, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def _tem_coluna(db, tabela, coluna):
    colunas = db.execute(f"PRAGMA table_info({tabela})").fetchall()
    return any(item["name"] == coluna for item in colunas)

def _migrar_pedidos_finalizado(db):
    
    sql = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='pedidos'"
    ).fetchone()
    if sql is None:
        return  

    if "'finalizado'" in (sql["sql"] or ""):
        return  

    db.commit()  
    db.executescript("""
        PRAGMA foreign_keys = OFF;

        CREATE TABLE pedidos_novo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_usuario_id INTEGER NOT NULL,
            categoria_id INTEGER NOT NULL,
            descricao TEXT NOT NULL,
            foto TEXT,
            status TEXT NOT NULL DEFAULT 'aberto'
                CHECK (status IN ('aberto', 'aceito', 'finalizado', 'cancelado')),
            prestador_id INTEGER,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_usuario_id) REFERENCES usuarios (id),
            FOREIGN KEY (categoria_id) REFERENCES categorias (id),
            FOREIGN KEY (prestador_id) REFERENCES prestadores (id)
        );

        INSERT INTO pedidos_novo
            (id, cliente_usuario_id, categoria_id, descricao, foto,
             status, prestador_id, data_criacao)
        SELECT id, cliente_usuario_id, categoria_id, descricao, foto,
               status, prestador_id, data_criacao
        FROM pedidos;

        DROP TABLE pedidos;
        ALTER TABLE pedidos_novo RENAME TO pedidos;

        PRAGMA foreign_keys = ON;
    """)


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            tipo TEXT NOT NULL
                CHECK (tipo IN ('cliente', 'prestador', 'admin')),
            ativo INTEGER NOT NULL DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS prestadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            telefone TEXT,
            especialidade TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            usuario_id INTEGER UNIQUE,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    """)

    if not _tem_coluna(db, "prestadores", "usuario_id"):
        db.execute("ALTER TABLE prestadores ADD COLUMN usuario_id INTEGER")

    db.execute("""
        CREATE TABLE IF NOT EXISTS prestador_servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestador_id INTEGER NOT NULL,
            categoria_id INTEGER NOT NULL,
            FOREIGN KEY (prestador_id) REFERENCES prestadores (id),
            FOREIGN KEY (categoria_id) REFERENCES categorias (id),
            UNIQUE (prestador_id, categoria_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL UNIQUE,
            telefone TEXT,
            cidade TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_usuario_id INTEGER NOT NULL,
            categoria_id INTEGER NOT NULL,
            descricao TEXT NOT NULL,
            foto TEXT,
            status TEXT NOT NULL DEFAULT 'aberto'
                CHECK (status IN ('aberto', 'aceito', 'finalizado', 'cancelado')),
            prestador_id INTEGER,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_usuario_id) REFERENCES usuarios (id),
            FOREIGN KEY (categoria_id) REFERENCES categorias (id),
            FOREIGN KEY (prestador_id) REFERENCES prestadores (id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS pedido_recusas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            prestador_id INTEGER NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
            FOREIGN KEY (prestador_id) REFERENCES prestadores (id),
            UNIQUE (pedido_id, prestador_id)
        )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS notificacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        pedido_id INTEGER,
        tipo TEXT NOT NULL,
        mensagem TEXT NOT NULL,
        lida INTEGER NOT NULL DEFAULT 0,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
        )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS avaliacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL UNIQUE,
        prestador_id INTEGER NOT NULL,
        cliente_usuario_id INTEGER NOT NULL,
        nota TEXT NOT NULL
            CHECK (nota IN ('excelente', 'bom', 'ruim', 'pessimo')),
        comentario TEXT,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
        FOREIGN KEY (prestador_id) REFERENCES prestadores (id),
        FOREIGN KEY (cliente_usuario_id) REFERENCES usuarios (id)
        )
    """)

    db.execute("""
        UPDATE prestadores
        SET usuario_id = (
            SELECT u.id
            FROM usuarios u
            WHERE u.email = prestadores.email
              AND u.tipo = 'prestador'
            LIMIT 1
        )
        WHERE usuario_id IS NULL
    """)

    _migrar_pedidos_finalizado(db)

    db.commit()


def init_app(app):
    os.makedirs(app.instance_path, exist_ok=True)

    app.config["DATABASE"] = os.path.join(
        app.instance_path,
        "chamaai.db"
    )

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()