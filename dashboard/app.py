import html
import os
import sys
import streamlit as st

# ============================================================
# PATH SETUP
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

for path in [PROJECT_ROOT, CURRENT_DIR, os.path.join(PROJECT_ROOT, "backend")]:
    if path not in sys.path:
        sys.path.insert(0, path)

# ============================================================
# BACKEND & AUTH IMPORTS
# ============================================================

try:
    from backend.main import review_code, ollama_is_running, apply_fixes_to_code
    from backend.rag_engine import index_repository_from_zip
    from backend.auth import (
        init_db,
        register_user,
        authenticate_user,
        get_google_login_url,
        process_google_callback,
    )
except ImportError:
    from main import review_code, ollama_is_running, apply_fixes_to_code
    from rag_engine import index_repository_from_zip
    from auth import (
        init_db,
        register_user,
        authenticate_user,
        get_google_login_url,
        process_google_callback,
    )

init_db()

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="ReviewX | Autonomous Code Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# HIGH-END CYBER DESIGN SYSTEM & BULLETPROOF AUTH STYLING
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

button[data-testid="stDeployButton"],
.stDeployButton,
#MainMenu,
footer {
    display: none !important;
    visibility: hidden !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
    height: 2.2rem !important;
}

button[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] button {
    display: flex !important;
    visibility: visible !important;
    background: rgba(10, 14, 26, 0.85) !important;
    border: 1px solid rgba(139, 92, 246, 0.4) !important;
    border-radius: 10px !important;
    color: #38bdf8 !important;
    box-shadow: 0 0 16px rgba(124, 58, 237, 0.4) !important;
}

.stApp {
    background-color: #030508 !important;
    color: #f8fafc;
    overflow-x: hidden;
}

.cosmic-canvas {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 0;
    pointer-events: none;
    overflow: hidden;
}

.star-field-1 {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: 
        radial-gradient(1.5px 1.5px at 40px 60px, #ffffff, rgba(255,255,255,0)),
        radial-gradient(1.2px 1.2px at 150px 220px, #ffffff, rgba(255,255,255,0)),
        radial-gradient(1.8px 1.8px at 280px 90px, #ffffff, rgba(255,255,255,0)),
        radial-gradient(1.3px 1.3px at 420px 310px, #ffffff, rgba(255,255,255,0)),
        radial-gradient(2px 2px at 580px 180px, #ffffff, rgba(255,255,255,0));
    background-size: 550px 550px;
    animation: twinkleA 3.5s infinite ease-in-out;
}

.star-field-2 {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: 
        radial-gradient(1.8px 1.8px at 210px 380px, rgba(255, 255, 255, 1), transparent),
        radial-gradient(2.2px 2.2px at 510px 450px, rgba(255, 255, 255, 1), transparent),
        radial-gradient(2px 2px at 980px 220px, rgba(255, 255, 255, 1), transparent);
    background-size: 700px 700px;
    animation: twinkleB 4.8s infinite ease-in-out 1.2s;
}

.aurora-haze {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: 
        radial-gradient(circle at 15% 18%, rgba(124, 58, 237, 0.28) 0%, transparent 48%),
        radial-gradient(circle at 85% 22%, rgba(56, 189, 248, 0.22) 0%, transparent 48%),
        radial-gradient(circle at 50% 92%, rgba(147, 51, 234, 0.15) 0%, transparent 55%);
}

@keyframes twinkleA {
    0%, 100% { opacity: 0.25; transform: scale(0.98); }
    50% { opacity: 0.95; transform: scale(1.02); }
}

@keyframes twinkleB {
    0%, 100% { opacity: 0.85; }
    50% { opacity: 0.25; }
}

.block-container {
    position: relative;
    z-index: 1;
    max-width: 1540px;
    padding-top: 0.8rem !important;
    padding-bottom: 2rem !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(6, 9, 16, 0.96) 0%, rgba(3, 5, 8, 0.98) 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    backdrop-filter: blur(25px) !important;
    z-index: 10;
}

/* ========================================================
   CYBERPUNK GLASSMORPHISM AUTH CARD CONTAINER
======================================================== */
.cyber-auth-wrap {
    background: linear-gradient(170deg, rgba(13, 20, 42, 0.92) 0%, rgba(6, 10, 24, 0.98) 100%);
    border: 1px solid rgba(139, 92, 246, 0.45);
    border-radius: 26px;
    padding: 34px 28px 28px 28px;
    box-shadow: 
        0 30px 80px -15px rgba(0, 0, 0, 0.95),
        0 0 50px rgba(124, 58, 237, 0.25),
        inset 0 1px 0 rgba(255, 255, 255, 0.15);
    backdrop-filter: blur(40px);
    margin-bottom: 20px;
}

.auth-headline {
    text-align: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.auth-header-glow {
    font-size: 28px;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -0.8px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}

.auth-header-glow span.brand-grad {
    background: linear-gradient(135deg, #c084fc 0%, #818cf8 50%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 18px rgba(139, 92, 246, 0.7));
}

/* Tabs: Kill Red and Ensure Neon Glow */
div[data-testid="stHorizontalBlock"] button {
    border-radius: 12px !important;
    font-size: 13.5px !important;
    font-weight: 800 !important;
    padding: 10px 18px !important;
    transition: all 0.25s ease !important;
}

div[data-testid="stHorizontalBlock"] button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(167, 139, 250, 0.6) !important;
    box-shadow: 0 4px 20px rgba(124, 58, 237, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
}

div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
    background: rgba(15, 23, 42, 0.8) !important;
    color: #94a3b8 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
    color: #ffffff !important;
    border-color: rgba(139, 92, 246, 0.5) !important;
    background: rgba(26, 38, 70, 0.9) !important;
}

/* Form Container Inside Auth */
div[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* Deep Neon Input Fields */
div[data-testid="stTextInput"] {
    margin-bottom: 14px !important;
}

div[data-baseweb="input"] {
    background: linear-gradient(180deg, rgba(8, 14, 30, 0.95) 0%, rgba(5, 9, 20, 0.98) 100%) !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important;
    border-radius: 14px !important;
    box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.7) !important;
    transition: all 0.25s ease !important;
}

div[data-baseweb="input"]:focus-within {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 24px rgba(56, 189, 248, 0.45), inset 0 1px 3px rgba(0, 0, 0, 0.6) !important;
    background: rgba(11, 20, 42, 0.98) !important;
}

div[data-testid="stTextInput"] input {
    background: transparent !important;
    color: #f1f5f9 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 12px 16px !important;
}

div[data-testid="stTextInput"] input::placeholder {
    color: #475569 !important;
    font-weight: 400 !important;
}

div[data-testid="stTextInput"] label {
    color: #7dd3fc !important;
    font-size: 12.5px !important;
    font-weight: 800 !important;
    letter-spacing: 0.6px !important;
    margin-bottom: 6px !important;
}

/* Vibrant Submit Button */
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #7c3aed 0%, #6366f1 50%, #06b6d4 100%) !important;
    color: #ffffff !important;
    font-weight: 800 !important;
    font-size: 14px !important;
    letter-spacing: 0.5px !important;
    border-radius: 14px !important;
    border: none !important;
    padding: 13px 22px !important;
    box-shadow: 0 8px 28px rgba(99, 102, 241, 0.5), 0 0 25px rgba(56, 189, 248, 0.3) !important;
    transition: all 0.25s ease !important;
    margin-top: 10px !important;
}

div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 36px rgba(99, 102, 241, 0.7), 0 0 35px rgba(56, 189, 248, 0.5) !important;
}

/* High Contrast Crisp Google Button */
.google-auth-btn {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 12px !important;
    width: 100% !important;
    background: #ffffff !important;
    color: #0f172a !important;
    font-weight: 800 !important;
    font-size: 14px !important;
    padding: 12px 20px !important;
    border-radius: 14px !important;
    text-decoration: none !important;
    border: 1px solid #ffffff !important;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.65), 0 0 20px rgba(255, 255, 255, 0.2) !important;
    transition: all 0.25s ease !important;
    margin-top: 14px !important;
}

.google-auth-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.85), 0 0 25px rgba(56, 189, 248, 0.45) !important;
    background: #f8fafc !important;
}

/* 12-Feature Roadmap Matrix Cards */
.tool-matrix-card {
    background: linear-gradient(170deg, rgba(11, 16, 28, 0.85) 0%, rgba(6, 9, 16, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 16px 16px;
    min-height: 125px;
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.tool-matrix-card:hover {
    border-color: rgba(139, 92, 246, 0.45);
    transform: translateY(-2px);
    box-shadow: 0 10px 24px -10px rgba(0, 0, 0, 0.7), 0 0 18px rgba(124, 58, 237, 0.15);
}

.badge-live {
    font-size: 9.5px;
    font-weight: 800;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34d399;
    padding: 2px 7px;
    border-radius: 99px;
    text-transform: uppercase;
}

.badge-queued {
    font-size: 9.5px;
    font-weight: 800;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: #38bdf8;
    padding: 2px 7px;
    border-radius: 99px;
    text-transform: uppercase;
}

.terminal-window-header {
    background: linear-gradient(90deg, rgba(14, 20, 36, 0.95) 0%, rgba(8, 12, 22, 0.9) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-bottom: none;
    border-top-left-radius: 16px;
    border-top-right-radius: 16px;
    padding: 12px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.terminal-dots-box {
    display: flex;
    align-items: center;
    gap: 7px;
}

.window-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.w-red { background: #ef4444; }
.w-yellow { background: #f59e0b; }
.w-green { background: #10b981; }

.file-tab-badge {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 8px;
    padding: 3px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    gap: 6px;
}

div[data-testid="stTextArea"] textarea {
    background: #040711 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-top: none !important;
    border-bottom-left-radius: 16px !important;
    border-bottom-right-radius: 16px !important;
    color: #e2e8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13.5px !important;
    line-height: 1.7 !important;
    padding: 16px 20px !important;
}

.console-container {
    background: #020408;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    overflow: hidden;
    margin-top: 14px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
}

.console-header {
    background: linear-gradient(90deg, rgba(15, 23, 42, 0.95), rgba(8, 12, 22, 0.95));
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 10px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.console-body {
    padding: 14px 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.6;
    max-height: 220px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
}

.hud-main-container {
    background: linear-gradient(170deg, rgba(14, 20, 36, 0.92) 0%, rgba(6, 9, 16, 0.98) 100%);
    border: 1px solid rgba(139, 92, 246, 0.25);
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 30px 80px -20px rgba(0, 0, 0, 0.85);
}

.score-orb-wrapper {
    position: relative;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.metric-chip {
    background: rgba(18, 26, 47, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.cyber-card {
    background: rgba(10, 15, 28, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 12px;
}

.cyber-card-fatal {
    border-left: 5px solid #f43f5e;
    background: linear-gradient(90deg, rgba(244, 63, 94, 0.08) 0%, rgba(10, 15, 28, 0.75) 100%);
}

.cyber-card-warn {
    border-left: 5px solid #f59e0b;
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.08) 0%, rgba(10, 15, 28, 0.75) 100%);
}

.cyber-loader-container {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(3, 5, 8, 0.92);
    backdrop-filter: blur(20px);
    z-index: 999999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.loader-orb-ring {
    position: relative;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    border: 3px solid rgba(139, 92, 246, 0.15);
    border-top: 3px solid #38bdf8;
    border-right: 3px solid #818cf8;
    animation: spinOrb 1.1s cubic-bezier(0.68, -0.55, 0.27, 1.55) infinite;
    margin-bottom: 20px;
}

.loader-orb-center {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 30px;
    height: 30px;
    background: linear-gradient(135deg, #7c3aed, #38bdf8);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}

@keyframes spinOrb {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.loader-status-title {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 6px;
    text-align: center;
}

.loader-status-title span {
    background: linear-gradient(135deg, #a78bfa 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.loader-status-sub {
    font-size: 13px;
    color: #94a3b8;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 14px;
    text-align: center;
}

.loader-progress-track {
    width: 250px;
    height: 4px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 99px;
    overflow: hidden;
    position: relative;
}

.loader-progress-bar {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    width: 45%;
    background: linear-gradient(90deg, #7c3aed, #38bdf8);
    border-radius: 99px;
    animation: barScan 1.6s infinite ease-in-out;
}

@keyframes barScan {
    0% { left: -45%; }
    100% { left: 100%; }
}
</style>

<div class="cosmic-canvas">
    <div class="aurora-haze"></div>
    <div class="star-field-1"></div>
    <div class="star-field-2"></div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "review_result" not in st.session_state:
    st.session_state.review_result = None
if "last_project" not in st.session_state:
    st.session_state.last_project = "Core Audit"
if "selected_language" not in st.session_state:
    st.session_state.selected_language = "Python"
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "signin"
if "editor_version" not in st.session_state:
    st.session_state.editor_version = 0
if "rag_indexed_count" not in st.session_state:
    st.session_state.rag_indexed_count = 0

if "editor_code" not in st.session_state:
    st.session_state.editor_code = (
        'for i in range(0, 5):\n'
        '    if i > 5:\n'
        '        print(2)\n'
        '    print(i)\n'
    )

def fix_and_reinspect(issues_list, proj_name, lang):
    current_code = st.session_state.editor_code
    patched = apply_fixes_to_code(current_code, lang, issues_list)
    st.session_state.editor_code = patched
    st.session_state.editor_version += 1
    fresh_result = review_code(code=patched, language=lang, project_name=proj_name)
    st.session_state.review_result = fresh_result
    st.rerun()

# ============================================================
# GOOGLE REDIRECT LISTENER
# ============================================================

query_params = st.query_params
if "code" in query_params and not st.session_state.authenticated:
    auth_code = query_params["code"]
    try:
        success, res = process_google_callback(auth_code)
    except Exception as e:
        success = False
        res = f"OAuth Error: {str(e)}"
    if success:
        st.session_state.authenticated = True
        st.session_state.user = res
        st.query_params.clear()
        st.rerun()
    else:
        st.query_params.clear()
        st.error(f"Authentication Failed: {res}")

# ============================================================
# AUTHENTICATION & MODERN CAPABILITIES SHOWCASE SCREEN
# ============================================================

if not st.session_state.authenticated:
    col_left, col_right = st.columns([1.55, 1], gap="large")

    with col_left:
        hero_html = (
            '<div style="padding-top: 4px;">\n'
            '<div style="display:inline-flex; align-items:center; gap:8px; background:rgba(124,58,237,0.22); border:1px solid rgba(167,139,250,0.45); color:#e0e7ff; font-size:11.5px; font-weight:800; letter-spacing:1.8px; padding:7px 16px; border-radius:99px; text-transform:uppercase; margin-bottom:14px;">\n'
            '<span style="width:8px; height:8px; background:#38bdf8; border-radius:50%; box-shadow:0 0 12px #38bdf8;"></span>\n'
            '⚡ ENTERPRISE-GRADE AI CODE INTELLIGENCE</div>\n'
            '<div style="font-size:44px; font-weight:900; line-height:1.08; color:#ffffff; letter-spacing:-1.8px; margin-bottom:14px;">\n'
            'Autonomous Code Audits <br><span style="background:linear-gradient(135deg, #c084fc 0%, #818cf8 35%, #38bdf8 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Multi-Agent Refactor Engine</span>\n'
            '</div>\n'
            '<div style="font-size:14.5px; color:#94a3b8; line-height:1.65; margin-bottom:16px; max-width:680px;">\n'
            'ReviewX bridges deterministic AST compilers with semantic local LLMs via Ollama, ChromaDB vector RAG codebase indexing, and real-time sandbox execution.\n'
            '</div>\n'
            '<div style="display:flex; gap:16px; align-items:center; margin-bottom:14px;">\n'
            '   <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.1); border-radius:14px; padding:10px 18px; flex:1;">\n'
            '       <div style="font-size:20px; font-weight:900; color:#38bdf8;">12 Core</div>\n'
            '       <div style="font-size:11px; color:#64748b; font-weight:700;">Engine Features</div>\n'
            '   </div>\n'
            '   <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.1); border-radius:14px; padding:10px 18px; flex:1;">\n'
            '       <div style="font-size:20px; font-weight:900; color:#a78bfa;">100% Free</div>\n'
            '       <div style="font-size:11px; color:#64748b; font-weight:700;">Local Toolchain</div>\n'
            '   </div>\n'
            '   <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.1); border-radius:14px; padding:10px 18px; flex:1;">\n'
            '       <div style="font-size:20px; font-weight:900; color:#34d399;">0 Hallucinations</div>\n'
            '       <div style="font-size:11px; color:#64748b; font-weight:700;">Deterministic AST</div>\n'
            '   </div>\n'
            '</div>\n'
            # --- Live Cyber Interactive Pipeline & Terminal Card ---
            '<div style="background:linear-gradient(180deg, rgba(10,15,28,0.95) 0%, rgba(4,7,14,0.98) 100%); border:1px solid rgba(255,255,255,0.12); border-radius:16px; overflow:hidden; box-shadow:0 18px 40px rgba(0,0,0,0.65); margin-bottom:12px;">\n'
            '   <div style="background:rgba(15,23,42,0.95); padding:10px 18px; border-bottom:1px solid rgba(255,255,255,0.08); display:flex; justify-content:space-between; align-items:center;">\n'
            '       <div style="display:flex; align-items:center; gap:8px;">\n'
            '           <span style="width:9px; height:9px; border-radius:50%; background:#ef4444; display:inline-block; box-shadow:0 0 8px rgba(239,68,68,0.6);"></span>\n'
            '           <span style="width:9px; height:9px; border-radius:50%; background:#f59e0b; display:inline-block; box-shadow:0 0 8px rgba(245,158,11,0.6);"></span>\n'
            '           <span style="width:9px; height:9px; border-radius:50%; background:#10b981; display:inline-block; box-shadow:0 0 8px rgba(16,185,129,0.6);"></span>\n'
            '           <span style="color:#cbd5e1; font-size:12px; font-family:\'JetBrains Mono\', monospace; margin-left:10px; font-weight:600;">engine-flow.pipeline</span>\n'
            '       </div>\n'
            '       <span style="color:#38bdf8; font-size:11px; font-weight:800; letter-spacing:1px;">AUTONOMOUS AGENTS ACTIVE</span>\n'
            '   </div>\n'
            '   <div style="padding:12px 18px; font-family:\'JetBrains Mono\', monospace; font-size:12px; line-height:1.75; color:#cbd5e1;">\n'
            '       <div style="color:#64748b; margin-bottom:4px;">// Realtime Multi-Agent Inspection Sequence:</div>\n'
            '       <div><span style="color:#34d399; font-weight:700;">✓ [0.002s]</span> AST Compiler &rarr; Static parser validated (Strict Scope Guard)</div>\n'
            '       <div><span style="color:#38bdf8; font-weight:700;">✓ [0.015s]</span> ChromaDB Vector RAG &rarr; Cross-file repository context injected</div>\n'
            '       <div><span style="color:#c084fc; font-weight:700;">✓ [0.084s]</span> Subprocess Sandbox &rarr; Sandboxed execution verified (Exit 0)</div>\n'
            '       <div><span style="color:#fbbf24; font-weight:700;">✓ [0.120s]</span> Consensus Judge &rarr; Security &amp; quality consensus score 10/10</div>\n'
            '   </div>\n'
            '</div>\n'
            # --- Live Engine Telemetry & Runtimes Grid ---
            '<div style="background:rgba(12,18,34,0.85); border:1px solid rgba(255,255,255,0.1); border-radius:14px; padding:10px 18px; display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">\n'
            '   <div style="display:flex; align-items:center; gap:10px;">\n'
            '       <span style="font-size:11px; font-weight:800; color:#38bdf8; text-transform:uppercase; letter-spacing:1px;">⚡ Runtimes:</span>\n'
            '       <span style="font-size:11px; background:rgba(56,189,248,0.12); border:1px solid rgba(56,189,248,0.3); color:#f1f5f9; padding:3px 9px; border-radius:6px; font-family:\'JetBrains Mono\', monospace; font-weight:600;">Python 3.11</span>\n'
            '       <span style="font-size:11px; background:rgba(168,85,247,0.12); border:1px solid rgba(168,85,247,0.3); color:#f1f5f9; padding:3px 9px; border-radius:6px; font-family:\'JetBrains Mono\', monospace; font-weight:600;">Node.js v20</span>\n'
            '       <span style="font-size:11px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); color:#f1f5f9; padding:3px 9px; border-radius:6px; font-family:\'JetBrains Mono\', monospace; font-weight:600;">GCC/G++</span>\n'
            '       <span style="font-size:11px; background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); color:#f1f5f9; padding:3px 9px; border-radius:6px; font-family:\'JetBrains Mono\', monospace; font-weight:600;">OpenJDK</span>\n'
            '   </div>\n'
            '   <div style="display:flex; align-items:center; gap:8px;">\n'
            '       <span style="width:7px; height:7px; background:#10b981; border-radius:50%; box-shadow:0 0 10px #10b981;"></span>\n'
            '       <span style="font-size:10.5px; font-weight:800; color:#10b981; letter-spacing:0.8px;">SANDBOX READY</span>\n'
            '   </div>\n'
            '</div>\n'
            # --- GAP FILLER: Interactive Security & Quality Gate Card ---
            '<div style="background:linear-gradient(170deg, rgba(14,22,46,0.85) 0%, rgba(8,13,28,0.95) 100%); border:1px solid rgba(139,92,246,0.25); border-radius:14px; padding:12px 18px; display:flex; justify-content:space-between; align-items:center;">\n'
            '   <div style="display:flex; align-items:center; gap:12px;">\n'
            '       <div style="width:36px; height:36px; border-radius:10px; background:rgba(56,189,248,0.15); border:1px solid rgba(56,189,248,0.35); display:flex; align-items:center; justify-content:center; font-size:17px;">🛡️</div>\n'
            '       <div>\n'
            '           <div style="font-size:12.5px; font-weight:800; color:#ffffff;">Autonomous Security & Quality Gate</div>\n'
            '           <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Real-time vulnerability prevention &bull; Deterministic compiler-level verification</div>\n'
            '       </div>\n'
            '   </div>\n'
            '   <div style="background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.35); border-radius:8px; padding:4px 10px; font-size:11px; font-weight:800; color:#34d399; font-family:\'JetBrains Mono\', monospace;">\n'
            '       100% VERIFIED\n'
            '   </div>\n'
            '</div>\n'
            '</div>'
        )
        st.markdown(hero_html, unsafe_allow_html=True)

    with col_right:
        # Single seamless card container
        st.markdown("""
        <div class="cyber-auth-wrap">
            <div class="auth-headline">
                <div class="auth-header-glow">
                    <span>Launch</span> 
                    <span class="brand-grad">ReviewX</span>
                    <span style="font-size: 22px;">⚡</span>
                </div>
                <div style="font-size: 13px; color: #94a3b8; font-weight: 500; margin-top: 8px;">
                    Autonomous multi-agent intelligence workspace
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Tab Selection Row with clear breathing space
        col_tab1, col_tab2 = st.columns(2)
        with col_tab1:
            if st.button("Sign In", use_container_width=True, type="primary" if st.session_state.auth_mode == "signin" else "secondary"):
                st.session_state.auth_mode = "signin"
                st.rerun()
        with col_tab2:
            if st.button("Create Account", use_container_width=True, type="primary" if st.session_state.auth_mode == "signup" else "secondary"):
                st.session_state.auth_mode = "signup"
                st.rerun()

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        if st.session_state.auth_mode == "signin":
            with st.form("signin_form"):
                st.markdown("<div style='font-size:11.5px; font-weight:800; color:#38bdf8; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;'>👤 Developer Credentials</div>", unsafe_allow_html=True)
                login_id = st.text_input("Username or Email", placeholder="dev@company.com")
                login_pwd = st.text_input("Password", type="password", placeholder="••••••••")
                submit_login = st.form_submit_button("Authenticate Session →", use_container_width=True)
                if submit_login:
                    success, res = authenticate_user(login_id, login_pwd)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = res
                        st.rerun()
                    else:
                        st.error(res)
        else:
            with st.form("signup_form"):
                st.markdown("<div style='font-size:11.5px; font-weight:800; color:#c084fc; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;'>🚀 Create Developer Profile</div>", unsafe_allow_html=True)
                reg_user = st.text_input("Developer Username", placeholder="e.g. dev_shorya")
                reg_email = st.text_input("Work Email", placeholder="shorya@company.com")
                reg_pwd = st.text_input("Password", type="password", placeholder="Min. 6 characters")
                submit_reg = st.form_submit_button("Create Profile →", use_container_width=True)
                if submit_reg:
                    success, res = register_user(reg_user, reg_email, reg_pwd)
                    if success:
                        st.success(res)
                    else:
                        st.error(res)

        st.markdown("""
        <div style="display:flex; align-items:center; text-align:center; margin:22px 0 14px 0; color:#64748b; font-size:10px; font-weight:800; letter-spacing:1.5px;">
            <span style="flex:1; border-bottom:1px solid rgba(255,255,255,0.12); margin-right:1em;"></span>
            OR CONTINUE WITH
            <span style="flex:1; border-bottom:1px solid rgba(255,255,255,0.12); margin-left:1em;"></span>
        </div>
        """, unsafe_allow_html=True)

        google_login_url, err = get_google_login_url()
        if google_login_url:
            st.markdown(f"""
            <a href="{google_login_url}" target="_self" class="google-auth-btn">
                <svg width="20" height="20" viewBox="0 0 48 48">
                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.79l7.97-6.2z"/>
                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                </svg>
                Continue with Google
            </a>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ----------------- 12 USER-CENTRIC FEATURE CAPABILITIES -----------------
    st.markdown("""
    <div style="text-align: center; margin-top: 24px; margin-bottom: 22px;">
        <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(124, 58, 237, 0.16); border: 1px solid rgba(167, 139, 250, 0.35); color: #c084fc; font-size: 11px; font-weight: 800; padding: 4px 14px; border-radius: 99px; text-transform: uppercase; letter-spacing: 1px;">
            ⚡ Platform Capabilities
        </div>
        <div style="font-size: 26px; font-weight: 900; color: #ffffff; letter-spacing: -0.8px; margin-top: 8px;">
            Core ReviewX Intelligence Suite
        </div>
        <div style="font-size: 13px; color: #94a3b8; margin-top: 3px;">
            Production-grade autonomous code auditing, security enforcement, and automated refactoring.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Row 1 (Features 1 to 4)
    r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4, gap="small")
    with r1_c1:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Multi-Agent Code Review</span>
                <span class="badge-live">LIVE</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Parallel specialized audit bots analyzing syntax, security, and algorithmic performance.</div>
        </div>
        """, unsafe_allow_html=True)
    with r1_c2:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Repository-Aware Context</span>
                <span class="badge-live">LIVE</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Deep semantic indexing of your whole project to cross-verify imports and module calls.</div>
        </div>
        """, unsafe_allow_html=True)
    with r1_c3:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Quality Consensus Judge</span>
                <span class="badge-live">LIVE</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Consolidates feedback from multiple agents into an objective 10-point health score.</div>
        </div>
        """, unsafe_allow_html=True)
    with r1_c4:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Severity & Confidence Scoring</span>
                <span class="badge-queued">UPCOMING</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Quantified risk metrics tagging issues as Critical, Warning, or Informational.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Row 2 (Features 5 to 8)
    r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4, gap="small")
    with r2_c1:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Explainable Findings</span>
                <span class="badge-live">LIVE</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Clear, step-by-step diagnostic breakdown explaining the exact root cause of bugs.</div>
        </div>
        """, unsafe_allow_html=True)
    with r2_c2:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">1-Click Auto Patching</span>
                <span class="badge-live">LIVE</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Instant refactoring engine that automatically fixes syntax, dead code, and injections.</div>
        </div>
        """, unsafe_allow_html=True)
    with r2_c3:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Automated Unit Test Gen</span>
                <span class="badge-queued">UPCOMING</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Generates high-coverage unit tests and edge cases based on inspected code logic.</div>
        </div>
        """, unsafe_allow_html=True)
    with r2_c4:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">GitHub PR Diff Review</span>
                <span class="badge-queued">UPCOMING</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Integrates into pull request workflows to audit changed lines before merging.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Row 3 (Features 9 to 12)
    r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4, gap="small")
    with r3_c1:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Autonomous PR Comments</span>
                <span class="badge-queued">UPCOMING</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Posts inline comments and suggested code changes directly on GitHub pull requests.</div>
        </div>
        """, unsafe_allow_html=True)
    with r3_c2:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Human-in-the-Loop Approval</span>
                <span class="badge-queued">UPCOMING</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Developer-guided approval workflows ensuring manual sign-off before patch execution.</div>
        </div>
        """, unsafe_allow_html=True)
    with r3_c3:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Audit History & Memory</span>
                <span class="badge-queued">UPCOMING</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Tracks historical reviews, recurring anti-patterns, and repository quality trends over time.</div>
        </div>
        """, unsafe_allow_html=True)
    with r3_c4:
        st.markdown("""
        <div class="tool-matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13.5px; font-weight:800; color:#fff;">Real-Time Diagnostics HUD</span>
                <span class="badge-live">LIVE</span>
            </div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.5; margin-top:8px;">Live terminal telemetry, exit codes, execution timing, and compiler error stream.</div>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# ============================================================
# LEFT SIDEBAR WITH REPOSITORY RAG UPLOADER
# ============================================================

with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:18px; padding-bottom:14px; border-bottom:1px solid rgba(255,255,255,0.08);">
        <div style="width:38px; height:38px; background:linear-gradient(135deg, #7c3aed, #38bdf8); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:20px; box-shadow:0 0 18px rgba(124,58,237,0.5);">⚡</div>
        <div>
            <div style="font-size:20px; font-weight:900; color:#fff;">Review<span style="color:#818cf8;">X</span></div>
            <div style="font-size:10px; color:#64748b; font-weight:800; text-transform:uppercase;">Repo-Aware Suite</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    current_user = st.session_state.user
    if current_user:
        u_name = current_user.get("username", "Developer")
        u_email = current_user.get("email", "")
        st.markdown(f"""
        <div style="background: rgba(10, 15, 28, 0.85); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 14px; padding: 12px 14px; margin-bottom: 14px;">
            <div style="color:#fff; font-weight:800; font-size:13.5px;">{u_name}</div>
            <div style="color:#94a3b8; font-size:11px;">{u_email}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Sign Out", use_container_width=True, type="secondary"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.review_result = None
            st.rerun()

    st.divider()

    st.markdown("<div style='font-size:12px; font-weight:800; color:#38bdf8; margin-bottom:6px;'>📂 REPOSITORY-AWARE RAG</div>", unsafe_allow_html=True)
    uploaded_zip = st.file_uploader("Upload Repo ZIP (.zip)", type=["zip"], help="Upload entire project to give the AI cross-file context")
    if uploaded_zip:
        if st.button("⚡ Index Repository in ChromaDB", use_container_width=True):
            with st.spinner("Extracting & Indexing codebase in Vector DB..."):
                count = index_repository_from_zip(uploaded_zip.getvalue())
                st.session_state.rag_indexed_count = count
                st.success(f"Indexed {count} files successfully!")

    if st.session_state.rag_indexed_count > 0:
        st.markdown(f"<div style='font-size:11px; color:#10b981; font-weight:700;'>● {st.session_state.rag_indexed_count} repo files active in Vector Store</div>", unsafe_allow_html=True)

    st.divider()

    project_name = st.text_input("Workspace / Project", value=st.session_state.last_project)
    st.session_state.last_project = project_name

    language = st.selectbox(
        "Programming Language",
        ["Python", "JavaScript", "C++", "C", "Java"],
        index=["Python", "JavaScript", "C++", "C", "Java"].index(st.session_state.selected_language)
        if st.session_state.selected_language in ["Python", "JavaScript", "C++", "C", "Java"] else 0
    )
    st.session_state.selected_language = language

    ollama_online = ollama_is_running()
    status_color = "#10b981" if ollama_online else "#f43f5e"
    status_text = "Ollama Active" if ollama_online else "Ollama Offline"

    st.markdown(f"""
    <div style="background: rgba(8, 12, 22, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 14px; margin-top: 15px;">
        <span style="font-size: 11px; font-weight: 800; color: {status_color}; text-transform:uppercase;">
            ● {status_text}
        </span>
        <div style="font-size: 11.5px; color: #718096; margin-top: 4px;">
            • ChromaDB Vector Store Active<br>
            • Subprocess Runtime Engine<br>
            • AST Static Compiler Guard
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# 50-50 HIGH-TECH IDE WORKSPACE
# ============================================================

col_editor, col_output = st.columns([1, 1], gap="large")

with col_editor:
    lang_ext = {"Python": "main.py", "C++": "main.cpp", "C": "main.c", "Java": "Main.java", "JavaScript": "index.js"}.get(st.session_state.selected_language, "source.code")

    st.markdown(f"""
    <div class="terminal-window-header">
        <div class="terminal-dots-box">
            <span class="window-dot w-red"></span>
            <span class="window-dot w-yellow"></span>
            <span class="window-dot w-green"></span>
            <div class="file-tab-badge" style="margin-left: 10px;">
                <span>⚡</span> {lang_ext}
            </div>
        </div>
        <div style="font-size: 11px; font-weight: 800; color: #38bdf8; text-transform: uppercase;">
            ACTIVE BUFFER
        </div>
    </div>
    """, unsafe_allow_html=True)

    dynamic_text_key = f"code_editor_v{st.session_state.editor_version}"
    input_code = st.text_area(
        "Source Input",
        value=st.session_state.editor_code,
        height=360,
        label_visibility="collapsed",
        key=dynamic_text_key
    )
    if input_code != st.session_state.editor_code:
        st.session_state.editor_code = input_code

    col_btn_run, col_btn_clear = st.columns([2, 1])
    with col_btn_run:
        review_clicked = st.button("⚡ Run Full Inspection", use_container_width=True, type="primary")
    with col_btn_clear:
        if st.button("🗑️ Clear Code", use_container_width=True):
            st.session_state.editor_code = ""
            st.session_state.editor_version += 1
            st.session_state.review_result = None
            st.rerun()

    if review_clicked:
        active_code = input_code.strip() if input_code else st.session_state.editor_code.strip()
        if not active_code:
            st.warning("Please paste or write source code in the editor.")
        else:
            loader_box = st.empty()
            loader_box.markdown("""
            <div class="cyber-loader-container">
                <div class="loader-orb-ring"><div class="loader-orb-center">⚡</div></div>
                <div class="loader-status-title">Executing Deep <span>Multi-Agent + RAG Audit</span></div>
                <div class="loader-status-sub">Querying ChromaDB &bull; Verifying Runtime &bull; Multi-Agent Swarm</div>
                <div class="loader-progress-track"><div class="loader-progress-bar"></div></div>
            </div>
            """, unsafe_allow_html=True)

            result = review_code(
                code=active_code,
                language=st.session_state.selected_language,
                project_name=st.session_state.last_project
            )
            loader_box.empty()
            st.session_state.review_result = result
            st.rerun()

    # Terminal Output Box
    exec_info = st.session_state.review_result.get("execution") if st.session_state.review_result else None
    if exec_info:
        is_ok = exec_info.get("success", False)
        raw_output = exec_info.get("output", "")
        escaped_output = html.escape(raw_output)
        time_taken = exec_info.get("execution_time", "0s")
        exit_code = exec_info.get("exit_code", 0)

        status_badge = (
            f'<span style="color:#10b981; font-weight:800; font-size:11px;">● SUCCESS (0)</span>'
            if is_ok else
            f'<span style="color:#f43f5e; font-weight:800; font-size:11px;">● EXIT CODE ({exit_code})</span>'
        )

        st.markdown(f"""
        <div class="console-container">
            <div class="console-header">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:13px;">💻</span>
                    <span style="font-size:11px; font-weight:800; color:#cbd5e1; text-transform:uppercase;">Live Terminal Output</span>
                </div>
                <div style="display:flex; align-items:center; gap:12px;">
                    {status_badge}
                    <span style="font-size:11px; color:#64748b; font-family:'JetBrains Mono', monospace;">{time_taken}</span>
                </div>
            </div>
            <div class="console-body" style="color: {'#38bdf8' if is_ok else '#fb7185'};">
{escaped_output}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="console-container">
            <div class="console-header">
                <span style="font-size:11px; font-weight:800; color:#64748b; text-transform:uppercase;">Terminal Console</span>
                <span style="font-size:11px; color:#64748b; font-weight:700;">STANDBY</span>
            </div>
            <div class="console-body" style="color: #475569; font-style: italic;">
Run inspection to test and execute your code. Program output will stream here.
            </div>
        </div>
        """, unsafe_allow_html=True)

with col_output:
    st.markdown("""
    <div class="terminal-window-header">
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:14px;">📡</span>
            <span style="font-size: 12px; font-weight: 800; color: #e2e8f0; text-transform: uppercase;">Telemetry & Diagnostic HUD</span>
        </div>
        <div style="font-size: 11px; font-weight: 800; color: #a78bfa; text-transform: uppercase;">MONITOR ACTIVE</div>
    </div>
    """, unsafe_allow_html=True)

    result = st.session_state.review_result
    if not result:
        st.markdown("""
        <div style="background: linear-gradient(165deg, rgba(12, 17, 30, 0.8) 0%, rgba(6, 9, 16, 0.9) 100%); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 24px; min-height: 615px; display:flex; align-items:center; justify-content:center;">
            <div style="border: 2px dashed rgba(139, 92, 246, 0.25); border-radius: 16px; padding: 85px 20px; text-align: center; width:100%;">
                <div style="font-size: 32px; margin-bottom: 12px;">⚡</div>
                <div style="font-weight: 900; color: #ffffff; font-size: 20px; margin-bottom: 6px;">Workspace Ready</div>
                <div style="color: #94a3b8; font-size: 13.5px; max-width: 420px; margin: 0 auto; line-height: 1.6;">
                    Write code on the left or upload your project ZIP in the sidebar to activate <b>Repository-Aware RAG</b>.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        errors = result.get("errors", [])
        suggestions = result.get("suggestions", [])
        score = result.get("quality_score", 0)
        has_rag = result.get("rag_context_found", False)

        try:
            score = int(float(score))
        except Exception:
            score = 0
        score = max(0, min(10, score))

        score_color = "#10b981" if score >= 8 else ("#f59e0b" if score >= 5 else "#f43f5e")
        score_gradient = "linear-gradient(135deg, rgba(16,185,129,0.2) 0%, rgba(5,150,105,0.05) 100%)" if score >= 8 else "linear-gradient(135deg, rgba(244,63,94,0.2) 0%, rgba(225,29,72,0.05) 100%)"
        score_border = "#10b981" if score >= 8 else "#f43f5e"

        st.markdown(f"""
        <div class="hud-main-container">
            <div style="display: flex; align-items: center; gap: 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 18px; margin-bottom: 22px;">
                <div class="score-orb-wrapper" style="background: {score_gradient}; border: 2px solid {score_border};">
                    <span style="font-size: 36px; font-weight: 900; color: {score_color};">{score}</span>
                    <span style="font-size: 11px; font-weight: 800; color: #94a3b8; text-transform: uppercase;">/ 10 Score</span>
                </div>
                <div>
                    <div style="font-size: 20px; font-weight: 900; color: #ffffff;">Audit Quality Consensus</div>
                    <div style="font-size: 12px; color: {'#38bdf8' if has_rag else '#94a3b8'}; margin-top: 4px;">
                        {'⚡ Code reviewed with active Repository-Aware RAG context' if has_rag else '• Standalone file audit (No repo context attached)'}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.markdown(f"""
            <div class="metric-chip">
                <div>
                    <div style="font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase;">Fatal Errors</div>
                    <div style="font-size: 24px; font-weight: 900; color: {'#f43f5e' if errors else '#10b981'};">{len(errors)}</div>
                </div>
                <div style="font-size: 24px;">{'🚨' if errors else '🛡️'}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_m2:
            st.markdown(f"""
            <div class="metric-chip">
                <div>
                    <div style="font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase;">Optimization Tips</div>
                    <div style="font-size: 24px; font-weight: 900; color: #f59e0b;">{len(suggestions)}</div>
                </div>
                <div style="font-size: 24px;">💡</div>
            </div>
            """, unsafe_allow_html=True)

        with col_m3:
            st.markdown(f"""
            <div class="metric-chip">
                <div>
                    <div style="font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase;">RAG Mode</div>
                    <div style="font-size: 14px; font-weight: 900; color: {'#38bdf8' if has_rag else '#64748b'}; margin-top: 6px;">
                        {'ACTIVE CONTEXT' if has_rag else 'SINGLE FILE'}
                    </div>
                </div>
                <div style="font-size: 24px;">📂</div>
            </div>
            """, unsafe_allow_html=True)

        all_issues = errors + suggestions
        if all_issues:
            if st.button("🛠 Auto-Refactor: Fix All Issues in Editor", type="primary", use_container_width=True):
                fix_and_reinspect(all_issues, st.session_state.last_project, st.session_state.selected_language)

        tab_err, tab_sugg = st.tabs([f"❌ Critical Errors ({len(errors)})", f"💡 Suggestions ({len(suggestions)})"])
        with tab_err:
            if not errors:
                st.markdown('<div style="color: #10b981; font-weight:700; padding:20px 0; text-align:center;">✨ Zero syntax or fatal errors.</div>', unsafe_allow_html=True)
            else:
                for idx, err in enumerate(errors, start=1):
                    st.markdown(f"""
                    <div class="cyber-card cyber-card-fatal">
                        <span style="font-size: 11px; font-weight: 900; color: #fb7185;">EXCEPTION #{idx}</span>
                        <div style="color: #f8fafc; font-size: 13.5px; margin-top: 6px;">{err}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"⚡ Patch Issue #{idx}", key=f"btn_err_{idx}_{st.session_state.editor_version}", use_container_width=True):
                        fix_and_reinspect([err], st.session_state.last_project, st.session_state.selected_language)

        with tab_sugg:
            if not suggestions:
                st.markdown('<div style="color: #94a3b8; padding:20px 0; text-align:center;">💡 Code conforms to architectural guidelines.</div>', unsafe_allow_html=True)
            else:
                for idx, sugg in enumerate(suggestions, start=1):
                    st.markdown(f"""
                    <div class="cyber-card cyber-card-warn">
                        <span style="font-size: 11px; font-weight: 900; color: #fbbf24;">OPTIMIZATION #{idx}</span>
                        <div style="color: #f8fafc; font-size: 13.5px; margin-top: 6px;">{sugg}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"⚡ Apply Optimization #{idx}", key=f"btn_sugg_{idx}_{st.session_state.editor_version}", use_container_width=True):
                        fix_and_reinspect([sugg], st.session_state.last_project, st.session_state.selected_language)

        st.markdown("</div>", unsafe_allow_html=True)