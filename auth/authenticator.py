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
import os
import sys
import logging

# =============================
# CONFIGURACIÓN DE LOGGING
# =============================
logging.basicConfig(
    level=logging.DEBUG,  # Cambia a INFO en producción
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]  # Imprime en consola
)

# Añadir el path para importar el conector de base de datos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database.db_connector as connector

_user_ids = {}

# ======================================================
# FUNCIONES AUXILIARES
# ======================================================

def get_user_credentials():
    """Fetch user credentials from DB with debug info."""
    logging.debug("Fetching user credentials from database...")
    try:
        users = connector.query_to_dataframe(
            "SELECT id_user, username, name, email, password FROM users"
        )
        logging.debug(f"Retrieved {len(users)} users from DB.")
    except Exception as e:
        logging.error(f"Error retrieving users: {e}")
        return {}, {}

    credentials = {"usernames": {}}
    user_ids = {}

    for _, user in users.iterrows():
        credentials["usernames"][user["username"]] = {
            "name": user["name"],
            "email": user["email"],
            "password": user["password"]
        }
        user_ids[user["username"]] = user["id_user"]

    logging.debug("User credentials and ID mapping successfully built.")
    return credentials, user_ids


def setup_authenticator():
    """Initialize authenticator and store user IDs."""
    logging.debug("Setting up authenticator...")
    credentials, user_ids = get_user_credentials()

    if not credentials.get("usernames"):
        logging.warning("No users found in database during authenticator setup.")

    global _user_ids
    _user_ids = user_ids

    try:
        authenticator = stauth.Authenticate(
            credentials=credentials,
            cookie_name="fitness_dashboard_auth",
            key="fitness_dashboard",
            cookie_expiry_days=30
        )
        logging.debug("Authenticator successfully configured.")
    except Exception as e:
        logging.error(f"Failed to initialize authenticator: {e}")
        raise

    return authenticator


def create_user(username, name, email, password):
    """Create user with detailed error tracing."""
    logging.info(f"Creating user '{username}'...")
    try:
        hasher = stauth.Hasher()
        hashed_password = hasher.hash(password)
    except Exception as e:
        logging.error(f"Password hashing failed: {e}")
        return False, "Password hashing error"

    try:
        user_id = connector.insert_data("users", {
            "username": username,
            "name": name,
            "email": email,
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
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm Password", type="password")

        submit_button = st.form_submit_button("Sign Up")

        if submit_button:
            logging.debug(f"Signup attempt: {username}")
            if not all([username, name, email, password]):
                st.error("Please fill in all fields")
                logging.warning("Signup failed: missing fields.")
            elif password != password_confirm:
                st.error("Passwords do not match")
                logging.warning("Signup failed: passwords do not match.")
            else:
                success, result = create_user(username, name, email, password)
                if success:
                    st.success("Account created successfully! Please log in.")
                    logging.info(f"User '{username}' successfully created.")
                    st.session_state["show_signup"] = False
                else:
                    st.error(f"Error creating account: {result}")
                    logging.error(f"Signup error for '{username}': {result}")

    if st.button("Back to Login"):
        logging.debug("User clicked 'Back to Login'.")
        st.session_state["show_signup"] = False

def login_page():
    """Show login form and debug the authentication flow."""
    st.title("🔐 Login")
    logging.debug("Rendering login page...")

    for key in ["authentication_status", "username", "name", "user_id"]:
        st.session_state.setdefault(key, None)

    try:
        authenticator = setup_authenticator()
    except Exception as e:
        st.error("Failed to initialize authenticator.")
        logging.error(f"Authenticator setup failed: {e}")
        return None, None, None, None

    try:
        name, authentication_status, username = authenticator.login("Login", "main")
        logging.debug(f"Login attempt - Username: {username}, Status: {authentication_status}")
    except Exception as e:
        st.error(f"Authentication error: {e}")
        logging.error(f"Authenticator login() failed: {e}")
        return None, None, None, authenticator

    # Handle authentication result
    if authentication_status is True:
        if username in _user_ids:
            st.session_state["user_id"] = _user_ids[username]
        logging.info(f"User '{username}' logged in successfully.")
    elif authentication_status is False:
        logging.warning(f"Login failed for user '{username}'.")
        st.error("Username/password is incorrect")
        show_signup_option()
    elif authentication_status is None:
        logging.info("Login form displayed, waiting for user input.")
        st.warning("Please enter your username and password")
        show_signup_option()

    return authentication_status, username, name, authenticator


def check_authentication():
    """Wrap authentication flow with debug logs."""
    logging.debug("Checking authentication state...")
    for key, default in [
        ("authentication_status", None),
        ("username", None),
        ("name", None),
        ("user_id", None),
        ("show_signup", False)
    ]:
        st.session_state.setdefault(key, default)

    if st.session_state["authentication_status"] != True:
        if st.session_state["show_signup"]:
            logging.debug("Displaying signup page.")
            signup_page()
        else:
            logging.debug("Displaying login page.")
            authentication_status, username, name, authenticator = login_page()
            if authentication_status:
                if username in _user_ids:
                    st.session_state["user_id"] = _user_ids[username]
                return True, username, name, authenticator
        return False, None, None, None

    logging.debug("User already authenticated.")
    return True, st.session_state["username"], st.session_state["name"], setup_authenticator()


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
