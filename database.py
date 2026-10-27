import os
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        caminho = current_app.config["DATABASE"]

        g.db = sqlite3.connect(caminho)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


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
        CREATE TABLE IF NOT EXISTS prestadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            telefone TEXT,
            especialidade TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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