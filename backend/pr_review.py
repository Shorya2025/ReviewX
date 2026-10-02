from pathlib import Path
import re
import requests

from github_api import (
    get_first_installation,
    get_repositories,
    get_pull_requests,
    get_pull_request_files,
)

from github_auth import create_installation_token

from github_comments import (
    post_pull_request_review,
    post_inline_review_comment,
)

from main import review_code


GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"


# ============================================================
# LANGUAGE DETECTION
# ============================================================

def detect_language(filename):
    """
    Detect programming language from file extension.
    """

    extension = Path(filename).suffix.lower()

    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".rb": "ruby",
        ".kt": "kotlin",
        ".swift": "swift",
    }

    return language_map.get(
        extension,
        "text"
    )


# ============================================================
# FALLBACK: EXTRACT ADDED CODE FROM PATCH
# ============================================================

def extract_added_code(patch):
    """
    Extract newly added lines from a GitHub PR patch.

    This is only a fallback when the complete file cannot
    be retrieved.
    """

    if not patch:
        return ""

    added_lines = []

    for line in patch.splitlines():

        # Do not treat the file header as source code.
        if line.startswith("+++"):
            continue

        if line.startswith("+"):
            added_lines.append(
                line[1:]
            )

    return "\n".join(
        added_lines
    )


# ============================================================
# GITHUB AUTHENTICATION
# ============================================================

def get_installation_access_token():
    """
    Create a short-lived GitHub App installation token.
    """

    installation = get_first_installation()

    installation_id = installation["id"]

    token_data = create_installation_token(
        installation_id
    )

    return token_data["token"]


def get_github_headers(access_token):
    """
    Create GitHub API request headers.
    """

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


# ============================================================
# RETRIEVE COMPLETE FILE USING GITHUB raw_url
# ============================================================

def get_file_from_pr(
    file_data,
    access_token
):
    """
    Retrieve the complete file content using the raw_url
    returned by GitHub's Pull Request Files API.

    This is preferable to manually constructing a Contents
    API URL because GitHub has already identified the exact
    file/version associated with the PR.
    """

    raw_url = file_data.get(
        "raw_url"
    )

    filename = file_data.get(
        "filename",
        "unknown"
    )

    if not raw_url:

        print(
            f"No raw_url available for {filename}."
        )

        return None

    headers = get_github_headers(
        access_token
    )

    try:

        response = requests.get(
            raw_url,
            headers=headers,
            timeout=30
        )

    except requests.RequestException as error:

        print(
            f"Network error while retrieving "
            f"{filename}:"
        )

        print(error)

        return None

    if response.status_code != 200:

        print(
            f"Could not retrieve complete file "
            f"'{filename}'."
        )

        print(
            f"GitHub response: "
            f"{response.status_code}"
        )

        return None

    try:

        return response.text

    except Exception as error:

        print(
            f"Could not decode '{filename}':"
        )

        print(error)

        return None


# ============================================================
# PR PATCH LINE PARSER
# ============================================================

def get_changed_lines_from_patch(patch):
    """
    Return the NEW-file line numbers that were added
    or changed in a GitHub PR.

    Example:

        @@ -10,5 +20,7 @@

    means the new file starts at line 20 for that hunk.
    """

    if not patch:
        return set()

    changed_lines = set()

    new_file_line = None

    for raw_line in patch.splitlines():

        # ----------------------------------------------------
        # Hunk header
        # ----------------------------------------------------

        if raw_line.startswith("@@"):

            match = re.search(
                r"\+(\d+)(?:,\d+)?",
                raw_line
            )

            if match:

                new_file_line = int(
                    match.group(1)
                )

            continue

        # ----------------------------------------------------
        # File header
        # ----------------------------------------------------

        if raw_line.startswith("+++"):
            continue

        if new_file_line is None:
            continue

        # ----------------------------------------------------
        # Added line
        # ----------------------------------------------------

        if raw_line.startswith("+"):

            changed_lines.add(
                new_file_line
            )

            new_file_line += 1

            continue

        # ----------------------------------------------------
        # Deleted line
        # ----------------------------------------------------

        if raw_line.startswith("-"):

            # Deleted lines do not exist in the new file.
            continue

        # ----------------------------------------------------
        # Context line
        # ----------------------------------------------------

        new_file_line += 1

    return changed_lines


# ============================================================
# FIND LINE NUMBER IN AI FINDING
# ============================================================

def get_issue_line(issue):
    """
    Extract a line number from an AI finding.

    Supports structured findings:

        {
            "line": 714
        }

    and textual findings:

        "Problem found at line 714"
    """

    if isinstance(
        issue,
        dict
    ):

        possible_keys = [
            "line",
            "line_number",
            "lineno",
            "lineNumber",
        ]

        for key in possible_keys:

            value = issue.get(
                key
            )

            if value is None:
                continue

            try:

                return int(
                    value
                )

            except (
                TypeError,
                ValueError
            ):

                pass

    if isinstance(
        issue,
        str
    ):

        patterns = [
            r"\bline\s*[:#]?\s*(\d+)\b",
            r"\bline_number\s*[:=]\s*(\d+)\b",
            r"\blineno\s*[:=]\s*(\d+)\b",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                issue,
                re.IGNORECASE
            )

            if match:

                return int(
                    match.group(1)
                )

    return None


# ============================================================
# FORMAT AI FINDING
# ============================================================

def format_issue(issue):
    """
    Convert an AI finding into GitHub Markdown.
    """

    if isinstance(
        issue,
        dict
    ):

        title = issue.get(
            "title",
            "AI detected an issue"
        )

        severity = issue.get(
            "severity",
            "Not specified"
        )

        confidence = issue.get(
            "confidence",
            "Not specified"
        )

        why = issue.get(
            "why",
            issue.get(
                "message",
                ""
            )
        )

        risk = issue.get(
            "risk",
            ""
        )

        recommendation = issue.get(
            "recommendation",
            issue.get(
                "suggestion",
                ""
            )
        )

        result = (
            f"### {title}\n\n"
            f"**Severity:** {severity}\n\n"
            f"**Confidence:** {confidence}\n\n"
        )

        if why:

            result += (
                f"**Why:** {why}\n\n"
            )

        if risk:

            result += (
                f"**Risk:** {risk}\n\n"
            )

        if recommendation:

            result += (
                f"**Recommendation:** "
                f"{recommendation}\n\n"
            )

        return result

    return f"- {issue}\n\n"


# ============================================================
# BUILD OVERALL GITHUB REVIEW
# ============================================================

def build_github_review(
    repository_name,
    pull_number,
    reviews
):
    """
    Build the overall Markdown review.
    """

    body = ""

    body += (
        "# 🤖 AI Code Review\n\n"
    )

    body += (
        "> This review was generated by "
        "**AI Code Reviewer**.\n"
        "> It is advisory and does not replace "
        "human approval.\n\n"
    )

    body += "---\n\n"

    body += (
        "## 📋 Review Summary\n\n"
    )

    body += (
        f"**Repository:** `{repository_name}`\n\n"
    )

    body += (
        f"**Pull Request:** `#{pull_number}`\n\n"
    )

    body += (
        f"**Files reviewed:** `{len(reviews)}`\n\n"
    )

    total_errors = 0
    total_suggestions = 0

    for item in reviews:

        review = item.get(
            "review",
            {}
        )

        total_errors += len(
            review.get(
                "errors",
                []
            )
        )

        total_suggestions += len(
            review.get(
                "suggestions",
                []
            )
        )

    body += (
        f"**Issues detected:** "
        f"`{total_errors}`\n\n"
    )

    body += (
        f"**Suggestions:** "
        f"`{total_suggestions}`\n\n"
    )

    body += "---\n\n"

    # --------------------------------------------------------
    # File-by-file results
    # --------------------------------------------------------

    for item in reviews:

        filename = item[
            "filename"
        ]

        language = item[
            "language"
        ]

        review = item[
            "review"
        ]

        errors = review.get(
            "errors",
            []
        )

        suggestions = review.get(
            "suggestions",
            []
        )

        quality_score = review.get(
            "quality_score"
        )

        rag_found = review.get(
            "rag_context_found"
        )

        body += (
            f"## 📄 `{filename}`\n\n"
        )

        body += (
            f"**Language:** `{language}`\n\n"
        )

        if quality_score is not None:

            body += (
                f"**Quality Score:** "
                f"`{quality_score}/10`\n\n"
            )

        body += (
            f"**Repository Context Used:** "
            f"`{rag_found}`\n\n"
        )

        # ----------------------------------------------------
        # Errors
        # ----------------------------------------------------

        if errors:

            body += (
                "### 🔴 Issues Found\n\n"
            )

            for error in errors:

                body += format_issue(
                    error
                )

        else:

            body += (
                "### 🟢 Issues Found\n\n"
                "No direct issues were detected "
                "by the AI reviewer.\n\n"
            )

        # ----------------------------------------------------
        # Suggestions
        # ----------------------------------------------------

        if suggestions:

            body += (
                "### 💡 Suggestions\n\n"
            )

            for suggestion in suggestions:

                body += format_issue(
                    suggestion
                )

        # ----------------------------------------------------
        # AI agent results
        # ----------------------------------------------------

        agents = review.get(
            "agents",
            {}
        )

        if agents:

            body += (
                "### 🧠 AI Agent Results\n\n"
            )

            for agent_key, agent_data in agents.items():

                if not isinstance(
                    agent_data,
                    dict
                ):
                    continue

                agent_name = agent_data.get(
                    "name",
                    agent_key
                )

                status = agent_data.get(
                    "status",
                    "Unknown"
                )

                body += (
                    f"- **{agent_name}:** "
                    f"{status}\n"
                )

            body += "\n"

        body += "---\n\n"

    # --------------------------------------------------------
    # Human-in-the-loop requirement
    # --------------------------------------------------------

    body += (
        "## 👤 Human Review Required\n\n"
    )

    body += (
        "AI findings are **advisory only**. "
        "A human developer should verify the findings "
        "before making changes or approving the Pull Request.\n\n"
    )

    body += (
        "Generated by **AI Code Reviewer** 🚀"
    )

    return body


# ============================================================
# POST INLINE FINDINGS
# ============================================================

def post_inline_comments(
    owner,
    repo_name,
    pull_number,
    commit_id,
    reviews
):
    """
    Post eligible AI findings as inline GitHub comments.

    An inline comment is created only when:

    1. AI provides a line number.
    2. The line exists in the new file.
    3. The line was actually changed by the PR.
    """

    print()
    print(
        "Posting inline AI findings..."
    )

    posted_count = 0
    skipped_count = 0

    for item in reviews:

        filename = item[
            "filename"
        ]

        review = item[
            "review"
        ]

        changed_lines = item.get(
            "changed_lines",
            set()
        )

        errors = review.get(
            "errors",
            []
        )

        for finding in errors:

            ai_line = get_issue_line(
                finding
            )

            # ------------------------------------------------
            # No line number
            # ------------------------------------------------

            if ai_line is None:

                print(
                    f"Skipping inline comment for "
                    f"{filename}: no line number."
                )

                skipped_count += 1

                continue

            # ------------------------------------------------
            # Ensure line belongs to PR diff
            # ------------------------------------------------

            if ai_line not in changed_lines:

                print(
                    f"Skipping inline comment for "
                    f"{filename}:{ai_line} "
                    f"(line was not changed in the PR)."
                )

                skipped_count += 1

                continue

            # ------------------------------------------------
            # Build inline comment
            # ------------------------------------------------

            inline_body = (
                "## 🤖 ReviewX AI Finding\n\n"
                "This finding is **advisory** and "
                "requires human verification.\n\n"
                f"{format_issue(finding)}"
            )

            try:

                post_inline_review_comment(
                    owner=owner,
                    repo=repo_name,
                    pull_number=pull_number,
                    commit_id=commit_id,
                    path=filename,
                    line=ai_line,
                    body=inline_body,
                    side="RIGHT",
                )

                print(
                    f"Inline comment posted: "
                    f"{filename}:{ai_line}"
                )

                posted_count += 1

            except Exception as error:

                print(
                    f"Failed to post inline comment "
                    f"for {filename}:{ai_line}"
                )

                print(
                    error
                )

    print()

    print(
        f"Inline comments posted: "
        f"{posted_count}"
    )

    print(
        f"Inline comments skipped: "
        f"{skipped_count}"
    )

    return posted_count


# ============================================================
# MAIN PR REVIEW PIPELINE
# ============================================================

def review_pull_request():

    print()
    print(
        "=========================================="
    )

    print(
        "AI GITHUB PULL REQUEST REVIEW"
    )

    print(
        "=========================================="
    )

    print()

    # ========================================================
    # 1. GitHub App installation
    # ========================================================

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
        account.get(
            "login"
        )
    )

    # ========================================================
    # 2. Get repositories
    # ========================================================

    print()
    print(
        "Getting repositories..."
    )

    repository_data = get_repositories()

    repositories = repository_data.get(
        "repositories",
        []
    )

    if not repositories:

        print(
            "No repositories found."
        )

        return

    repository = repositories[0]

    full_name = repository[
        "full_name"
    ]

    owner, repo_name = full_name.split(
        "/",
        1
    )

    print(
        "Using repository:",
        full_name
    )

    # ========================================================
    # 3. Get open Pull Requests
    # ========================================================

    print()
    print(
        "Getting open Pull Requests..."
    )

    pull_requests = get_pull_requests(
        owner,
        repo_name
    )

    if not pull_requests:

        print(
            "No open Pull Requests found."
        )

        return

    # ========================================================
    # 4. Select first PR
    # ========================================================

    pull_request = pull_requests[0]

    pull_number = pull_request[
        "number"
    ]

    pull_title = pull_request[
        "title"
    ]

    head_data = pull_request.get(
        "head",
        {}
    )

    commit_id = head_data.get(
        "sha"
    )

    print()

    print(
        f"Selected Pull Request: "
        f"#{pull_number}"
    )

    print(
        "Title:",
        pull_title
    )

    print(
        "Commit:",
        commit_id
    )

    # ========================================================
    # 5. Create installation token
    # ========================================================

    print()
    print(
        "Creating GitHub installation token..."
    )

    try:

        access_token = (
            get_installation_access_token()
        )

    except Exception as error:

        print(
            "Could not create installation token:"
        )

        print(
            error
        )

        return

    print(
        "Installation token created."
    )

    # ========================================================
    # 6. Get changed PR files
    # ========================================================

    print()
    print(
        "Getting changed files..."
    )

    changed_files = get_pull_request_files(
        owner,
        repo_name,
        pull_number
    )

    print(
        f"Found {len(changed_files)} "
        "changed file(s)."
    )

    all_reviews = []

    # ========================================================
    # 7. Review each changed file
    # ========================================================

    for index, file_data in enumerate(
        changed_files,
        start=1
    ):

        filename = file_data.get(
            "filename",
            "unknown"
        )

        status = file_data.get(
            "status",
            "unknown"
        )

        patch = file_data.get(
            "patch",
            ""
        )

        print()
        print(
            "------------------------------------------"
        )

        print(
            f"FILE {index}: {filename}"
        )

        print(
            "------------------------------------------"
        )

        print(
            "Status:",
            status
        )

        print(
            "Additions:",
            file_data.get(
                "additions",
                0
            )
        )

        print(
            "Deletions:",
            file_data.get(
                "deletions",
                0
            )
        )

        # ----------------------------------------------------
        # Ignore files without a textual patch
        # ----------------------------------------------------

        if not patch:

            print(
                "No patch available."
            )

            print(
                "Skipping this file."
            )

            continue

        # ----------------------------------------------------
        # Calculate changed lines
        # ----------------------------------------------------

        changed_lines = (
            get_changed_lines_from_patch(
                patch
            )
        )

        print(
            "Changed lines:",
            sorted(
                changed_lines
            )
        )

        # ----------------------------------------------------
        # Retrieve COMPLETE file using raw_url
        # ----------------------------------------------------

        print()
        print(
            "Getting complete file from GitHub..."
        )

        full_file_code = get_file_from_pr(
            file_data=file_data,
            access_token=access_token
        )

        # ----------------------------------------------------
        # Fallback
        # ----------------------------------------------------

        if not full_file_code:

            print()
            print(
                "Complete file could not be retrieved."
            )

            print(
                "Using PR diff as fallback."
            )

            full_file_code = extract_added_code(
                patch
            )

        # ----------------------------------------------------
        # Verify code exists
        # ----------------------------------------------------

        if not full_file_code.strip():

            print(
                "No source code available."
            )

            continue

        # ----------------------------------------------------
        # Detect language
        # ----------------------------------------------------

        language = detect_language(
            filename
        )

        print(
            "Detected language:",
            language
        )

        print(
            "Lines sent to AI:",
            len(
                full_file_code.splitlines()
            )
        )

        # ----------------------------------------------------
        # AI review
        # ----------------------------------------------------

        print()
        print(
            "Sending COMPLETE file "
            "to AI reviewer..."
        )

        try:

            review_result = review_code(
                code=full_file_code,
                language=language,
                project_name=full_name
            )

            all_reviews.append(
                {
                    "filename": filename,
                    "language": language,
                    "review": review_result,
                    "changed_lines": changed_lines,
                }
            )

            print(
                "AI review completed."
            )

        except Exception as error:

            print()
            print(
                "AI review failed:"
            )

            print(
                error
            )

    # ========================================================
    # 8. Check review results
    # ========================================================

    if not all_reviews:

        print()
        print(
            "No files could be reviewed."
        )

        return

    # ========================================================
    # 9. Build GitHub review
    # ========================================================

    print()
    print(
        "Building GitHub review..."
    )

    review_body = build_github_review(
        repository_name=full_name,
        pull_number=pull_number,
        reviews=all_reviews
    )

    # ========================================================
    # 10. Post overall review
    # ========================================================

    print()
    print(
        "Posting AI review to GitHub..."
    )

    try:

        posted_review = post_pull_request_review(
            owner,
            repo_name,
            pull_number,
            review_body
        )

        review_id = posted_review.get(
            "id"
        )

        print()
        print(
            "=========================================="
        )

        print(
            "AI REVIEW POSTED SUCCESSFULLY!"
        )

        print(
            "=========================================="
        )

        print()

        print(
            "GitHub Review ID:",
            review_id
        )

        print(
            "Pull Request:",
            f"#{pull_number}"
        )

        print(
            "Repository:",
            full_name
        )

    except Exception as error:

        print()
        print(
            "Failed to post review to GitHub:"
        )

        print(
            error
        )

    # ========================================================
    # 11. Inline comments
    # ========================================================

    if not commit_id:

        print()
        print(
            "Cannot post inline comments because "
            "the Pull Request commit SHA was not found."
        )

        return

    post_inline_comments(
        owner=owner,
        repo_name=repo_name,
        pull_number=pull_number,
        commit_id=commit_id,
        reviews=all_reviews
    )

    # ========================================================
    # 12. Complete
    # ========================================================

    print()
    print(
        "=========================================="
    )

    print(
        "AI GITHUB REVIEW COMPLETE"
    )

    print(
        "=========================================="
    )

    print()

    print(
        "The AI reviewed the available complete files."
    )

    print(
        "Inline comments are restricted to "
        "PR-changed lines."
    )

    print(
        "Human approval is still required."
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    review_pull_request()