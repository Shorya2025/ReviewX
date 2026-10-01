import requests

from github_auth import (
    get_installations,
    create_installation_token
)


GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"


def get_headers(access_token):
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def get_first_installation():

    installations = get_installations()

    if not installations:
        raise RuntimeError(
            "No GitHub App installations found."
        )

    return installations[0]


def get_installation_access_token():

    installation = get_first_installation()

    installation_id = installation["id"]

    token_data = create_installation_token(
        installation_id
    )

    return token_data["token"]


def get_repositories():

    access_token = get_installation_access_token()

    headers = get_headers(access_token)

    response = requests.get(
        f"{GITHUB_API_URL}/installation/repositories",
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


def get_pull_requests(
    owner,
    repo,
    state="open"
):

    access_token = get_installation_access_token()

    headers = get_headers(access_token)

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/pulls"
    )

    params = {
        "state": state,
        "per_page": 30
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"GitHub API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()


def get_pull_request_files(
    owner,
    repo,
    pull_number
):

    access_token = get_installation_access_token()

    headers = get_headers(access_token)

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/pulls/"
        f"{pull_number}/files"
    )

    params = {
        "per_page": 100
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"GitHub API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()


def get_pull_request_diff(
    owner,
    repo,
    pull_number
):

    access_token = get_installation_access_token()

    headers = {
        "Accept": "application/vnd.github.diff",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/pulls/"
        f"{pull_number}"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"GitHub API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.text


if __name__ == "__main__":

    print()
    print("==========================================")
    print("GitHub PR Diff Test")
    print("==========================================")
    print()

    print("Finding GitHub App installation...")

    installation = get_first_installation()

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

    print()

    print("Getting repositories...")

    repository_data = get_repositories()

    repositories = repository_data.get(
        "repositories",
        []
    )

    print(
        f"Found {len(repositories)} "
        f"repository/repositories."
    )

    if not repositories:

        print()
        print(
            "No repositories are accessible "
            "to the GitHub App."
        )

        raise SystemExit

    repository = repositories[0]

    full_name = repository["full_name"]

    owner, repo_name = full_name.split(
        "/",
        1
    )

    print()
    print("Using repository:", full_name)

    print()
    print("Getting open Pull Requests...")

    pull_requests = get_pull_requests(
        owner,
        repo_name
    )

    print(
        f"Found {len(pull_requests)} "
        f"open Pull Request(s)."
    )

    if not pull_requests:

        print()
        print(
            "There is no open Pull Request "
            "to test."
        )

        print()
        print(
            "Create an open Pull Request "
            "in this repository first."
        )

        raise SystemExit

    # Use the first open PR for testing
    pull_request = pull_requests[0]

    pull_number = pull_request["number"]

    print()
    print(
        "Testing Pull Request:",
        f"#{pull_number}"
    )

    print(
        "Title:",
        pull_request["title"]
    )

    print()

    print("Getting changed files...")

    changed_files = get_pull_request_files(
        owner,
        repo_name,
        pull_number
    )

    print(
        f"Found {len(changed_files)} "
        f"changed file(s)."
    )

    for file in changed_files:

        print()
        print(
            "File:",
            file.get("filename")
        )

        print(
            "Status:",
            file.get("status")
        )

        print(
            "Additions:",
            file.get("additions")
        )

        print(
            "Deletions:",
            file.get("deletions")
        )

    print()
    print("Getting actual PR diff...")

    diff = get_pull_request_diff(
        owner,
        repo_name,
        pull_number
    )

    print()
    print("==========================================")
    print("PR DIFF")
    print("==========================================")
    print()

    print(diff)

    print()
    print("==========================================")
    print("PR diff retrieved successfully!")
    print("==========================================")