"""Registro escolar: Flask, plantillas HTML y SQLite, sin modo depuración."""

import os
import re
import secrets
import sqlite3
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.exceptions import HTTPException

from db import close_db, create_user, get_db, init_db, list_users
from validation import validate_user


def create_app(test_config=None):
    load_dotenv(Path(__file__).with_name(".env"))
    app = Flask(__name__)
    app.config.from_mapping(
        APP_ENV=os.environ.get("APP_ENV", "development"),
        SECRET_KEY=os.environ.get("SECRET_KEY") or None,
        DATABASE=os.environ.get("DATABASE_PATH")
        or str(Path(app.instance_path) / "users.sqlite3"),
        DEBUG=False,
        MAX_CONTENT_LENGTH=8 * 1024,
        MAX_FORM_MEMORY_SIZE=8 * 1024,
        MAX_FORM_PARTS=4,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
        WTF_CSRF_TIME_LIMIT=3600,
    )
    if test_config:
        app.config.update(test_config)

    production = app.config["APP_ENV"] == "production"
    if app.config["APP_ENV"] not in {"development", "production"}:
        raise RuntimeError("APP_ENV debe ser development o production.")
    if production and (
        not isinstance(app.config["SECRET_KEY"], str)
        or len(app.config["SECRET_KEY"]) < 32
    ):
        raise RuntimeError("En producción, configura SECRET_KEY con al menos 32 caracteres aleatorios.")
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = secrets.token_urlsafe(48)
    app.config["SESSION_COOKIE_SECURE"] = production
    if production:
        app.config["DEBUG"] = False

    database = Path(app.config["DATABASE"])
    if not database.is_absolute():
        database = Path(app.root_path) / database
    app.config["DATABASE"] = str(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()

    # Registro global: ninguna ruta POST queda excluida de la protección CSRF.
    CSRFProtect(app)

    def render_index(values=None, errors=None, page=1, status=200):
        users, total = list_users(page)
        pages = max(1, (total + 9) // 10)
        if page > pages:
            abort(404)
        return render_template(
            "index.html", users=users, total=total, page=page, pages=pages,
            values=values if values is not None else {"name": "", "email": "", "age": ""},
            errors=errors or {},
        ), status

    @app.get("/")
    def index():
        if set(request.args) - {"page"} or len(request.args.getlist("page")) > 1:
            abort(400)
        page = request.args.get("page", "1")
        if not re.fullmatch(r"[1-9][0-9]{0,5}", page):
            abort(400)
        return render_index(page=int(page))

    @app.post("/users")
    def register():
        expected = {"name", "email", "age", "csrf_token"}
        if (
            request.args or request.files or set(request.form) != expected
            or any(len(request.form.getlist(key)) != 1 for key in expected)
        ):
            abort(400)
        values, errors = validate_user(request.form)
        if errors:
            return render_index(values, errors, status=422)
        try:
            create_user(values["name"], values["email"], int(values["age"]))
        except sqlite3.IntegrityError as error:
            # Distinguir la restricción UNIQUE sin analizar ni mostrar el mensaje SQL.
            if getattr(error, "sqlite_errorcode", None) == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
                return render_index(
                    values, {"email": "Ese correo ya está registrado."}, status=409
                )
            raise
        flash("Usuario registrado correctamente.", "success")
        # POST/Redirect/GET impide repetir la escritura al actualizar la página.
        return redirect(url_for("index"), code=303)

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return {"status": "ok"}

    def error_page(status, title, message, request_id=None):
        return render_template(
            "error.html", status=status, title=title, message=message, request_id=request_id
        ), status

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return error_page(400, "Formulario no válido", "Recarga la página y vuelve a enviar el formulario.")

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {
            400: ("Solicitud no válida", "Revisa los datos e inténtalo de nuevo."),
            404: ("Página no encontrada", "La página que buscas no está disponible."),
            405: ("Método no permitido", "Usa el formulario para registrar un usuario."),
            413: ("Solicitud demasiado grande", "El formulario supera el tamaño permitido de 8 KiB."),
        }
        title, message = messages.get(error.code, ("Solicitud no disponible", "No se pudo atender esta solicitud."))
        # Conservar cabeceras del protocolo, por ejemplo Allow en HTTP 405.
        response = error.get_response()
        response.set_data(render_template("error.html", status=error.code, title=title, message=message))
        response.content_type = "text/html; charset=utf-8"
        return response

    @app.errorhandler(Exception)
    def unexpected_error(error):
        reference = secrets.token_hex(6)
        # Registrar categoría e identificador, nunca str(error), SQL, formulario,
        # correo, cookies, secretos ni traceback que pueda incluir datos personales.
        app.logger.error("error_id=%s category=%s", reference, type(error).__name__)
        return error_page(500, "No pudimos completar la operación", "Inténtalo de nuevo más tarde.", reference)

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self'; "
            "script-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # Flask-WTF comprueba el referente en solicitudes CSRF HTTPS.
        # Permitirlo solo dentro del mismo origen evita filtrarlo a otros sitios.
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
