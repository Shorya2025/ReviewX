import json
import os
import re
import requests

from dotenv import load_dotenv


# ============================================================
# PROJECT / ENVIRONMENT
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ENV_FILE = os.path.join(
    PROJECT_ROOT,
    ".env"
)

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)


# ============================================================
# OLLAMA CONFIGURATION
# ============================================================

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5-coder:1.5b"
)


# ============================================================
# OLLAMA CONNECTION
# ============================================================

def ollama_is_running():
    """
    Check whether Ollama is running.
    """

    try:

        response = requests.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=5
        )

        return response.status_code == 200

    except requests.RequestException:

        return False


# ============================================================
# EXTRACT JSON FROM AI RESPONSE
# ============================================================

def extract_json_from_response(raw_response):
    """
    Try several methods to extract JSON from the AI response.
    """

    if not raw_response:
        return None

    raw_response = raw_response.strip()

    # --------------------------------------------------------
    # Method 1: Direct JSON
    # --------------------------------------------------------

    try:

        return json.loads(
            raw_response
        )

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Method 2: Remove markdown JSON fences
    # --------------------------------------------------------

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        raw_response,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    )

    try:

        return json.loads(
            cleaned.strip()
        )

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Method 3: Find JSON object inside response
    # --------------------------------------------------------

    start = raw_response.find("{")
    end = raw_response.rfind("}")

    if start != -1 and end != -1 and end > start:

        possible_json = raw_response[
            start:end + 1
        ]

        try:

            return json.loads(
                possible_json
            )

        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# EXTRACT CODE FROM TEXT
# ============================================================

def extract_code_from_text(raw_response):
    """
    Try to recover source code if the model returns
    code instead of the expected JSON structure.
    """

    if not raw_response:
        return ""

    # --------------------------------------------------------
    # Look for fenced code block
    # --------------------------------------------------------

    matches = re.findall(
        r"```(?:python|py|javascript|js|java|cpp|c|typescript|ts)?\s*\n?(.*?)```",
        raw_response,
        flags=re.IGNORECASE | re.DOTALL
    )

    if matches:

        longest = max(
            matches,
            key=len
        )

        return longest.strip()

    # --------------------------------------------------------
    # Look for common corrected-code labels
    # --------------------------------------------------------

    labels = [
        "corrected_code:",
        "corrected code:",
        "fixed_code:",
        "fixed code:",
        "solution:",
        "code:"
    ]

    lower_response = raw_response.lower()

    for label in labels:

        index = lower_response.find(
            label
        )

        if index != -1:

            code = raw_response[
                index + len(label):
            ].strip()

            if code:

                return code

    return ""


# ============================================================
# NORMALIZE AI RESULT
# ============================================================

def normalize_ai_result(
    raw_response
):
    """
    Convert different possible AI response formats
    into one consistent structure.
    """

    # --------------------------------------------------------
    # Try JSON first
    # --------------------------------------------------------

    parsed = extract_json_from_response(
        raw_response
    )

    if isinstance(
        parsed,
        dict
    ):

        corrected_code = (
            parsed.get(
                "corrected_code"
            )
            or parsed.get(
                "fixed_code"
            )
            or parsed.get(
                "code"
            )
            or ""
        )

        # ----------------------------------------------------
        # Sometimes the model puts code inside a nested field
        # ----------------------------------------------------

        if isinstance(
            corrected_code,
            dict
        ):

            corrected_code = (
                corrected_code.get(
                    "code",
                    ""
                )
            )

        if isinstance(
            corrected_code,
            str
        ):

            corrected_code = (
                corrected_code.strip()
            )

        else:

            corrected_code = ""

        if corrected_code:

            return {
                "success": True,
                "issue_summary": str(
                    parsed.get(
                        "issue_summary",
                        parsed.get(
                            "summary",
                            "Issue identified."
                        )
                    )
                ),
                "root_cause": str(
                    parsed.get(
                        "root_cause",
                        "See AI analysis."
                    )
                ),
                "fix_explanation": str(
                    parsed.get(
                        "fix_explanation",
                        parsed.get(
                            "explanation",
                            "The suggested code addresses the identified issue."
                        )
                    )
                ),
                "risk_level": str(
                    parsed.get(
                        "risk_level",
                        "UNKNOWN"
                    )
                ),
                "corrected_code": corrected_code
            }

    # --------------------------------------------------------
    # If JSON failed, try extracting code from raw response
    # --------------------------------------------------------

    extracted_code = extract_code_from_text(
        raw_response
    )

    if extracted_code:

        return {
            "success": True,
            "issue_summary": (
                "AI generated a corrected version "
                "of the source code."
            ),
            "root_cause": (
                "The issue was analyzed by the "
                "AI remediation agent."
            ),
            "fix_explanation": (
                "The generated code contains the "
                "suggested remediation."
            ),
            "risk_level": "UNKNOWN",
            "corrected_code": extracted_code
        }

    # --------------------------------------------------------
    # Nothing usable was returned
    # --------------------------------------------------------

    return {
        "success": False,
        "error": (
            "AI response did not contain "
            "recognizable corrected code."
        ),
        "raw_response": raw_response
    }


# ============================================================
# GENERATE AI FIX
# ============================================================

def generate_ai_fix(
    code,
    finding,
    language="python"
):
    """
    Generate a suggested fix for an AI-detected issue.
    """

    # --------------------------------------------------------
    # Convert finding to readable text
    # --------------------------------------------------------

    if isinstance(
        finding,
        dict
    ):

        finding_text = json.dumps(
            finding,
            indent=2
        )

    else:

        finding_text = str(
            finding
        )

    # --------------------------------------------------------
    # AI prompt
    # --------------------------------------------------------

    prompt = f"""
You are a code fixing agent.

Programming language:
{language}

Detected problem:
{finding_text}

Source code:
--------------------
{code}
--------------------

Your job is to fix ONLY the detected problem.

IMPORTANT:
- Return the COMPLETE corrected source code.
- Do not return only a small snippet.
- Do not omit unchanged lines.
- Do not explain the answer before the code.
- Do not use markdown.
- Return JSON only.

Use exactly these JSON keys:

{{
  "issue_summary": "short description",
  "root_cause": "why the problem happens",
  "fix_explanation": "what you changed",
  "risk_level": "LOW",
  "corrected_code": "COMPLETE corrected source code"
}}

The corrected_code value MUST contain the entire source file.
"""


    # --------------------------------------------------------
    # Check Ollama
    # --------------------------------------------------------

    if not ollama_is_running():

        return {
            "success": False,
            "error": (
                "Ollama is not running at "
                f"{OLLAMA_BASE_URL}"
            )
        }

    # --------------------------------------------------------
    # Send request
    # --------------------------------------------------------

    try:

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1
                }
            },
            timeout=180
        )

    except requests.RequestException as error:

        return {
            "success": False,
            "error": (
                f"Ollama request failed: {error}"
            )
        }

    # --------------------------------------------------------
    # Check HTTP response
    # --------------------------------------------------------

    if response.status_code != 200:

        return {
            "success": False,
            "error": (
                f"Ollama returned HTTP "
                f"{response.status_code}: "
                f"{response.text}"
            )
        }

    # --------------------------------------------------------
    # Parse Ollama response
    # --------------------------------------------------------

    try:

        response_data = response.json()

    except ValueError:

        return {
            "success": False,
            "error": (
                "Ollama returned invalid HTTP JSON."
            )
        }

    raw_result = response_data.get(
        "response",
        ""
    )

    if not raw_result:

        return {
            "success": False,
            "error": (
                "Ollama returned an empty response."
            )
        }

    # --------------------------------------------------------
    # Normalize result
    # --------------------------------------------------------

    result = normalize_ai_result(
        raw_result
    )

    # --------------------------------------------------------
    # Preserve raw response for debugging
    # --------------------------------------------------------

    if not result.get(
        "success",
        False
    ):

        result["model"] = OLLAMA_MODEL

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )

    print(
        "ReviewX AI Fix Generator Test"
    )

    print(
        "=========================================="
    )

    print()

    print(
        "Ollama URL:",
        OLLAMA_BASE_URL
    )

    print(
        "Ollama Model:",
        OLLAMA_MODEL
    )

    print()

    # --------------------------------------------------------
    # Test source code
    # --------------------------------------------------------

    test_code = """def calculate_total(price, quantity):
    total = price * quantity
    print("Total:", total)
    return total
"""

    # --------------------------------------------------------
    # Test finding
    # --------------------------------------------------------

    test_finding = {
        "title": "Missing input validation",
        "severity": "MEDIUM",
        "confidence": 0.91,
        "line": 1,
        "why": (
            "The function accepts price and quantity "
            "without validating their values."
        ),
        "risk": (
            "Invalid values could produce incorrect "
            "results."
        ),
        "recommendation": (
            "Validate the inputs before performing "
            "the calculation."
        )
    }

    print(
        "Checking Ollama..."
    )

    if not ollama_is_running():

        print()

        print(
            "ERROR: Ollama is not running."
        )

        print(
            "Start Ollama before running this test."
        )

        raise SystemExit(1)

    print(
        "Ollama connection: OK"
    )

    print()

    print(
        "Sending test issue to AI..."
    )

    result = generate_ai_fix(
        code=test_code,
        finding=test_finding,
        language="python"
    )

    print()

    if not result.get(
        "success",
        False
    ):

        print(
            "AI FIX GENERATION FAILED"
        )

        print()

        print(
            "Error:",
            result.get(
                "error",
                "Unknown error"
            )
        )

        # ----------------------------------------------------
        # Print raw response so we can diagnose the model
        # ----------------------------------------------------

        raw_response = result.get(
            "raw_response"
        )

        if raw_response:

            print()

            print(
                "RAW AI RESPONSE:"
            )

            print(
                "------------------------------------------"
            )

            print(
                raw_response
            )

            print(
                "------------------------------------------"
            )

    else:

        print(
            "AI FIX GENERATED SUCCESSFULLY!"
        )

        print()

        print(
            "Issue:"
        )

        print(
            result.get(
                "issue_summary"
            )
        )

        print()

        print(
            "Root Cause:"
        )

        print(
            result.get(
                "root_cause"
            )
        )

        print()

        print(
            "Fix Explanation:"
        )

        print(
            result.get(
                "fix_explanation"
            )
        )

        print()

        print(
            "Risk Level:",
            result.get(
                "risk_level"
            )
        )

        print()

        print(
            "Corrected Code:"
        )

        print(
            "------------------------------------------"
        )

        print(
            result.get(
                "corrected_code"
            )
        )

        print(
            "------------------------------------------"
        )

    print()