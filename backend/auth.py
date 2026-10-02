import hashlib

import os

import re

import sqlite3

import urllib.parse

from datetime import datetime

import requests



CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

DB_PATH = os.path.join(PROJECT_ROOT, "users.db")



# Yahan apni credentials daalein

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

REDIRECT_URI = "http://localhost:8501"



os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"





def get_db_connection():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn





def init_db():

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password_hash TEXT,

            avatar_url TEXT,

            auth_provider TEXT DEFAULT 'local',

            created_at TEXT NOT NULL

        )

    """)

    conn.commit()



    # Agar purani database file hai toh missing columns ko automatically add karein

    cursor.execute("PRAGMA table_info(users)")

    existing_columns = [col[1] for col in cursor.fetchall()]



    if "avatar_url" not in existing_columns:

        cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")

    if "auth_provider" not in existing_columns:

        cursor.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local'")



    conn.commit()

    conn.close()





def hash_password(password: str) -> str:

    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()





# ============================================================

# STANDARD USERNAME / EMAIL REGISTRATION & LOGIN

# ============================================================



def register_user(username: str, email: str, password: str):

    username = username.strip()

    email = email.strip().lower()

    password = password.strip()



    if not username or not email or not password:

        return False, "All fields are required."



    if len(password) < 6:

        return False, "Password must be at least 6 characters long."



    hashed = hash_password(password)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")



    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(

            """

            INSERT INTO users (username, email, password_hash, auth_provider, created_at) 

            VALUES (?, ?, ?, 'local', ?)

            """,

            (username, email, hashed, now)

        )

        conn.commit()

        conn.close()

        return True, "Account registered successfully! Now sign in."

    except sqlite3.IntegrityError as e:

        error_msg = str(e).lower()

        if "username" in error_msg:

            return False, f"Username '{username}' already exists. Choose another."

        elif "email" in error_msg:

            return False, f"Email '{email}' is already registered."

        return False, "An account with these details already exists."

    except Exception as e:

        return False, f"Registration failed: {str(e)}"





def authenticate_user(username_or_email: str, password: str):

    identifier = username_or_email.strip().lower()

    hashed = hash_password(password.strip())



    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(

        """

        SELECT * FROM users 

        WHERE (LOWER(username) = ? OR LOWER(email) = ?) 

          AND password_hash = ?

        """,

        (identifier, identifier, hashed)

    )

    user = cursor.fetchone()

    conn.close()



    if user:

        return True, dict(user)

    return False, "Invalid username/email or password."





# ============================================================

# OFFICIAL GOOGLE OAUTH 2.0 (RELIABLE DIRECT FLOW)

# ============================================================



def get_google_login_url():

    params = {

        "client_id": GOOGLE_CLIENT_ID,

        "redirect_uri": REDIRECT_URI,

        "response_type": "code",

        "scope": "openid email profile",

        "access_type": "offline",

        "prompt": "select_account"

    }

    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    return url, None





def process_google_callback(auth_code: str):

    try:

        token_url = "https://oauth2.googleapis.com/token"

        token_data = {

            "code": auth_code,

            "client_id": GOOGLE_CLIENT_ID,

            "client_secret": GOOGLE_CLIENT_SECRET,

            "redirect_uri": REDIRECT_URI,

            "grant_type": "authorization_code",

        }

        

        token_resp = requests.post(token_url, data=token_data, timeout=10)

        token_json = token_resp.json()

        

        if "error" in token_json:

            return False, f"Token error: {token_json.get('error_description', token_json.get('error'))}"

        

        access_token = token_json.get("access_token")

        if not access_token:

            return False, "Failed to retrieve access token from Google."



        userinfo_resp = requests.get(

            "https://www.googleapis.com/oauth2/v2/userinfo",

            headers={"Authorization": f"Bearer {access_token}"},

            timeout=10

        )

        profile = userinfo_resp.json()

        

        google_email = profile.get("email", "").strip().lower()

        google_name = profile.get("name", "").strip()

        avatar = profile.get("picture", "")



        if not google_email:

            return False, "Could not fetch verified email from Google."



        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")



        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (google_email,))

        existing_user = cursor.fetchone()



        if existing_user:

            cursor.execute(

                "UPDATE users SET avatar_url = ? WHERE LOWER(email) = ?",

                (avatar, google_email)

            )

            conn.commit()

            cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (google_email,))

            user = cursor.fetchone()

            conn.close()

            return True, dict(user)



        clean_user = re.sub(r"[^a-zA-Z0-9_]", "", google_name.lower().replace(" ", "_"))

        if not clean_user:

            clean_user = google_email.split("@")[0]



        base_name = clean_user

        counter = 1

        while True:

            cursor.execute("SELECT id FROM users WHERE LOWER(username) = ?", (clean_user.lower(),))

            if not cursor.fetchone():

                break

            clean_user = f"{base_name}_{counter}"

            counter += 1



        cursor.execute(

            """

            INSERT INTO users (username, email, avatar_url, auth_provider, created_at)

            VALUES (?, ?, ?, 'google', ?)

            """,

            (clean_user, google_email, avatar, now)

        )

        conn.commit()

        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (google_email,))

        new_user = cursor.fetchone()

        conn.close()



        return True, dict(new_user)

    except Exception as e:

        return False, f"Google login error: {str(e)}"
