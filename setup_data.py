"""
Script de preparación (se ejecuta UNA vez desde la terminal):
    python setup_data.py

1. Carga 25 películas en Firestore (sin duplicados: usa un ID fijo por película).
2. Crea la tabla 'people' en PostgreSQL (Aiven) si no existe.
3. Imprime conteos para verificar ambas conexiones.

Lee las credenciales de .streamlit/secrets.toml (igual que la app).
"""
import json
import re

import psycopg2
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

MOVIES = [
    ("Star Wars: A New Hope", "Sci-Fi", "George Lucas", "Lucasfilm"),
    ("American Graffiti", "Comedy", "George Lucas", "Universal Pictures"),
    ("Jurassic Park", "Adventure", "Steven Spielberg", "Universal Pictures"),
    ("E.T. the Extra-Terrestrial", "Sci-Fi", "Steven Spielberg", "Universal Pictures"),
    ("Jaws", "Thriller", "Steven Spielberg", "Universal Pictures"),
    ("Schindler's List", "Drama", "Steven Spielberg", "Universal Pictures"),
    ("Inception", "Sci-Fi", "Christopher Nolan", "Warner Bros."),
    ("The Dark Knight", "Action", "Christopher Nolan", "Warner Bros."),
    ("Interstellar", "Sci-Fi", "Christopher Nolan", "Paramount Pictures"),
    ("Oppenheimer", "Drama", "Christopher Nolan", "Universal Pictures"),
    ("Pulp Fiction", "Crime", "Quentin Tarantino", "Miramax"),
    ("Kill Bill: Vol. 1", "Action", "Quentin Tarantino", "Miramax"),
    ("Django Unchained", "Western", "Quentin Tarantino", "Columbia Pictures"),
    ("Pan's Labyrinth", "Fantasy", "Guillermo del Toro", "Warner Bros."),
    ("The Shape of Water", "Fantasy", "Guillermo del Toro", "Fox Searchlight"),
    ("Pinocchio", "Animation", "Guillermo del Toro", "Netflix"),
    ("Gravity", "Sci-Fi", "Alfonso Cuarón", "Warner Bros."),
    ("Roma", "Drama", "Alfonso Cuarón", "Netflix"),
    ("Y tu mamá también", "Drama", "Alfonso Cuarón", "Producciones Anhelo"),
    ("The Revenant", "Adventure", "Alejandro G. Iñárritu", "20th Century Fox"),
    ("Birdman", "Comedy", "Alejandro G. Iñárritu", "Fox Searchlight"),
    ("Amores perros", "Drama", "Alejandro G. Iñárritu", "Altavista Films"),
    ("Titanic", "Romance", "James Cameron", "Paramount Pictures"),
    ("Avatar", "Sci-Fi", "James Cameron", "20th Century Fox"),
    ("The Terminator", "Action", "James Cameron", "Orion Pictures"),
]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def seed_firestore():
    key_dict = json.loads(st.secrets["firebase"]["service_account_json"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
    for name, genre, director, company in MOVIES:
        # .set() con ID fijo: si se ejecuta otra vez, sobrescribe en lugar de duplicar
        db.collection("movies").document(slug(name)).set(
            {"name": name, "genre": genre, "director": director, "company": company}
        )
    total = len(list(db.collection("movies").stream()))
    print(f"[Firestore] OK. Documentos en 'movies': {total}")


def setup_postgres():
    pg = st.secrets["postgres"]
    conn = psycopg2.connect(
        host=pg["host"], port=int(pg["port"]), dbname=pg["dbname"],
        user=pg["user"], password=pg["password"], sslmode="require",
        connect_timeout=10,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS people (
                    id         SERIAL PRIMARY KEY,
                    email      VARCHAR(255) NOT NULL,
                    comment    TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute("SELECT current_database(), COUNT(*) FROM people")
            dbname, count = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    print(f"[PostgreSQL] OK. Base: {dbname} | Registros en 'people': {count}")


if __name__ == "__main__":
    for step in (seed_firestore, setup_postgres):
        try:
            step()
        except Exception as e:
            print(f"[ERROR en {step.__name__}] {e}")
