"""Reglas del ejercicio: normalizar primero y validar después, sin borrar ataques."""

import re
import unicodedata

from email_validator import EmailNotValidError, validate_email


def validate_user(form):
    """Devuelve los valores canónicos y los errores que puede ver el usuario."""
    values = {key: form.get(key, "") for key in ("name", "email", "age")}
    errors = {}

    # Limitar antes de normalizar evita trabajo excesivo. Nunca se guarda un
    # valor recortado silenciosamente: el usuario debe corregirlo.
    for key, value in values.items():
        if len(value) > 512:
            errors[key] = "El valor enviado es demasiado largo."
            values[key] = ""

    raw_name = values["name"]
    has_controls = any(unicodedata.category(char).startswith("C") for char in raw_name)
    name = " ".join(unicodedata.normalize("NFC", raw_name).split())
    values["name"] = name
    allowed_name = all(
        unicodedata.category(char)[0] in {"L", "M"} or char in " '-’."
        for char in name
    )
    has_letter = any(unicodedata.category(char).startswith("L") for char in name)
    if "name" not in errors and (
        has_controls or not 2 <= len(name) <= 80 or not allowed_name or not has_letter
    ):
        errors["name"] = (
            "Escribe entre 2 y 80 caracteres: letras, espacios, apóstrofos, guiones o puntos."
        )

    raw_email = values["email"]
    email = unicodedata.normalize("NFC", raw_email).strip()
    values["email"] = email
    if "email" not in errors:
        try:
            if any(unicodedata.category(char).startswith("C") for char in raw_email):
                raise EmailNotValidError("Control character")
            result = validate_email(email, check_deliverability=False, allow_smtputf8=False)
            # Política de esta demo: el correo completo no distingue mayúsculas.
            # ascii_email convierte dominios internacionales a su forma IDNA.
            canonical_email = result.ascii_email.lower()
            if len(canonical_email) > 254:
                raise EmailNotValidError("Too long")
            values["email"] = canonical_email
        except EmailNotValidError:
            errors["email"] = "Escribe un correo válido, de hasta 254 caracteres."

    age = values["age"].strip()
    values["age"] = age
    if "age" not in errors:
        if not re.fullmatch(r"[0-9]{1,3}", age) or not 0 <= int(age) <= 120:
            errors["age"] = "Escribe una edad entera entre 0 y 120 años."
        else:
            values["age"] = str(int(age))

    return values, errors
