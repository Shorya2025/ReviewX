import requests

from github_auth import create_installation_token
from github_api import get_first_installation


GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"


def get_installation_access_token():

    installation = get_first_installation()

    installation_id = installation["id"]

    token_data = create_installation_token(
        installation_id
    )

    return token_data["token"]


def get_headers(access_token):

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def post_pull_request_review(
    owner,
    repo,
    pull_number,
    body
):
    """
    Post an advisory review on a GitHub Pull Request.

    The review uses COMMENT so that it does not approve
    or reject the Pull Request.
    """

    access_token = get_installation_access_token()

    headers = get_headers(access_token)

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/pulls/"
        f"{pull_number}/reviews"
    )

    payload = {
        "body": body,
        "event": "COMMENT"
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    if response.status_code not in (200, 201):

        raise RuntimeError(
            f"GitHub review creation failed "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()


def post_inline_review_comment(
    owner,
    repo,
    pull_number,
    commit_id,
    path,
    line,
    body,
    side="RIGHT"
):
    """
    Post an inline review comment on a specific line
    of a Pull Request diff.

    Parameters
    ----------
    owner:
        GitHub repository owner.

    repo:
        GitHub repository name.

    pull_number:
        Pull Request number.

    commit_id:
        SHA of the commit being reviewed.

    path:
        File path inside the repository.

    line:
        Line number in the Pull Request diff.

    body:
        AI review message.

    side:
        Which side of the diff the comment belongs to.
        RIGHT means the new version of the file.
    """

    access_token = get_installation_access_token()

    headers = get_headers(access_token)

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/pulls/"
        f"{pull_number}/comments"
    )

    payload = {
        "body": body,
        "commit_id": commit_id,
        "path": path,
        "line": line,
        "side": side
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    if response.status_code not in (200, 201):

        raise RuntimeError(
            f"GitHub inline comment creation failed "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()


if __name__ == "__main__":

    print()
    print("==========================================")
    print("GitHub PR Comment Test")
    print("==========================================")
    print()

    installation = get_first_installation()

    account = installation.get(
        "account",
        {}
    )

    print(
        "GitHub account:",
        account.get("login")
    )

    print()

    print(
        "GitHub PR comment system is ready."
    )

    print(
        "Overall review comments: ENABLED"
    )

    print(
        "Inline diff comments: ENABLED"
    )

    print(
        "Review event: COMMENT"
    )

    print(
        "The AI will NOT approve or reject the PR."
    )
    