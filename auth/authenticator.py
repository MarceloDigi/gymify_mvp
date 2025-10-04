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

# Add parent directory to path so we can import database modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database.db_connector as connector

# Global variable to store user IDs
_user_ids = {}

def get_user_credentials():
    """
    Fetch user credentials from the database.

    Queries the database for user information, including username, name, email, and hashed password.
    Constructs a credentials dictionary for authentication and a mapping of usernames to user IDs.

    Returns:
        tuple: A dictionary of user credentials and a mapping of usernames to user IDs.
    """
    conn = connector.get_db_connection()
    users = connector.query_to_dataframe("SELECT id_user, username, name, email, password FROM users")

    credentials = {
        "usernames": {}
    }

    # Also create a mapping of usernames to user IDs
    user_ids = {}

    for _, user in users.iterrows():
        credentials["usernames"][user["username"]] = {
            "name": user["name"],
            "email": user["email"],
            "password": user["password"]
        }
        user_ids[user["username"]] = user["id_user"]

    return credentials, user_ids

def setup_authenticator():
    """
    Configure the Streamlit Authenticator with user credentials.

    Retrieves user credentials from the database and initializes the authenticator with a cookie name,
    secret key, and expiration settings.

    Returns:
        stauth.Authenticate: An instance of the Streamlit Authenticator.
    """
    # Get credentials from database
    credentials, user_ids = get_user_credentials()

    # Store user_ids in a global variable for later use
    global _user_ids
    _user_ids = user_ids

    # Create a cookie name for the authenticator
    cookie_name = "fitness_dashboard_auth"

    # Set up authenticator with a key
    authenticator = stauth.Authenticate(
        credentials=credentials,
        cookie_name=cookie_name,
        key="fitness_dashboard",
        cookie_expiry_days=30
    )

    return authenticator

def create_user(username, name, email, password):
    """
    Create a new user in the database.

    Hashes the user's password and inserts the user information into the database.

    Args:
        username (str): The username of the new user.
        name (str): The full name of the new user.
        email (str): The email address of the new user.
        password (str): The plaintext password of the new user.

    Returns:
        tuple: A boolean indicating success and either the user ID or an error message.
    """
    # Hash the password - different versions of streamlit-authenticator have different APIs
    try:
        # For newer versions (0.2.0+)
        hasher = stauth.Hasher()
        hashed_password = hasher.hash(password)
    except TypeError:
        # For older versions
        hashed_password = stauth.Hasher([password]).generate()[0]

    # Insert user into database
    try:
        user_id = insert_data("users", {
            "username": username,
            "name": name,
            "email": email,
            "password": hashed_password
        })
        return True, user_id
    except sqlite3.IntegrityError:
        return False, "Username or email already exists"
    except Exception as e:
        return False, str(e)

def login_page():
    """
    Display the login page and handle user authentication.

    Shows a login form and processes authentication using the Streamlit Authenticator.
    Updates the session state with authentication status and user details.

    Returns:
        tuple: Authentication status, username, name, and the authenticator instance.
    """
    st.title("🔐 Login")

    # Initialize session state for authentication
    if "authentication_status" not in st.session_state:
        st.session_state["authentication_status"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "name" not in st.session_state:
        st.session_state["name"] = None
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None

    # Set up authenticator
    authenticator = setup_authenticator()

    # Display login form - handle different versions of streamlit-authenticator
    try:
        name, authentication_status, username = authenticator.login("Login", "main")
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None, None, None, authenticator

    # Handle authentication status
    if authentication_status == True:
        # Store user ID in session state
        global _user_ids
        if username in _user_ids:
            st.session_state["user_id"] = _user_ids[username]
    elif authentication_status == False:
        st.error("Username/password is incorrect")
        show_signup_option()
    elif authentication_status == None:
        st.warning("Please enter your username and password")
        show_signup_option()

    return authentication_status, username, name, authenticator

def show_signup_option():
    """
    Display the signup option for new users.

    Provides a button to navigate to the signup page if the user does not have an account.
    """
    st.markdown("---")
    st.markdown("Don't have an account?")

    if st.button("Sign Up"):
        st.session_state["show_signup"] = True

def signup_page():
    """
    Display the signup page and handle user creation.

    Collects user details through a form, validates the input, and creates a new user in the database.
    Provides feedback on the success or failure of the signup process.
    """
    st.title("📝 Sign Up")

    with st.form("signup_form"):
        username = st.text_input("Username")
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm Password", type="password")

        submit_button = st.form_submit_button("Sign Up")

        if submit_button:
            if not username or not name or not email or not password:
                st.error("Please fill in all fields")
            elif password != password_confirm:
                st.error("Passwords do not match")
            else:
                success, result = create_user(username, name, email, password)
                if success:
                    st.success("Account created successfully! Please log in.")
                    st.session_state["show_signup"] = False
                else:
                    st.error(f"Error creating account: {result}")

    if st.button("Back to Login"):
        st.session_state["show_signup"] = False

def logout_button(authenticator):
    """
    Display the logout button.

    Args:
        authenticator (stauth.Authenticate): The authenticator instance to handle logout.
    """
    authenticator.logout("Logout", "sidebar")

def check_authentication():
    """
    Check user authentication status and manage login/signup flow.

    Verifies if the user is authenticated. If not, displays the login or signup page.
    Updates session state with user details upon successful authentication.

    Returns:
        tuple: Authentication status, username, name, and the authenticator instance.
    """
    # Initialize session state
    if "authentication_status" not in st.session_state:
        st.session_state["authentication_status"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "name" not in st.session_state:
        st.session_state["name"] = None
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
    if "show_signup" not in st.session_state:
        st.session_state["show_signup"] = False

    # If user is not authenticated, show login or signup page
    if st.session_state["authentication_status"] != True:
        if st.session_state["show_signup"]:
            signup_page()
        else:
            authentication_status, username, name, authenticator = login_page()
            if authentication_status:
                # Store user ID in session state
                global _user_ids
                if username in _user_ids:
                    st.session_state["user_id"] = _user_ids[username]
                return True, username, name, authenticator
        return False, None, None, None

    # User is already authenticated
    return True, st.session_state["username"], st.session_state["name"], setup_authenticator()

def init_auth_tables():
    """
    Initialize authentication tables and create a default admin user if none exists.

    Checks if the users table exists and creates a default admin user if the table is empty.
    Logs the success or failure of the admin user creation process.
    """
    try:
        conn = connector.get_db_connection()

        # Check if users table exists and has any users
        users = connector.query_to_dataframe("SELECT COUNT(*) as count FROM users")

        # If no users exist, create admin user
        if users[0]["count"] == 0:
            success, result = create_user("admin", "Administrator", "admin@example.com", "admin123")
            if success:
                print("Created default admin user (username: admin, password: admin123)")
            else:
                print(f"Error creating default admin user: {result}")

        conn.close()
    except Exception as e:
        print(f"Error initializing auth tables: {e}")
