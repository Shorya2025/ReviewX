from github_api import (
    get_first_installation,
    get_repositories,
    get_pull_requests,
    create_pull_request_summary_comment,
)


def main():
    print("=" * 60)
    print("ReviewX - GitHub PR Comment Test")
    print("=" * 60)

    # 1. Get GitHub App installation
    installation = get_first_installation()

    if not installation:
        print("ERROR: No GitHub App installation found.")
        return

    print(f"Installation ID: {installation['id']}")
    print(f"Account: {installation['account']['login']}")

    # 2. Get repositories
    repositories = get_repositories()

    # GitHub API may return repositories inside a dictionary
    if isinstance(repositories, dict):
        repositories = repositories.get("repositories", [])

    if not repositories:
        print("ERROR: No repositories found.")
        return

    repository = repositories[0]

    owner = repository["owner"]["login"]
    repo = repository["name"]

    print(f"Repository: {owner}/{repo}")

    # 3. Get open Pull Requests
    pull_requests = get_pull_requests(owner, repo, state="open")

    if not pull_requests:
        print("ERROR: No open Pull Request found.")
        print("Create an open Pull Request first.")
        return

    # Use the first open PR
    pull_request = pull_requests[0]

    pull_number = pull_request["number"]

    print(f"Pull Request: #{pull_number}")
    print(f"Title: {pull_request['title']}")

    # 4. Create a visible comment on the PR
    comment_body = """## 🤖 ReviewX AI Code Review

GitHub integration is working successfully.

This comment was posted automatically by **ReviewX** using the GitHub App.

### Integration Status

- ✅ GitHub App authentication
- ✅ Repository access
- ✅ Pull Request access
- ✅ GitHub API connection
- ✅ PR comment creation

**Next step:** Connect the existing ReviewX AI review results to this GitHub PR comment.

> This is an integration test comment and does not represent an actual code-review finding.
"""

    comment = create_pull_request_summary_comment(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        body=comment_body,
    )

    print()
    print("=" * 60)

    if comment:
        print("SUCCESS!")
        print("=" * 60)
        print("Comment created successfully.")
        print(f"Comment ID: {comment.get('id')}")
        print(f"Comment URL: {comment.get('html_url')}")
    else:
        print("ERROR: Comment was not created.")


if __name__ == "__main__":
    main()