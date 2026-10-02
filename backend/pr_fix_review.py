import base64
import json
import requests

from github_auth import create_installation_token
from github_api import (
    get_first_installation,
    get_repositories,
    get_pull_requests,
    get_pull_request_files,
)
from github_comments import post_pull_request_review

from main import review_code
from fix_generator import generate_ai_fix


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


def get_file_content(
    owner,
    repo,
    file_path,
    ref,
    access_token
):

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/contents/"
        f"{file_path}"
    )

    headers = get_headers(access_token)

    response = requests.get(
        url,
        headers=headers,
        params={"ref": ref},
        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            "GitHub file retrieval failed "
            f"{response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    encoded_content = data.get("content")

    if not encoded_content:

        raise RuntimeError(
            f"No file content returned for {file_path}"
        )

    try:

        decoded = base64.b64decode(
            encoded_content
        ).decode("utf-8")

    except Exception as error:

        raise RuntimeError(
            f"Could not decode {file_path}: {error}"
        )

    return decoded


def detect_language(file_path):

    lower_path = file_path.lower()

    if lower_path.endswith(".py"):
        return "python"

    if lower_path.endswith(".js"):
        return "javascript"

    if lower_path.endswith(".ts"):
        return "typescript"

    if lower_path.endswith(".java"):
        return "java"

    if lower_path.endswith(".cpp"):
        return "cpp"

    if lower_path.endswith(".c"):
        return "c"

    if lower_path.endswith(".cs"):
        return "csharp"

    if lower_path.endswith(".go"):
        return "go"

    if lower_path.endswith(".rs"):
        return "rust"

    return "text"


def extract_first_item(data, possible_keys):

    if isinstance(data, list):

        if not data:
            return None

        return data[0]

    if isinstance(data, dict):

        for key in possible_keys:

            value = data.get(key)

            if isinstance(value, list) and value:

                return value[0]

        if "items" in data:

            items = data["items"]

            if isinstance(items, list) and items:

                return items[0]

    return None


def extract_collection(data, possible_keys):

    if isinstance(data, list):

        return data

    if isinstance(data, dict):

        for key in possible_keys:

            value = data.get(key)

            if isinstance(value, list):

                return value

        if isinstance(data.get("items"), list):

            return data["items"]

    return []


def find_fixable_finding(review_result):

    findings = []

    errors = review_result.get(
        "errors",
        []
    )

    if isinstance(errors, list):

        for error in errors:

            if isinstance(error, dict):

                finding = dict(error)

            else:

                finding = {
                    "title": str(error),
                    "severity": "MEDIUM",
                    "confidence": 0.80,
                    "why": str(error)
                }

            findings.append(finding)

    suggestions = review_result.get(
        "suggestions",
        []
    )

    if isinstance(suggestions, list):

        for suggestion in suggestions:

            if isinstance(suggestion, dict):

                finding = dict(suggestion)

            else:

                finding = {
                    "title": str(suggestion),
                    "severity": "LOW",
                    "confidence": 0.70,
                    "why": str(suggestion)
                }

            findings.append(finding)

    for finding in findings:

        text_value = json.dumps(
            finding,
            default=str
        ).strip()

        if text_value:

            return finding

    return None


def build_fix_comment(
    file_path,
    finding,
    fix_result
):

    issue_summary = fix_result.get(
        "issue_summary",
        "AI identified an issue."
    )

    root_cause = fix_result.get(
        "root_cause",
        "See the AI analysis."
    )

    fix_explanation = fix_result.get(
        "fix_explanation",
        "See the suggested corrected code."
    )

    risk_level = fix_result.get(
        "risk_level",
        "UNKNOWN"
    )

    corrected_code = fix_result.get(
        "corrected_code",
        ""
    )

    original_issue = finding.get(
        "title",
        finding.get(
            "why",
            "AI identified an issue."
        )
    )

    comment = (
        "## 🛠️ ReviewX AI Suggested Fix\n\n"

        f"**File:** `{file_path}`\n\n"

        "> This is an **advisory AI-generated fix**.\n"
        "> A human developer must review and approve any changes.\n\n"

        "### Issue\n\n"

        f"{original_issue}\n\n"

        "### AI Fix Summary\n\n"

        f"{issue_summary}\n\n"

        "### Root Cause\n\n"

        f"{root_cause}\n\n"

        "### Risk Level\n\n"

        f"`{risk_level}`\n\n"

        "### Recommended Fix\n\n"

        f"{fix_explanation}\n\n"

        "### Suggested Corrected Code\n\n"

        "```text\n"

        f"{corrected_code}\n"

        "```\n\n"

        "### Human Review Required\n\n"

        "Please verify the suggested code before applying it.\n\n"

        "ReviewX does **not** automatically modify, "
        "approve, reject, or merge the Pull Request."
    )

    return comment


def run_fix_generation():

    print()

    print("==========================================")

    print("ReviewX AI PR Fix Generation")

    print("==========================================")

    print()

    print(
        "Finding GitHub App installation..."
    )

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

    access_token = get_installation_access_token()

    print(
        "Installation access token created."
    )

    print()

    print(
        "Getting repositories..."
    )

    repository_data = get_repositories()

    repositories = extract_collection(
        repository_data,
        [
            "repositories",
            "repos",
            "data"
        ]
    )

    if not repositories:

        raise RuntimeError(
            "No repositories were returned "
            "by the GitHub App."
        )

    print(
        f"Found {len(repositories)} "
        "accessible repository/repositories."
    )

    repository = repositories[0]

    owner = repository.get(
        "owner",
        {}
    ).get(
        "login"
    )

    repo = repository.get(
        "name"
    )

    if not owner or not repo:

        raise RuntimeError(
            "Could not determine repository "
            "owner or repository name."
        )

    print(
        f"Repository: {owner}/{repo}"
    )

    print()

    print(
        "Getting open Pull Requests..."
    )

    pull_request_data = get_pull_requests(
        owner,
        repo,
        state="open"
    )

    pull_requests = extract_collection(
        pull_request_data,
        [
            "pull_requests",
            "pulls",
            "data"
        ]
    )

    if not pull_requests:

        print(
            "No open Pull Request found."
        )

        return

    pull_request = pull_requests[0]

    pull_number = pull_request.get(
        "number"
    )

    head_data = pull_request.get(
        "head",
        {}
    )

    head_sha = head_data.get(
        "sha"
    )

    head_ref = head_data.get(
        "ref"
    )

    print(
        f"Pull Request: #{pull_number}"
    )

    print(
        f"Branch: {head_ref}"
    )

    print(
        f"Commit: {head_sha}"
    )

    print()

    print(
        "Getting changed files..."
    )

    changed_file_data = get_pull_request_files(
        owner,
        repo,
        pull_number
    )

    changed_files = extract_collection(
        changed_file_data,
        [
            "files",
            "changed_files",
            "data"
        ]
    )

    if not changed_files:

        print(
            "No changed files found."
        )

        return

    print(
        f"Changed files: {len(changed_files)}"
    )

    print()

    selected_file = None

    supported_extensions = (
        ".py",
        ".js",
        ".ts",
        ".java",
        ".cpp",
        ".c",
        ".cs",
        ".go",
        ".rs"
    )

    for file_data in changed_files:

        file_path = file_data.get(
            "filename",
            ""
        )

        if file_path.lower().endswith(
            supported_extensions
        ):

            selected_file = file_data

            break

    if selected_file is None:

        print(
            "No supported source-code file "
            "was found in the Pull Request."
        )

        return

    file_path = selected_file[
        "filename"
    ]

    language = detect_language(
        file_path
    )

    print(
        f"Selected file: {file_path}"
    )

    print(
        f"Language: {language}"
    )

    print()

    print(
        "Downloading source code from GitHub..."
    )

    full_file_code = get_file_content(
        owner=owner,
        repo=repo,
        file_path=file_path,
        ref=head_sha,
        access_token=access_token
    )

    print(
        f"Downloaded {len(full_file_code)} characters."
    )

    print()

    print(
        "Running ReviewX AI review..."
    )

    review_result = review_code(
        code=full_file_code,
        language=language,
        project_name=repo
    )

    print(
        "AI review completed."
    )

    print()

    finding = find_fixable_finding(
        review_result
    )

    if finding is None:

        print(
            "No AI finding was available "
            "for fix generation."
        )

        return

    print(
        "AI finding selected:"
    )

    print(
        json.dumps(
            finding,
            indent=2,
            default=str
        )
    )

    print()

    print(
        "Sending finding to AI fix generator..."
    )

    fix_result = generate_ai_fix(
        code=full_file_code,
        finding=finding,
        language=language
    )

    if not fix_result.get(
        "success",
        False
    ):

        print()

        print(
            "AI FIX GENERATION FAILED"
        )

        print()

        print(
            "Error:",
            fix_result.get(
                "error",
                "Unknown error"
            )
        )

        return

    print(
        "AI fix generated successfully."
    )

    print()

    comment_body = build_fix_comment(
        file_path=file_path,
        finding=finding,
        fix_result=fix_result
    )

    print(
        "Posting AI suggested fix to GitHub..."
    )

    review = post_pull_request_review(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        body=comment_body
    )

    print()

    print("==========================================")

    print("AI FIX REVIEW POSTED SUCCESSFULLY!")

    print("==========================================")

    print()

    print(
        "GitHub Review ID:",
        review.get("id")
    )

    print(
        "Pull Request:",
        f"#{pull_number}"
    )

    print(
        "File:",
        file_path
    )

    print()

    print(
        "The suggested fix is now visible "
        "on the GitHub Pull Request."
    )

    print(
        "Human approval is still required."
    )

    print()


if __name__ == "__main__":

    try:

        run_fix_generation()

    except Exception as error:

        print()

        print("==========================================")

        print("AI FIX REVIEW FAILED")

        print("==========================================")

        print()

        print(
            "Error:",
            error
        )

        print()