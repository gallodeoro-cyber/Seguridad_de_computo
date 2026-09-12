"""Una conexión por petición y consultas con valores separados del SQL."""

import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=5)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    # El esquema procede únicamente de este archivo local controlado.
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with get_db() as connection:
        connection.executescript(schema)


def create_user(name, email, age):
    # El contexto confirma la transacción o la revierte al producirse un error.
    with get_db() as connection:
        connection.execute(
            "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
            (name, email, age),
        )


def list_users(page, per_page=10):
    connection = get_db()
    total = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    users = connection.execute(
        "SELECT id, name, email, age, created_at FROM users "
        "ORDER BY id DESC LIMIT ? OFFSET ?",
        (per_page, (page - 1) * per_page),
    ).fetchall()
    return users, total
