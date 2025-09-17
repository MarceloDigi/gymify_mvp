"""
Home Page Script

This script serves as the entry point for the Streamlit dashboard. It sets up the page configuration, handles user authentication, and displays the main dashboard content.

Features:
- **Authentication**: Supports toggling authentication on or off.
- **User Greeting**: Displays a personalized greeting for authenticated users.
- **Navigation Instructions**: Guides users to navigate through the dashboard.
- **Admin Section**: Provides additional information and tools for admin users.

Modules:
- `check_authentication`: Verifies user authentication status.
- `logout_button`: Displays a logout button for authenticated users.

Dependencies:
- `streamlit`
- `os`, `sys`, `pathlib`

"""

import streamlit as st

# Set page config (must be the first Streamlit command)
st.set_page_config(page_title="🏠 Dashboard Inicio", layout="wide")

import sys
import os
from pathlib import Path

# Agregar variable para activar/desactivar autenticación
USE_AUTH = True  # <- CAMBIA A True cuando quieras volver a activar login

if USE_AUTH:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from auth.authenticator import check_authentication, logout_button
    is_authenticated, username, name, authenticator = check_authentication()

    if not is_authenticated:
        st.stop()

    with st.sidebar:
        st.write(f"👋 Hola, {name}")
        logout_button(authenticator)

else:
    username = "admin"
    name = "Administrador"
    st.warning("🔓 Modo sin autenticación activo. Todos los datos están visibles.")
    with st.sidebar:
        st.write(f"👋 Hola, {name} (modo libre)")

# Main content
st.title("🏠 Bienvenido al Dashboard de Entrenamiento")

st.markdown("Usa el menú lateral izquierdo para navegar entre las páginas 📊.")

# Admin section
if username == "admin":
    st.subheader("🔧 Administración")

    st.write("🆔 ID de usuario logueado:", st.session_state.get("user_id", "⚠️ No definido"))
    st.write("👤 Username:", username)

    with st.expander("Información del Sistema"):
        st.info("La aplicación ahora está conectada a una base de datos MySQL.")
        st.write("📦 Los datos deben estar precargados en MySQL.")
        st.write("🔄 Puedes gestionar la carga de datos usando scripts externos de ETL.")
