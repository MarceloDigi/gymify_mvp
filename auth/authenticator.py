"""
Authenticator Module

This module handles user authentication and management for the Streamlit dashboard. It provides functions for user login, signup, and session management, as well as database interactions for storing and retrieving user credentials.

Modules:
- `get_user_credentials`: Fetches user credentials from the database.
- `setup_authenticator`: Configures the Streamlit Authenticator with user credentials.
- `create_user`: Adds a new user to the database.
- `login_page`: Displays the login page and handles authentication.
- `show_signup_option`: Displays the signup option for new users.
- `signup_page`: Displays the signup page and handles user creation.
- `logout_button`: Displays the logout button.
- `check_authentication`: Checks user authentication status and manages login/signup flow.
- `init_auth_tables`: Initializes authentication tables and creates a default admin user if none exists.

Dependencies:
- `streamlit`
- `streamlit_authenticator`
- `sqlite3`
- `pandas`
- `hashlib`
- `os`
- `pathlib`
- `yaml`

"""
import streamlit as st
import streamlit_authenticator as stauth
import sqlite3
import logging
from datetime import datetime
import time
import pandas as pd

AUTH_KEY   = st.secrets["auth_key"]
COOKIE_NAME= st.secrets.get("cookie_name", "fitness_dashboard_auth")
# =============================
# CONFIGURACIÓN DE LOGGING
# =============================
logging.basicConfig(
    level=logging.INFO,  # Cambia a INFO en producción
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]  # Imprime en consola
)

# Añadir el path para importar el conector de base de datos
import database.db_connector as connector

_user_ids = {}

# ======================================================
# FUNCIONES AUXILIARES
# ======================================================

@st.cache_data(ttl=600, show_spinner=False)
def get_user_credentials():
    """Fetch user credentials from DB (normaliza usernames a minúsculas)."""
    logging.info("🔍 Fetching user credentials from database...")
    try:
        conn = connector.get_db_connection()
        if conn is None:
            logging.error("❌ No DB connection available.")
            return {"usernames": {}}, {}

        t0 = time.time()
        rows = conn.execute("SELECT id_user, username, name, email, password FROM users").fetchall()
        dt = (time.time() - t0) * 1000
        logging.info(f"✅ Users fetched: {len(rows)} in {dt:.0f} ms")

        if len(rows) == 0:
            logging.warning("⚠️ No users found in DB.")
            return {"usernames": {}}, {}

        # Convertimos a dataframe temporal
        users = pd.DataFrame(rows, columns=["id_user", "username", "name", "email", "password"])

    except Exception as e:
        logging.error(f"❌ Error retrieving users: {e}")
        return {"usernames": {}}, {}

    credentials = {"usernames": {}}
    user_ids = {}

    for _, user in users.iterrows():
        username = str(user["username"]).strip().lower()
        credentials["usernames"][username] = {
            "name": user["name"],
            "email": user["email"],
            "password": user["password"]
        }
        user_ids[username] = user["id_user"]

    logging.info("✅ Credentials and ID mapping built successfully.")
    return credentials, user_ids

def build_authenticator_once(force_refresh: bool = False):
    """
    Build the Streamlit Authenticator once per session.
    Use force_refresh=True tras crear/borrar usuarios para recargar credenciales.
    """
    if not force_refresh and "authenticator" in st.session_state and "user_ids" in st.session_state:
        return st.session_state["authenticator"]

    logging.debug("Setting up authenticator...")
    credentials, user_ids = get_user_credentials()
    if not credentials.get("usernames"):
        logging.warning("No users found in database during authenticator setup.")

    try:
        authenticator = stauth.Authenticate(
            credentials=credentials,
            cookie_name=COOKIE_NAME,
            key=AUTH_KEY,
            cookie_expiry_days=30,
        )
        logging.debug("Authenticator successfully configured.")
    except Exception as e:
        logging.error(f"Failed to initialize authenticator: {e}")
        raise

    st.session_state["authenticator"] = authenticator
    st.session_state["user_ids"] = user_ids
    return authenticator

def create_user(username, name, email, born_date, weight, height, password):
    """Create user with detailed error tracing."""
    logging.info(f"Creating user '{username}'...")
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        hashed_password = stauth.Hasher([password]).generate()[0]
    except Exception as e:
        logging.error(f"Password hashing failed: {e}")
        return False, "Password hashing error"

    try:
        user_id = connector.insert_data("users", {
            "username": username,
            "name": name,
            "email": email,
            "born_date": str(born_date),
            "joined_in": today,
            "start_weight": weight,
            "start_height": height,
            "password": hashed_password
        })
        logging.info(f"User '{username}' created successfully with ID {user_id}.")
        return True, user_id
    except sqlite3.IntegrityError:
        logging.warning(f"Attempted to create duplicate user '{username}'.")
        return False, "Username or email already exists"
    except Exception as e:
        logging.error(f"Unexpected error creating user '{username}': {e}")
        return False, str(e)
    
def show_signup_option():
    """
    Display the signup option for new users.

    Provides a button to navigate to the signup page if the user does not have an account.
    """
    logging.debug("Displaying 'Sign Up' option.")
    st.markdown("---")
    st.markdown("Don't have an account?")
    if st.button("Sign Up"):
        logging.info("User clicked 'Sign Up' button.")
        st.session_state["show_signup"] = True

def signup_page():
    """
    Display the signup page and handle user creation.

    Collects user details through a form, validates input,
    and creates a new user in the database.
    """
    logging.debug("Rendering signup page.")
    st.title("📝 Sign Up")

    with st.form("signup_form"):
        username = st.text_input("Username")
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        born_date = st.date_input("Date of Birth", max_value=datetime.now().date(), format="DD/MM/YYYY")
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
        height = st.number_input("Height (cm)", min_value=0, step=1)
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm Password", type="password")

        submit_button = st.form_submit_button("Sign Up")

        if submit_button:
            logging.debug(f"Signup attempt: {username}")
            if not all([username, name, email, born_date, weight, height, password]):
                st.error("Please fill in all fields")
                logging.warning("Signup failed: missing fields.")
            elif password != password_confirm:
                st.error("Passwords do not match")
                logging.warning("Signup failed: passwords do not match.")
            else:
                success, result = create_user(username, name, email, born_date, weight, height, password)
                if success:
                    st.success("Account created successfully! Please log in.")
                    logging.info(f"User '{username}' successfully created.")
                    build_authenticator_once(force_refresh=True) # Fuerza refresco de credenciales en memoria
                    st.session_state["show_signup"] = False
                else:
                    st.error(f"Error creating account: {result}")
                    logging.error(f"Signup error for '{username}': {result}")

    if st.button("Back to Login"):
        logging.debug("User clicked 'Back to Login'.")
        st.session_state["show_signup"] = False

def login_page(location: str = "main"):
    """
    Renderiza el formulario de login y devuelve:
    (authentication_status, username, name, authenticator)

    - Usa usuarios desde DB si existen.
    - Si DB está vacía o falla la carga, usa fallback admin desde secrets.
    - Evita romper si authenticator.login() devuelve None.
    """
    # 1) Cargar credenciales desde DB
    try:
        credentials, user_ids = get_user_credentials()  # debe devolver (dict, dict)
    except Exception as e:
        logging.exception(f"❌ Error loading credentials from DB: {e}")
        credentials, user_ids = {"usernames": {}}, {}

    # 2) Fallback admin si no hay usuarios cargados
    if not credentials.get("usernames"):
        logging.warning("⚠️ No users from DB; using fallback admin from secrets.")
        u = st.secrets.get("admin_username", "admin")
        n = st.secrets.get("admin_name", "Administrator")
        p = st.secrets.get("admin_password", "change_me_now")
        # Hash al vuelo para streamlit-authenticator
        hashed = stauth.Hasher([p]).generate()[0]
        credentials = {"usernames": {u: {"name": n, "password": hashed}}}
        # user_ids opcional para tu app (0 como placeholder)
        user_ids = {u.lower(): 0}

    # 3) Construir authenticator
    try:
        authenticator = stauth.Authenticate(
            credentials,
            cookie_name=COOKIE_NAME,
            key=AUTH_KEY,
            cookie_expiry_days=15,
        )
        st.session_state["authenticator"] = authenticator
    except Exception as e:
        logging.exception(f"❌ Authenticator init failed: {e}")
        st.error(f"No se pudo inicializar el autenticador: {e}")
        return None, None, None, None

    # 4) Pintar formulario y capturar resultado con defensa ante None
    try:
        result = authenticator.login(
            fields={"Form name": "Login", "Username": "Usuario", "Password": "Contraseña"},
            location=location,  # 'main' | 'sidebar'
        )
    except Exception as e:
        logging.exception(f"❌ authenticator.login() failed: {e}")
        st.error(f"Error en login: {e}")
        return None, None, None, authenticator

    if not result:
        # Evita "cannot unpack NoneType"
        logging.warning("Authenticator returned None (no creds UI yet or internal issue).")
        st.info("Introduce tu usuario y contraseña para iniciar sesión.")
        return None, None, None, authenticator

    name, authentication_status, username = result

    # 5) Manejo de estados
    if authentication_status is True:
        uname_l = (username or "").strip().lower()
        st.session_state["username"] = username
        st.session_state["name"] = name
        st.session_state["user_id"] = user_ids.get(uname_l)  # puede ser None si viene del fallback
        logging.info(f"✅ Login OK: {username} (id={st.session_state.get('user_id')})")
        return authentication_status, username, name, authenticator

    if authentication_status is False:
        logging.warning("❌ Credenciales incorrectas.")
        st.error("Usuario o contraseña incorrectos.")
        return authentication_status, None, None, authenticator

    # authentication_status is None
    logging.info("ℹ️ Esperando credenciales de usuario.")
    st.info("Introduce tus credenciales para continuar.")
    return None, None, None, authenticator

def check_authentication():
    logging.debug("Checking authentication state...")
    build_authenticator_once()
    for key, default in [
        ("authentication_status", None),
        ("username", None),
        ("name", None),
        ("user_id", None),
        ("show_signup", False),
    ]:
        st.session_state.setdefault(key, default)

    if st.session_state["authentication_status"] is True:
            logging.debug("User already authenticated.")

            # ✅ Si por el rerun no hay user_id, vuelve a poblarlo desde el mapping
            if not st.session_state.get("user_id"):
                uid_map = st.session_state.get("user_ids", {})
                uname = st.session_state.get("username")
                st.session_state["user_id"] = uid_map.get(uname)

            return True, st.session_state["username"], st.session_state["name"], st.session_state.get("authenticator")

    # No autenticado → muestra login o signup
    if st.session_state["show_signup"]:
        logging.debug("Displaying signup page.")
        signup_page()
        return False, None, None, None

    logging.debug("Displaying login page.")
    authentication_status, username, name, authenticator = login_page()
    if authentication_status:
        if username in st.session_state.get("user_ids", {}):
            st.session_state["user_id"] = st.session_state["user_ids"][username]
        st.session_state["authentication_status"] = True
        st.session_state["username"] = username
        st.session_state["name"] = name

        uid_map = st.session_state.get("user_ids", {})
        st.session_state["user_id"] = uid_map.get(username)   # <-- clave

        return True, username, name, authenticator

    return False, None, None, None

def init_auth_tables():
    """Initialize auth tables and log DB status."""
    logging.debug("Initializing authentication tables...")
    try:
        conn = connector.get_db_connection()
        users = connector.query_to_dataframe("SELECT COUNT(*) as count FROM users")

        count = users.iloc[0]["count"]
        logging.info(f"User count in DB: {count}")

        if count == 0:
            logging.info("No users found, creating default admin...")
            success, result = create_user("admin", "Administrator", "admin@example.com", "admin123")
            if success:
                logging.info("Default admin user created successfully.")
            else:
                logging.error(f"Failed to create default admin: {result}")

        conn.close()
    except Exception as e:
        logging.exception(f"Error initializing auth tables: {e}")

def logout_button(authenticator, label="Cerrar sesión", location="sidebar"):
    """
    Dibuja el botón de logout usando streamlit-authenticator
    y limpia el estado si hace falta.
    """
    try:
        authenticator.logout(label, location=location, key="logout_btn")
    except Exception as e:
        # Fallback manual por si cambia la API
        if st.button(label, key="logout_btn_fallback"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()