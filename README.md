# Dashboard de filmes

Reto Tecnológico de Monterrey: dashboard interactivo con **Streamlit**, **Firebase Firestore** (películas) y **PostgreSQL en Aiven** (libro de visitas), desplegado en **Streamlit Community Cloud**.

## Funcionalidades

- Lectura de todos los documentos de la colección `movies` en un DataFrame (`load_movies`).
- Checkbox en el sidebar para mostrar todos los filmes con encabezado.
- Búsqueda por título parcial e insensible a mayúsculas (`search_by_title`).
- Selectbox de directores y botón que llama a `filter_by_director`.
- Formulario para insertar filmes en Firestore (`insert_movie`).
- Formulario para registrar comentarios en la tabla `people` de PostgreSQL (`insert_comment`).
- Botón para ver los comentarios registrados (`load_comments`).

## Estructura

```
streamlit_app.py      App principal
setup_data.py         Carga inicial de 25 filmes y creación de la tabla people
requirements.txt      Dependencias
secrets.toml.example  Plantilla de credenciales (valores ficticios)
.streamlit/secrets.toml  Credenciales reales (solo local, ignorado por Git)
```

## Ejecución local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup_data.py
streamlit run streamlit_app.py
```

## Tabla de PostgreSQL

```sql
CREATE TABLE IF NOT EXISTS people (
    id         SERIAL PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    comment    TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

## Credenciales

Se leen con `st.secrets`. Copia `secrets.toml.example` a `.streamlit/secrets.toml` y llena tus datos. En producción, pega el mismo contenido en *Settings > Secrets* de Streamlit Community Cloud.
