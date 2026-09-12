-- SQL fijo de inicialización. No contiene ni recibe entradas del usuario.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 2 AND 80),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(email) BETWEEN 3 AND 254),
    age INTEGER NOT NULL CHECK(typeof(age) = 'integer' AND age BETWEEN 0 AND 120),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
