"""
Home Page Script

This script serves as the entry point for the Streamlit dashboard. It sets up the page configuration, handles user authentication, and initializes shared data for all pages.

Features:
- **Authentication**: Optional user authentication.
- **Global Data Initialization**: Loads and caches data once per session.
- **User Greeting**: Personalized greeting.
- **Admin Section**: Information and tools for admin users.
"""
import streamlit as st

# --- Imports ---
import auth.authenticator as auth
import utils.data_loader as loader
import database.gsheet_connnector as gsheet_conn

# --- Streamlit page configuration ---
st.set_page_config(page_title="🏠 Dashboard Inicio", layout="wide")

# --- Authentication ---
USE_AUTH = True  # Cambia a False para desactivar login

if USE_AUTH:
    is_authenticated, username, name, authenticator = auth.check_authentication()

    if not is_authenticated:
        st.stop()

    with st.sidebar:
        st.write(f"👋 Hola, {name}")
        auth.logout_button(authenticator)

else:
    username = "admin"
    name = "Administrador"
    st.warning("🔓 Modo sin autenticación activo. Todos los datos están visibles.")
    with st.sidebar:
        st.write(f"👋 Hola, {name} (modo libre)")

# --- Cached data loaders ---
@st.cache_data(ttl=600)
def load_templates_from_gsheet():
    """Carga las plantillas de rutinas desde Google Sheets."""
    return gsheet_conn.read_gsheet(
        spreadsheet_key="GOOGLE_SHEET_KEY_FITNESS_PERSONAL",
        worksheet="Routines"
    )

@st.cache_data(ttl=600)
def load_workout_data():
    """Carga los datasets principales desde la base de datos MySQL."""
    df_track = loader.load_workout_data(track_record_muscles=False)
    df_muscles = loader.load_workout_data(track_record=False)
    return df_track, df_muscles

# --- Global data initialization ---
def initialize_global_data():
    """Carga datos globales una sola vez por sesión."""
    if "df_track_record" not in st.session_state or "df_track_record_muscles" not in st.session_state:
        st.info("Cargando datos globales... ⏳")

        sql_data = loader.load_dim_data(exercises=True, exercise_dim_table=True)

        df_track_record, df_track_record_muscles = load_workout_data()
        df_templates = load_templates_from_gsheet()
        df_exercises = sql_data['exercises']
        df_exercise_dimension_table = sql_data['exercise_dimension_table']

        st.session_state["df_track_record"] = df_track_record
        st.session_state["df_track_record_muscles"] = df_track_record_muscles
        st.session_state["df_templates"] = df_templates
        st.session_state["exercises"] = df_exercises
        st.session_state['exercise_dimension_table'] = df_exercise_dimension_table

        st.success("✅ Datos cargados correctamente.")
    else:
        st.session_state["df_track_record"]
        st.session_state["df_track_record_muscles"]
        st.session_state["df_templates"]
        st.session_state["exercises"]
        st.session_state['exercise_dimension_table']

# --- Run initialization ---
initialize_global_data()

# --- Main page content ---
st.title("🏠 Bienvenido al Dashboard de Entrenamiento")

st.markdown("Usa el menú lateral izquierdo para navegar entre las páginas 📊.")

# --- Admin section ---
if username == "admin":
    st.subheader("🔧 Administración")

    st.write("🆔 ID de usuario logueado:", st.session_state.get("user_id", "⚠️ No definido"))
    st.write("👤 Username:", username)

    with st.expander("Información del Sistema"):
        st.info("La aplicación está conectada a una base de datos MySQL.")
        st.write("📦 Los datos deben estar precargados en MySQL.")
        st.write("🔄 Puedes gestionar la carga de datos usando scripts externos de ETL.")

# --- Optional: botón para recargar manualmente ---
with st.sidebar:
    if st.button("🔄 Recargar datos globales"):
        for key in ["df_track_record", "df_track_record_muscles", "df_templates", 'exercises', 'exercise_dimension_table']:
            if key in st.session_state:
                del st.session_state[key]
        st.cache_data.clear()
        st.experimental_rerun()
