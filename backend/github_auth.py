import os
import time
from pathlib import Path

import jwt
import requests
from dotenv import load_dotenv


# ============================================================
# LOAD .ENV FROM PROJECT ROOT
# ============================================================

# github_auth.py is inside:
# D:\AI-Code-Reviewer\backend\
#
# So parent.parent points to:
# D:\AI-Code-Reviewer\

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


# ============================================================
# GITHUB APP SETTINGS
# ============================================================

GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")

GITHUB_PRIVATE_KEY_PATH = os.getenv(
    "GITHUB_PRIVATE_KEY_PATH"
)

GITHUB_WEBHOOK_SECRET = os.getenv(
    "GITHUB_WEBHOOK_SECRET"
)

GITHUB_API_URL = "https://api.github.com"

GITHUB_API_VERSION = "2026-03-10"


# ============================================================
# LOAD PRIVATE KEY
# ============================================================

def load_private_key():

    if not GITHUB_PRIVATE_KEY_PATH:
        raise ValueError(
            "GITHUB_PRIVATE_KEY_PATH is missing from .env"
        )

    # Convert relative path into absolute path
    key_path = PROJECT_ROOT / GITHUB_PRIVATE_KEY_PATH

    if not key_path.exists():
        raise FileNotFoundError(
            f"Private key not found: {key_path}"
        )

    return key_path.read_text()


# ============================================================
# CREATE GITHUB APP JWT
# ============================================================

def create_app_jwt():

    if not GITHUB_APP_ID:
        raise ValueError(
            "GITHUB_APP_ID is missing from .env"
        )

    private_key = load_private_key()

    now = int(time.time())

    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),
        "iss": GITHUB_APP_ID,
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256"
    )

    return token


# ============================================================
# GET GITHUB APP INSTALLATIONS
# ============================================================

def get_installations():

    jwt_token = create_app_jwt()

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {jwt_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }

    response = requests.get(
        f"{GITHUB_API_URL}/app/installations",
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"GitHub API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()


# ============================================================
# CREATE INSTALLATION ACCESS TOKEN
# ============================================================

def create_installation_token(installation_id):

    jwt_token = create_app_jwt()

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {jwt_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }

    url = (
        f"{GITHUB_API_URL}/app/installations/"
        f"{installation_id}/access_tokens"
    )

    response = requests.post(
        url,
        headers=headers,
        timeout=30
    )

    if response.status_code != 201:

        raise RuntimeError(
            f"GitHub API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()


# ============================================================
# TEST GITHUB APP AUTHENTICATION
# ============================================================

if __name__ == "__main__":

    print("Testing GitHub App authentication...")
    print()

    # --------------------------------------------------------
    # Check configuration
    # --------------------------------------------------------

    print("Project root:")
    print(PROJECT_ROOT)
    print()

    print("Environment file:")
    print(ENV_FILE)
    print()

    print("App ID:")
    print(GITHUB_APP_ID)
    print()

    print("Private key path:")
    print(GITHUB_PRIVATE_KEY_PATH)
    print()

    print(
        "Webhook secret:",
        "SET" if GITHUB_WEBHOOK_SECRET else "NOT SET"
    )

    print()

    # --------------------------------------------------------
    # Create JWT
    # --------------------------------------------------------

    print("Creating JWT...")

    jwt_token = create_app_jwt()

    print("JWT created successfully.")
    print()

    # --------------------------------------------------------
    # Get installations
    # --------------------------------------------------------

    print("Getting GitHub App installations...")

    installations = get_installations()

    print(
        f"Found {len(installations)} installation(s)."
    )

    # --------------------------------------------------------
    # Display installations
    # --------------------------------------------------------

    for installation in installations:

        print()

        print(
            "Installation ID:",
            installation["id"]
        )

        account = installation.get(
            "account",
            {}
        )

        print(
            "Account:",
            account.get("login")
        )

        print(
            "Account type:",
            account.get("type")
        )

    print()

    print(
        "GitHub App authentication is working!"
    )