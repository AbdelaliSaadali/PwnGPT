import streamlit as st
import os
import time
import shutil
from brain import PwnGPTBrain

# --- Page Config ---
st.set_page_config(
    page_title="PwnGPT - Autonomous CTF Solver",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load Custom CSS ---
def load_css():
    with open("css/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# --- Helper Functions ---
def save_uploaded_files(uploaded_files, target_dir="uploads"):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    paths = []
    for uploaded_file in uploaded_files:
        file_path = os.path.join(target_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        paths.append(file_path)
    return paths, target_dir

def reset_env():
    """Clears the sandbox and session state, and KILLS the persistent Docker container."""
    # 1. Kill Container
    try:
        import subprocess
        subprocess.run(["docker", "rm", "-f", "pwngpt-session"], capture_output=True)
    except Exception as e:
        print(f"Failed to kill docker: {e}")

    # 2. Clear Sandbox Files
    sandbox_path = "/Users/mac/Desktop/PwnGPT/sandbox_workspace"
    if os.path.exists(sandbox_path):
        try:
            shutil.rmtree(sandbox_path)
            os.makedirs(sandbox_path) # Recreate empty
        except Exception as e:
            st.error(f"Failed to clear sandbox: {e}")
    
    # 3. Clear session
    st.session_state.logs = []
    st.session_state.flag = None
    st.session_state.running = False
    st.session_state.current_graph_state = None
    st.session_state.waiting_for_approval = False

# --- Sidebar Inputs ---
with st.sidebar:
    st.image("PwnGPT.png", width=300)
    st.title("PwnGPT Config")
    
    challenge_name = st.text_input("Challenge Name", "Web Intrusion 101")
    category = st.selectbox("Category", ["WEB", "PWN", "REV", "DFIR", "OSINT", "MISC", "CRYPTO"])
    flag_format = st.text_input("Flag Format (regex or prefix)", "CTF{")
    
    uploaded_files = st.file_uploader("Upload Challenge Files/Screenshots", accept_multiple_files=True)
    
    start_btn = st.button("🚀 INITIALIZE AGENT", type="primary")
    
    st.divider()
    if st.button("🗑️ RESET ENVIRONMENT", type="secondary"):
        reset_env()
        st.rerun()

# --- Main Layout ---
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("# 🛡️ PwnGPT: Agentic CTF Solver")
    description = st.text_area("Challenge Description / Briefing", height=150, 
                               placeholder="Paste the challenge text or clue here...")
    hints = st.text_area("Hints (Optional)", height=100, placeholder="Enter any provided hints here...")

# --- Session State Management ---
if "logs" not in st.session_state:
    st.session_state.logs = []
if "running" not in st.session_state:
    st.session_state.running = False
if "flag" not in st.session_state:
    st.session_state.flag = None
if "current_graph_state" not in st.session_state:
    st.session_state.current_graph_state = None
if "waiting_for_approval" not in st.session_state:
    st.session_state.waiting_for_approval = False

# --- Logic Flow ---
if start_btn:
    st.session_state.running = True
    st.session_state.logs = []
    st.session_state.flag = None
    st.session_state.waiting_for_approval = False
    st.session_state.current_graph_state = None
    
    with st.spinner("Initializing Toolkit (Pulling Docker Image if needed, this may take a minute)..."):
        # Save files
        file_paths = []
        upload_dir_path = "/Users/mac/Desktop/PwnGPT/sandbox_workspace" # Use absolute sandbox path
        if not os.path.exists(upload_dir_path):
            os.makedirs(upload_dir_path)
            
        if uploaded_files:
            file_paths, _ = save_uploaded_files(uploaded_files, target_dir=upload_dir_path)
        
        # Init Brain
        try:
            brain = PwnGPTBrain(upload_dir=upload_dir_path)
            
            # Initial State
            initial_state = {
                "challenge_name": challenge_name,
                "challenge_description": description,
                "hints": hints,
                "files": file_paths,
                "messages": [],
                "current_step": "Start",
                "tool_output": "",
                "flag_found": None,
                "current_action": {},
                "approval_status": "NONE",
                "flag_format": flag_format
            }
            st.session_state.current_graph_state = initial_state
        except RuntimeError as e:
            st.error(f"Initialization Failed: {str(e)}")
            st.session_state.running = False

def run_agent_step():
    """
    Runs the agent loop until it finishes or hits an approval request.
    Using placeholders to avoid full page reruns during streaming.
    """
    if not st.session_state.current_graph_state:
        return

    upload_dir_path = "/Users/mac/Desktop/PwnGPT/sandbox_workspace"
    brain = PwnGPTBrain(upload_dir=upload_dir_path)
    app = brain.graph
    
    # Placeholder for the console
    st.markdown("### 🧠 Neural Link (Thinking Console)")
    console_placeholder = st.empty()

    # Function to render logs to placeholder
    def format_log(line: str) -> str:
        line_esc = line.replace("<", "&lt;").replace(">", "&gt;") # Basic HTML escaping
        
        if line.startswith("Thought:"):
            return f'<div class="log-thought">{line_esc}</div>'
        elif line.startswith("Ran command:") or line.startswith("Scraped URL:"):
            return f'<div class="log-command">> {line_esc}</div>'
        elif line.startswith("Observing challenge:"):
             return f'<div class="log-obs">{line_esc}</div>'
        elif "SUCCESS:" in line or "✅" in line:
            return f'<div class="log-success">{line_esc}</div>'
        elif "⛔" in line or "⚠️" in line or "Error" in line:
            return f'<div class="log-error">{line_esc}</div>'
        elif "✋" in line:
            return f'<div class="log-warning">{line_esc}</div>'
        else:
            return f'<div>{line_esc}</div>'

    def render_logs():
        formatted_lines = [format_log(log) for log in st.session_state.logs]
        console_html = "".join(formatted_lines)
        # Scroll to bottom using flex direction or JS hack? 
        # For now, just render the div.
        console_placeholder.markdown(f'<div class="console-box">{console_html}</div>', unsafe_allow_html=True)

    # Render initial state
    render_logs()
    
    try:
        # Resume from current state
        # Note: If we just approved an action, current_graph_state has 'approval_status': 'GRANTED'
        # The brain logic will see this and pass through observe/reason to execute 'act'
        
        for event in app.stream(st.session_state.current_graph_state):
            for node, state in event.items():
                # Update global state
                st.session_state.current_graph_state = state
                
                # Update logs
                if state.get('messages'):
                    st.session_state.logs = state['messages']
                
                # Check for Flag
                if state.get('flag_found'):
                    st.session_state.flag = state['flag_found']
                    st.session_state.running = False
                    render_logs()
                    st.rerun() # Trigger success UI
                    return
                
                # Check for Approval Request
                if state.get('approval_status') == "REQUESTED":
                    st.session_state.waiting_for_approval = True
                    render_logs()
                    st.rerun() # Trigger Approval UI
                    return 

                # Live Update Console
                render_logs()
                
                # Check if Agent decided to finish or errored out
                # We inspect the messages or the last action
                current_action = state.get('current_action', {}).get('action')
                if current_action == "finish":
                     st.session_state.running = False
                     return
                
                if "Reasoning Error" in str(state.get('messages', [])[-1]):
                     st.error("Agent encountered a critical error. Stopping.")
                     st.session_state.running = False
                     return

                time.sleep(0.1) # Small cosmetic delay
                
    except Exception as e:
        st.error(f"Agent Crashed: {str(e)}")
        st.session_state.running = False

# Auto-run if running and not waiting
if st.session_state.running and not st.session_state.waiting_for_approval:
    run_agent_step()

# --- Display Console (Static or Post-Loop) ---
# If we are NOT running (waiting or finished), we still need to show the logs
if not st.session_state.running or st.session_state.waiting_for_approval:
    st.markdown("### 🧠 Neural Link (Thinking Console)")
    console_text = "\n".join(st.session_state.logs)
    st.markdown(f'<div class="console-box">{console_text}</div>', unsafe_allow_html=True)

# Approval UI Overlay
if st.session_state.waiting_for_approval:
    action = st.session_state.current_graph_state.get('current_action', {})
    st.warning(f"⚠️ **HIGH RISK ACTION DETECTED**")
    st.code(f"Action: {action.get('action')}\nCommand: {action.get('argument')}", language="bash")
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ APPROVE ACTION", type="primary"):
            st.session_state.current_graph_state['approval_status'] = "GRANTED"
            st.session_state.waiting_for_approval = False
            st.rerun() # Will trigger run_agent_step via the 'if running' block
            
    with col_b:
        if st.button("🛑 DENY ACTION"):
            st.session_state.current_graph_state['approval_status'] = "DENIED"
            st.session_state.waiting_for_approval = False
            st.rerun()

# --- Success & Feedback Loop ---
if st.session_state.flag:
    st.markdown(f"""
    <div class="success-box">
        🚩 POTENTIAL FLAG DETECTED: {st.session_state.flag}
    </div>
    """, unsafe_allow_html=True)
    
    st.info("Please verify if this is the correct flag.")
    
    col_confirm, col_reject = st.columns(2)
    
    with col_confirm:
        if st.button("✅ Confirm & Generate Write-up", type="primary"):
            with st.spinner("Generating Write-up..."):
                # Get the brain instance again (or we could cache it if it wasn't stateless per step)
                # We need the state
                upload_dir_path = "/Users/mac/Desktop/PwnGPT/sandbox_workspace"
                brain = PwnGPTBrain(upload_dir=upload_dir_path)
                writeup = brain.generate_writeup(st.session_state.current_graph_state)
                
                st.markdown("## 📝 CTF Write-up")
                st.markdown(writeup)
                st.balloons()
    
    with col_reject:
        if st.button("❌ Incorrect - Keep Searching"):
            # Resume logic
            # 1. Append user feedback to messages
            st.session_state.current_graph_state['messages'].append(
                f"User Feedback: The flag '{st.session_state.flag}' is INCORRECT. Disregard it and continue searching."
            )
            # 2. Clear flag found
            st.session_state.current_graph_state['flag_found'] = None
            st.session_state.flag = None
            
            # 3. Resume running
            st.session_state.running = True
            st.rerun()
