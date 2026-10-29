import json
import re

import pandas as pd
import psycopg2
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

st.set_page_config(page_title="Dashboard de filmes", page_icon="🎬", layout="wide")

COLUMNS = ["name", "genre", "director", "company"]


# ---------------------------------------------------------------
# FIRESTORE
# ---------------------------------------------------------------
@st.cache_resource
def get_firestore_client():
    """Crea el cliente de Firestore con la cuenta de servicio guardada en st.secrets."""
    key_dict = json.loads(st.secrets["firebase"]["service_account_json"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    return firestore.Client(credentials=creds, project=key_dict["project_id"])


@st.cache_data(ttl=600)
def load_movies():
    """Lee TODOS los documentos de la colección 'movies' y los devuelve en un DataFrame."""
    db = get_firestore_client()
    docs = db.collection("movies").stream()
    rows = [doc.to_dict() for doc in docs]
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(rows)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[COLUMNS].astype(str)


def search_by_title(df, text):
    """Búsqueda parcial ('que contenga') e insensible a mayúsculas/minúsculas."""
    mask = df["name"].str.contains(text, case=False, regex=False, na=False)
    return df[mask]


def filter_by_director(df, director):
    """Devuelve solo las películas del director seleccionado."""
    return df[df["director"] == director]


def insert_movie(name, genre, director, company):
    """Inserta un nuevo documento en la colección 'movies'."""
    db = get_firestore_client()
    db.collection("movies").add(
        {"name": name, "genre": genre, "director": director, "company": company}
    )


# ---------------------------------------------------------------
# POSTGRESQL (AIVEN)
# ---------------------------------------------------------------
def get_pg_connection():
    """Abre una conexión nueva a PostgreSQL con SSL obligatorio (Aiven)."""
    pg = st.secrets["postgres"]
    return psycopg2.connect(
        host=pg["host"],
        port=int(pg["port"]),
        dbname=pg["dbname"],
        user=pg["user"],
        password=pg["password"],
        sslmode="require",
        connect_timeout=10,
    )


def insert_comment(email, comment):
    """INSERT parametrizado en la tabla people."""
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO people (email, comment) VALUES (%s, %s)",
                (email, comment),
            )
        conn.commit()
    finally:
        conn.close()


def load_comments():
    """Consulta la tabla people y devuelve un DataFrame."""
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, comment, created_at FROM people ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return pd.DataFrame(rows, columns=["email", "comment", "created_at"])


# ---------------------------------------------------------------
# INTERFAZ
# ---------------------------------------------------------------
st.title("🎬 Dashboard de filmes")
st.caption("Películas en Firebase Firestore · Libro de visitas en PostgreSQL (Aiven)")

# Mensaje que sobrevive al st.rerun() después de insertar
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

# Carga inicial del dataset base
try:
    movies_df = load_movies()
except Exception as e:
    st.error(f"No se pudo conectar a Firestore: {e}")
    movies_df = pd.DataFrame(columns=COLUMNS)

st.metric("Películas en Firestore", len(movies_df))

# --- A. Checkbox: todos los filmes ---
st.sidebar.header("Opciones")
if st.sidebar.checkbox("Mostrar todos los filmes"):
    st.header("Todos los filmes")
    st.dataframe(movies_df, width="stretch", hide_index=True)

# --- B. Búsqueda por título ---
st.sidebar.subheader("Buscar por título")
title_text = st.sidebar.text_input("Título del filme")
if st.sidebar.button("Buscar filmes"):
    if title_text.strip():
        result = search_by_title(movies_df, title_text.strip())
        st.header(f"Resultados para: '{title_text.strip()}'")
        st.write(f"Total de filmes encontrados: **{len(result)}**")
        st.dataframe(result, width="stretch", hide_index=True)
    else:
        st.sidebar.warning("Escribe un texto para buscar.")

# --- C. Filtro por director ---
st.sidebar.subheader("Filtrar por director")
directors = sorted(
    d for d in movies_df["director"].dropna().unique() if str(d).strip()
)
selected_director = st.sidebar.selectbox("Selecciona un director", directors)
if st.sidebar.button("Filtrar director"):
    if selected_director:
        result = filter_by_director(movies_df, selected_director)
        st.header(f"Filmes de {selected_director}")
        st.write(f"Total de filmes: **{len(result)}**")
        st.dataframe(result, width="stretch", hide_index=True)
    else:
        st.sidebar.warning("No hay directores disponibles.")

# --- D. Formulario para insertar filme ---
st.sidebar.subheader("Nuevo filme")
with st.sidebar.form("new_movie_form", clear_on_submit=True):
    new_name = st.text_input("Nombre")
    new_genre = st.text_input("Género")
    new_director = st.text_input("Director")
    new_company = st.text_input("Compañía")
    save_movie = st.form_submit_button("Guardar filme")

if save_movie:
    values = [v.strip() for v in (new_name, new_genre, new_director, new_company)]
    if all(values):
        try:
            insert_movie(*values)
            load_movies.clear()  # invalida la caché para ver el nuevo filme
            st.session_state["flash"] = f"Filme '{values[0]}' guardado en Firestore."
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error al guardar el filme: {e}")
    else:
        st.sidebar.error("Llena los cuatro campos.")

# --- E. Libro de visitas (PostgreSQL) ---
st.sidebar.divider()
st.sidebar.header("Libro de visitas")
with st.sidebar.form("guestbook_form", clear_on_submit=True):
    email = st.text_input("Correo electrónico")
    comment = st.text_area("Comentario")
    save_comment = st.form_submit_button("Registrar comentario")

if save_comment:
    email, comment = email.strip(), comment.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        st.sidebar.error("Escribe un correo válido.")
    elif not comment:
        st.sidebar.error("Escribe un comentario.")
    else:
        try:
            insert_comment(email, comment)
            st.sidebar.success("¡Gracias! Comentario registrado.")
        except Exception as e:
            st.sidebar.error(f"Error al registrar en PostgreSQL: {e}")

if st.sidebar.button("Ver comentarios"):
    try:
        comments_df = load_comments()
        st.header("Comentarios de los visitantes")
        st.write(f"Total de comentarios: **{len(comments_df)}**")
        st.dataframe(comments_df, width="stretch", hide_index=True)
    except Exception as e:
        st.error(f"Error al leer PostgreSQL: {e}")
