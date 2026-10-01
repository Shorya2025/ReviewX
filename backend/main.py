import ast
import builtins
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
import requests

try:
    from backend.rag_engine import query_repository_context
except ImportError:
    from rag_engine import query_repository_context

# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder:latest")


# ============================================================
# HEALTH CHECK
# ============================================================

def ollama_is_running() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1.5)
        return resp.status_code == 200
    except Exception:
        return False


# ============================================================
# MULTI-LANGUAGE SYNTAX & STATIC COMPILER CHECK
# ============================================================

def validate_javascript_syntax(code: str) -> list:
    node_bin = shutil.which("node")
    if not node_bin:
        return []

    errors = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_js = os.path.join(temp_dir, "syntax_check.js")
        with open(temp_js, "w", encoding="utf-8") as f:
            f.write(code)

        proc = subprocess.run(
            [node_bin, "--check", temp_js],
            capture_output=True,
            text=True,
            timeout=4
        )
        if proc.returncode != 0:
            err_msg = proc.stderr.strip()
            clean_msg = re.sub(r'[\w\-\\:]+syntax_check\.js:\d+', 'Line error:', err_msg)
            first_line = clean_msg.splitlines()[0] if clean_msg.splitlines() else err_msg
            errors.append(f"JavaScript SyntaxError: {first_line}")

    return errors


def agent_syntax_and_casing(code: str, language: str) -> list:
    lang = language.lower()
    errors = []

    if lang in ["javascript", "typescript"]:
        return validate_javascript_syntax(code)

    if lang != "python":
        return errors

    has_curly_braces = bool(re.search(r'[{}]', code))
    
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        if has_curly_braces:
            errors.append(
                f"SyntaxError at line {e.lineno}: C-style curly braces '{{' '}}' detected in Python. "
                "Python uses colons ':' and indentation instead of braces."
            )
        else:
            errors.append(f"SyntaxError at line {e.lineno}: {e.msg}")
        return errors

    all_builtins = dir(builtins)
    builtin_exact = set(all_builtins)
    builtin_lower_map = {b.lower(): b for b in all_builtins}
    defined_symbols = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_symbols[node.name.lower()] = (node.name, node.lineno)
            for arg in node.args.args:
                defined_symbols[arg.arg.lower()] = (arg.arg, node.lineno)

        elif isinstance(node, ast.ClassDef):
            defined_symbols[node.name.lower()] = (node.name, node.lineno)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        defined_symbols[sub.id.lower()] = (sub.id, node.lineno)

        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined_symbols[node.target.id.lower()] = (node.target.id, node.lineno)

        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    defined_symbols[sub.id.lower()] = (sub.id, node.lineno)

        elif isinstance(node, ast.comprehension):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    defined_symbols[sub.id.lower()] = (sub.id, node.lineno)

        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars:
                    for sub in ast.walk(item.optional_vars):
                        if isinstance(sub, ast.Name):
                            defined_symbols[sub.id.lower()] = (sub.id, node.lineno)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                defined_symbols[name.lower()] = (name, node.lineno)

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                defined_symbols[name.lower()] = (name, node.lineno)

    exact_defined = {val[0] for val in defined_symbols.values()}

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_name = node.id
            if used_name in builtin_exact or used_name in exact_defined:
                continue

            lower_used = used_name.lower()
            if lower_used in builtin_lower_map:
                correct_builtin = builtin_lower_map[lower_used]
                if used_name != correct_builtin:
                    errors.append(
                        f"Line {node.lineno}: Case-sensitivity NameError: '{used_name}' is not defined. "
                        f"Did you mean built-in function '{correct_builtin}()'? Python is strictly case-sensitive."
                    )
                continue

            if lower_used in defined_symbols:
                orig_name, orig_line = defined_symbols[lower_used]
                if used_name != orig_name:
                    errors.append(
                        f"Line {node.lineno}: Case-sensitivity NameError: '{used_name}' is not defined. "
                        f"Did you mean '{orig_name}' (defined at line {orig_line})? Python is strictly case-sensitive."
                    )
                continue

            errors.append(f"Line {node.lineno}: NameError: '{used_name}' is not defined.")

    return errors


# ============================================================
# MULTI-LANGUAGE HEURISTIC SECURITY & OPTIMIZATION RULES
# ============================================================

def static_code_analysis_rules(code: str, language: str) -> list:
    suggestions = []
    lang = language.lower()

    if lang in ["javascript", "typescript"]:
        if re.search(r'(SELECT|INSERT|UPDATE|DELETE).*?\+\s*[\w\.]+', code, re.IGNORECASE):
            suggestions.append(
                "Critical Security Risk: Raw SQL query concatenation detected. Use parameterized queries or ORM binds to prevent SQL Injection."
            )

        if re.search(r'console\.log\(.*?(password|card|cvv|secret|token).*?\)', code, re.IGNORECASE):
            suggestions.append(
                "Compliance Risk: Possible logging of sensitive fields (credentials / card details) to stdout via console.log."
            )

        if "router." in code and not re.search(r'(const|let|var)\s+router\s*=', code):
            suggestions.append(
                "Reference Notice: 'router' is referenced without declaration. Ensure mock router or express instance is declared."
            )

    if lang == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "range":
                        if len(node.args) >= 2:
                            if isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                                try:
                                    bound_str = ast.unparse(node.args[1])
                                except Exception:
                                    bound_str = "N"
                                suggestions.append(
                                    f"Line {node.lineno}: Redundant '0' in range(0, ...). Simplify to 'range({bound_str})' for cleaner idiomatic Python."
                                )

                if isinstance(node, (ast.For, ast.AsyncFor)):
                    if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                        upper_bound = None
                        if len(node.iter.args) == 1 and isinstance(node.iter.args[0], ast.Constant):
                            upper_bound = node.iter.args[0].value
                        elif len(node.iter.args) >= 2 and isinstance(node.iter.args[1], ast.Constant):
                            upper_bound = node.iter.args[1].value

                        if upper_bound is not None and isinstance(node.target, ast.Name):
                            loop_var = node.target.id
                            for sub in node.body:
                                if isinstance(sub, ast.If):
                                    test = sub.test
                                    if isinstance(test, ast.Compare):
                                        if isinstance(test.left, ast.Name) and test.left.id == loop_var:
                                            for op, comp in zip(test.ops, test.comparators):
                                                if isinstance(op, (ast.Gt, ast.GtE)) and isinstance(comp, ast.Constant):
                                                    if isinstance(comp.value, (int, float)) and comp.value >= upper_bound:
                                                        suggestions.append(
                                                            f"Line {sub.lineno}: Dead Code / Unreachable Condition: '{loop_var}' runs from 0 to {upper_bound - 1}, so 'if {loop_var} > {comp.value}:' will NEVER execute."
                                                        )
        except Exception:
            pass

    return suggestions


# ============================================================
# CODE RUNNER / EXECUTION ENGINE
# ============================================================

def execute_code(code: str, language: str) -> dict:
    lang = language.lower()
    start_time = time.time()

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            if lang == "python":
                file_path = os.path.join(temp_dir, "script.py")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)

                proc = subprocess.run(
                    [sys.executable, file_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                duration = round(time.time() - start_time, 3)
                output = proc.stdout if proc.stdout else proc.stderr
                return {
                    "success": proc.returncode == 0,
                    "output": output.strip() if output else "[Process completed with no output]",
                    "exit_code": proc.returncode,
                    "execution_time": f"{duration}s"
                }

            elif lang in ["javascript", "typescript"]:
                node_bin = shutil.which("node")
                if not node_bin:
                    return {"success": False, "output": "Node.js runtime not installed on system.", "exit_code": 127, "execution_time": "0s"}
                file_path = os.path.join(temp_dir, "script.js")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)

                proc = subprocess.run([node_bin, file_path], capture_output=True, text=True, timeout=5)
                duration = round(time.time() - start_time, 3)
                output = proc.stdout if proc.stdout else proc.stderr
                return {
                    "success": proc.returncode == 0,
                    "output": output.strip() if output else "[Process completed with no output]",
                    "exit_code": proc.returncode,
                    "execution_time": f"{duration}s"
                }

            elif lang in ["c", "c++"]:
                compiler_name = "gcc" if lang == "c" else "g++"
                compiler = shutil.which(compiler_name)
                if not compiler:
                    return {"success": False, "output": f"{compiler_name} compiler not detected in system PATH.", "exit_code": 127, "execution_time": "0s"}
                
                ext = "c" if lang == "c" else "cpp"
                src_path = os.path.join(temp_dir, f"main.{ext}")
                bin_path = os.path.join(temp_dir, "out_bin.exe" if os.name == "nt" else "out_bin")
                with open(src_path, "w", encoding="utf-8") as f:
                    f.write(code)

                compile_proc = subprocess.run([compiler, src_path, "-o", bin_path], capture_output=True, text=True, timeout=6)
                if compile_proc.returncode != 0:
                    return {"success": False, "output": compile_proc.stderr.strip(), "exit_code": compile_proc.returncode, "execution_time": "0s"}

                run_proc = subprocess.run([bin_path], capture_output=True, text=True, timeout=5)
                duration = round(time.time() - start_time, 3)
                output = run_proc.stdout if run_proc.stdout else run_proc.stderr
                return {
                    "success": run_proc.returncode == 0,
                    "output": output.strip() if output else "[Process completed with no output]",
                    "exit_code": run_proc.returncode,
                    "execution_time": f"{duration}s"
                }

            elif lang == "java":
                javac_bin = shutil.which("javac")
                java_bin = shutil.which("java")
                if not javac_bin or not java_bin:
                    return {"success": False, "output": "JDK (javac/java) not detected in environment PATH.", "exit_code": 127, "execution_time": "0s"}

                match = re.search(r"public\s+class\s+([A-Za-z0-9_]+)", code)
                class_name = match.group(1) if match else "Main"
                src_path = os.path.join(temp_dir, f"{class_name}.java")
                with open(src_path, "w", encoding="utf-8") as f:
                    f.write(code)

                compile_proc = subprocess.run([javac_bin, src_path], capture_output=True, text=True, timeout=6)
                if compile_proc.returncode != 0:
                    return {"success": False, "output": compile_proc.stderr.strip(), "exit_code": compile_proc.returncode, "execution_time": "0s"}

                run_proc = subprocess.run([java_bin, "-cp", temp_dir, class_name], capture_output=True, text=True, timeout=5)
                duration = round(time.time() - start_time, 3)
                output = run_proc.stdout if run_proc.stdout else run_proc.stderr
                return {
                    "success": run_proc.returncode == 0,
                    "output": output.strip() if output else "[Process completed with no output]",
                    "exit_code": run_proc.returncode,
                    "execution_time": f"{duration}s"
                }

            return {
                "success": False,
                "output": f"Direct execution runner not supported for {language}.",
                "exit_code": -1,
                "execution_time": "0s"
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "Execution timed out (5s limit exceeded). Check for infinite loops.",
                "exit_code": 124,
                "execution_time": ">5s"
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Runtime execution error: {str(e)}",
                "exit_code": 1,
                "execution_time": "0s"
            }


# ============================================================
# LLM INFERENCE ENGINE (WITH REPOSITORY RAG CONTEXT)
# ============================================================

def safe_extract_json(raw_text: str) -> dict:
    if not raw_text:
        return {}
    cleaned = raw_text.strip()
    if "```" in cleaned:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned)
        if match:
            cleaned = match.group(1).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end+1])
        except Exception:
            pass
    return {}


def query_agent_raw(prompt: str, max_tokens: int = 250) -> dict:
    if not ollama_is_running():
        return {}
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": max_tokens,
                    "top_p": 0.8
                }
            },
            timeout=12
        )
        if resp.status_code == 200:
            return safe_extract_json(resp.json().get("response", "{}"))
    except Exception:
        pass
    return {}


def agent_security_review(code: str, language: str, repo_context: str = "") -> list:
    context_str = f"\nRepository Context:\n{repo_context[:1000]}" if repo_context else ""
    prompt = (
        f"Language: {language}\n"
        f"{context_str}\n"
        "Inspect strictly for security flaws, SQL injections, unprotected endpoints, memory leaks, or unhandled exceptions.\n"
        'Respond in JSON format: {"security_flaws": ["short flaw 1"]}\n'
        f"Code:\n{code[:2000]}"
    )
    res = query_agent_raw(prompt, max_tokens=180)
    flaws = res.get("security_flaws", [])
    return flaws if isinstance(flaws, list) else []


def agent_performance_review(code: str, language: str, repo_context: str = "") -> list:
    context_str = f"\nRepository Context:\n{repo_context[:1000]}" if repo_context else ""
    prompt = (
        f"Language: {language}\n"
        f"{context_str}\n"
        "Analyze algorithmic complexity, slow operations, redundant calls, or memory leaks.\n"
        'Respond in JSON format: {"optimizations": ["short tip 1"]}\n'
        f"Code:\n{code[:2000]}"
    )
    res = query_agent_raw(prompt, max_tokens=180)
    opts = res.get("optimizations", [])
    return opts if isinstance(opts, list) else []


def agent_judge_and_style(code: str, language: str, base_score: int, repo_context: str = "") -> dict:
    context_str = f"\nRepository Context:\n{repo_context[:1000]}" if repo_context else ""
    prompt = (
        f"Language: {language}\n"
        f"{context_str}\n"
        f"Review code architecture and conventions. Base score is {base_score}.\n"
        f'Respond in JSON format: {{"style_tips": ["short tip 1"], "quality_score": {base_score}}}\n'
        f"Code:\n{code[:2000]}"
    )
    res = query_agent_raw(prompt, max_tokens=150)
    style_tips = res.get("style_tips", [])
    if not isinstance(style_tips, list):
        style_tips = []
    score = res.get("quality_score", base_score)
    try:
        score = int(float(score))
    except Exception:
        score = base_score
    return {"style_tips": style_tips, "quality_score": score}


# ============================================================
# PIPELINE COORDINATOR WITH RUNTIME SYNC
# ============================================================

def review_code(code: str, language: str = "Python", project_name: str = "Default") -> dict:
    syntax_errors = agent_syntax_and_casing(code, language)
    static_suggestions = static_code_analysis_rules(code, language)

    repo_context = query_repository_context(code)

    run_result = None
    runtime_fatal_errors = []

    if not syntax_errors:
        run_result = execute_code(code, language)
        if run_result and not run_result.get("success", False):
            raw_err = run_result.get("output", "")
            err_lines = [l.strip() for l in raw_err.splitlines() if l.strip()]
            ref_err = next((l for l in err_lines if "Error:" in l), None)
            display_err = ref_err if ref_err else (err_lines[-1] if err_lines else "Runtime Execution Crash")
            runtime_fatal_errors.append(f"Runtime Crash ({run_result.get('execution_time')}): {display_err}")
    else:
        run_result = {
            "success": False,
            "output": "Execution blocked: Resolve critical syntax or scoping errors first.",
            "exit_code": 1,
            "execution_time": "0s"
        }

    all_initial_errors = syntax_errors + runtime_fatal_errors

    base_score = 10
    base_score -= min(6, len(all_initial_errors) * 3)
    base_score -= min(4, len(static_suggestions) * 2)
    base_score = max(1, base_score)
    quality_score = base_score

    security_issues = []
    perf_tips = []
    style_tips = []

    if ollama_is_running():
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                sec_future = executor.submit(agent_security_review, code, language, repo_context)
                perf_future = executor.submit(agent_performance_review, code, language, repo_context)
                judge_future = executor.submit(agent_judge_and_style, code, language, base_score, repo_context)

                security_issues = sec_future.result() or []
                perf_tips = perf_future.result() or []
                judge_data = judge_future.result() or {}
                style_tips = judge_data.get("style_tips", [])
                quality_score = judge_data.get("quality_score", base_score)
        except Exception:
            pass

    all_errors = list(dict.fromkeys(all_initial_errors + security_issues))
    all_suggestions = list(dict.fromkeys(static_suggestions + perf_tips + style_tips))
    quality_score = max(1, min(10, quality_score - len(security_issues) * 2))

    agent_report = {
        "syntax_agent": {
            "name": f"{language} Syntax & Scope Agent",
            "issues": all_initial_errors,
            "status": "Passed" if not all_initial_errors else "Flagged"
        },
        "security_agent": {
            "name": "Security & Vulnerability Agent",
            "issues": security_issues,
            "status": "Clean" if not security_issues else "Risk Detected"
        },
        "performance_agent": {
            "name": "Performance & Optimization Agent",
            "tips": perf_tips,
            "status": "Optimal" if not perf_tips else f"{len(perf_tips)} Issues Found"
        },
        "judge_agent": {
            "name": "Style & Architecture Judge",
            "tips": style_tips,
            "score": quality_score
        }
    }

    return {
        "project_name": project_name,
        "language": language,
        "errors": all_errors,
        "suggestions": all_suggestions,
        "quality_score": quality_score,
        "execution": run_result,
        "rag_context_found": bool(repo_context.strip()),
        "agents": agent_report
    }


# ============================================================
# REFACTOR ENGINE
# ============================================================

def clean_python_syntax(code: str) -> str:
    lines = code.splitlines()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped == "}":
            continue
        if line.rstrip().endswith("{"):
            line = line.rstrip()[:-1].rstrip()
            if not line.endswith(":"):
                line += ":"
        elif "}" in line and not any(q in line for q in ['"', "'"]):
            line = line.replace("}", "")
        clean_lines.append(line)
    
    fixed_lines = []
    for l in clean_lines:
        s = l.strip()
        if re.match(r'^(for\s+.*|if\s+.*|while\s+.*|def\s+.*|class\s+.*|elif\s+.*|else|try|except.*|finally)$', s):
            if not s.endswith(":"):
                l = l + ":"
        fixed_lines.append(l)
    return "\n".join(fixed_lines)


def remove_dead_code_branches(code: str, issue_text: str) -> str:
    match = re.search(r"Line (\d+): Dead Code.*?'if (\w+)\s*>\s*(\d+):'", issue_text)
    if not match:
        match = re.search(r"Line (\d+): Dead Code", issue_text)
    
    lines = code.splitlines()
    if match:
        target_line_idx = int(match.group(1)) - 1
        if 0 <= target_line_idx < len(lines):
            target_line = lines[target_line_idx]
            base_indent = len(target_line) - len(target_line.lstrip())
            
            if target_line.strip().startswith("if "):
                new_lines = []
                skip = False
                for idx, line in enumerate(lines):
                    if idx == target_line_idx:
                        skip = True
                        continue
                    if skip:
                        cur_indent = len(line) - len(line.lstrip())
                        if line.strip() and cur_indent <= base_indent:
                            skip = False
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                return "\n".join(new_lines)
    return code


def apply_fixes_to_code(code: str, language: str, issues_to_fix: list) -> str:
    if not issues_to_fix:
        return code

    patched_code = code
    lang = language.lower()

    # 1. Python Deterministic Patches
    if lang == "python":
        patched_code = clean_python_syntax(patched_code)

    # 2. JavaScript Deterministic Mocks & Patches (Bina npm install ke standalone chalane ke liye)
    if lang in ["javascript", "typescript"]:
        # Agar express missing hai ya router declared nahi hai toh clean mock inject karo
        if any("Cannot find module 'express'" in str(i) for i in issues_to_fix) or ("router." in patched_code and "const router" not in patched_code):
            patched_code = re.sub(r"const\s+express\s*=\s*require\(['\"]express['\"]\);\s*", "", patched_code)
            patched_code = re.sub(r"const\s+router\s*=\s*express\.Router\(\);\s*", "", patched_code)

            mock_header = (
                "// Standalone Runtime Mock for Router & Database\n"
                "const router = {\n"
                "    post: (path, handler) => {\n"
                "        console.log(`[POST ${path}] Route configured and executed successfully.`);\n"
                "        const req = { body: { items: ['itemA'], taxRate: 0.1, discountCode: 'SAVE20', cardNumber: '4111-XXXX-XXXX-1111' } };\n"
                "        const res = { json: (data) => console.log('[Response Sent]:', data) };\n"
                "        handler(req, res);\n"
                "    }\n"
                "};\n"
                "const db = { raw: async () => [{ id: 1, discount: 20 }] };\n"
                "const calculateTotal = (items, taxRate, discountCode) => 100;\n\n"
            )
            patched_code = mock_header + patched_code.strip()

        # Fix SQL Injection to Parameterized query
        patched_code = re.sub(
            r'SELECT\s+\*\s+FROM\s+(\w+)\s+WHERE\s+(\w+)\s*=\s*[\'"][^\'"]*[\'"]\s*\+\s*(\w+)\s*\+\s*[\'"][^\'"]*[\'"]',
            r"SELECT * FROM \1 WHERE \2 = ?",
            patched_code
        )

    # 3. Universal Rule Substitutions
    for issue in issues_to_fix:
        if not isinstance(issue, str):
            continue

        if "Dead Code" in issue or "Unreachable Condition" in issue:
            patched_code = remove_dead_code_branches(patched_code, issue)

        if "Redundant '0' in range(0," in issue:
            patched_code = re.sub(r"\brange\s*\(\s*0\s*,\s*", "range(", patched_code)

        # Built-in casing auto-fix
        match_b = re.search(r"['\"](\w+)['\"].*?built-in function ['\"](\w+)\(\)['\"]", issue)
        if match_b:
            patched_code = re.sub(rf"\b{re.escape(match_b.group(1))}\b", match_b.group(2), patched_code)

        # Variable casing auto-fix
        match_u = re.search(r"['\"](\w+)['\"].*?Did you mean ['\"](\w+)['\"]", issue)
        if match_u:
            patched_code = re.sub(rf"\b{re.escape(match_u.group(1))}\b", match_u.group(2), patched_code)
    if not ollama_is_running():
        return patched_code

    # 4. LLM-Guided Deep Patching
    issues_str = "\n".join([f"- {issue}" for issue in issues_to_fix if isinstance(issue, str)])
    prompt = (
        f"Language: {language}\n"
        f"Issues to fix:\n{issues_str}\n\n"
        f"Source Code:\n{patched_code}\n\n"
        "Return ONLY the fixed source code. No explanations, no markdown ticks."
    )

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.05, "num_predict": 700}
            },
            timeout=18
        )
        if resp.status_code == 200:
            llm_patched = resp.json().get("response", "").strip()
            if "```" in llm_patched:
                match = re.search(r'```(?:[a-zA-Z0-9_+-]+)?\s*([\s\S]*?)\s*```', llm_patched)
                if match:
                    llm_patched = match.group(1).strip()
            return llm_patched if llm_patched else patched_code
    except Exception as e:
        print(f"Error applying patch: {e}")

    return patched_code