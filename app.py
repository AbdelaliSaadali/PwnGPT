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
    
    st.markdown("### 📚 Knowledge Base (RAG)")
    kb_files = st.file_uploader("Upload Notes/Writeups", accept_multiple_files=True, type=["txt", "md"], key="kb_uploader")
    
    if kb_files:
        kb_dir = "knowledge"
        if not os.path.exists(kb_dir):
            os.makedirs(kb_dir)
        for kbf in kb_files:
            kbf_path = os.path.join(kb_dir, kbf.name)
            # Only save if not exists to avoid constant overwrites on rerun, or just overwrite is fine
            with open(kbf_path, "wb") as f:
                f.write(kbf.getbuffer())
        st.success(f"Added {len(kb_files)} files to Knowledge Base.")
    
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
if "writeup" not in st.session_state:
    st.session_state.writeup = None

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

# --- Layout Setup ---
# We create the tabs and placeholders consistently at the top level to avoid duplication
tab_console, tab_artifacts = st.tabs(["🧠 Thinking Console", "📂 Artifact Gallery"])

with tab_console:
    console_placeholder = st.empty()

with tab_artifacts:
    artifacts_placeholder = st.empty()

# --- Helper Functions for Rendering ---
def format_log(line: str) -> str:
    line_esc = line.replace("<", "&lt;").replace(">", "&gt;") # Basic HTML escaping
    
    if line.startswith("Thought:"):
        return f'<div class="log-thought">{line_esc}</div>'
    elif line.startswith("Ran command:") or line.startswith("Scraped URL:"):
        return f'<div class="log-command">> {line_esc}</div>'
    elif line.startswith("Observing challenge:"):
            return f'<div class="log-obs">{line_esc}</div>'
    elif "Expert Panel" in line or "Expert Consensus" in line:
            return f'<div class="log-expert">{line_esc}</div>'
    elif "SUCCESS:" in line or "✅" in line:
        return f'<div class="log-success">{line_esc}</div>'
    elif "⛔" in line or "⚠️" in line or "Error" in line:
        return f'<div class="log-error">{line_esc}</div>'
    elif "✋" in line:
        return f'<div class="log-warning">{line_esc}</div>'
    else:
        return f'<div>{line_esc}</div>'

def render_logs_to_placeholder(placeholder):
    if st.session_state.logs:
        formatted_lines = [format_log(log) for log in st.session_state.logs]
        console_html = "".join(formatted_lines)
        placeholder.markdown(f'<div class="console-box">{console_html}</div>', unsafe_allow_html=True)
    else:
        placeholder.info("Agent is identifying the best strategy...")

def render_artifacts_to_placeholder(placeholder):
    # Static list for speed in loop
    sandbox_path = "/Users/mac/Desktop/PwnGPT/sandbox_workspace"
    if os.path.exists(sandbox_path):
        files = []
        for root, dirs, filenames in os.walk(sandbox_path):
            for f in filenames:
                files.append(os.path.relpath(os.path.join(root, f), sandbox_path))
        
        if files:
            # We construct a simple list if we are inside the high-frequency loop
            # to avoid button rendering issues, but for now let's try rendering proper download buttons
            # IF we are stable. But to be safe and avoid "duplicate key" errors in loop,
            # let's just render the list string during thinking, and buttons when static.
            
            # Since we are reusing this function, let's just stick to the list format for consistency during run,
            # and maybe buttons at the very end.
            
            # Actually, let's use a Hybrid approach:
            # If running, show list. If stopped, show buttons.
            if st.session_state.running and not st.session_state.waiting_for_approval:
                 file_list = "\n".join([f"- {f}" for f in files])
                 placeholder.markdown(f"**Current Files (Live):**\n{file_list}")
            else:
                 # Render buttons - WE MUST BE CAREFUL AS THIS IS INSIDE A PLACEHOLDER
                 # Placeholders clear previous content.
                 with placeholder.container():
                     st.markdown("### 📦 Sandbox Artifacts")
                     for f in files:
                        c1, c2 = st.columns([4, 1])
                        c1.code(f, language="text")
                        file_full_path = os.path.join(sandbox_path, f)
                        try:
                            with open(file_full_path, "rb") as dl:
                                c2.download_button("⬇️", dl, file_name=os.path.basename(f), key=f"dl_{f}_{os.urandom(2).hex()}")
                        except:
                            pass
        else:
             placeholder.info("No artifacts yet.")
    else:
        placeholder.warning("Sandbox workspace not initialized.")


def run_agent_step():
    """
    Runs the agent loop until it finishes or hits an approval request.
    Updates the global placeholders.
    """
    if not st.session_state.current_graph_state:
        return

    upload_dir_path = "/Users/mac/Desktop/PwnGPT/sandbox_workspace"
    brain = PwnGPTBrain(upload_dir=upload_dir_path)
    app = brain.graph

    # Render initial state
    render_logs_to_placeholder(console_placeholder)
    render_artifacts_to_placeholder(artifacts_placeholder)
    
    try:
        # Stream events
        # Note: app.stream yields steps.
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
                    render_logs_to_placeholder(console_placeholder)
                    render_artifacts_to_placeholder(artifacts_placeholder)
                    st.rerun() 
                    return
                
                # Check for Approval Request
                if state.get('approval_status') == "REQUESTED":
                    st.session_state.waiting_for_approval = True
                    render_logs_to_placeholder(console_placeholder)
                    render_artifacts_to_placeholder(artifacts_placeholder)
                    st.rerun() 
                    return 

                # Live Update Console
                render_logs_to_placeholder(console_placeholder)
                render_artifacts_to_placeholder(artifacts_placeholder)
                
                # Check fin
                current_action = state.get('current_action', {}).get('action')
                if current_action == "finish":
                     st.session_state.running = False
                     return
                
                if "Reasoning Error" in str(state.get('messages', [])[-1]):
                     st.error("Agent encountered a critical error. Stopping.")
                     st.session_state.running = False
                     return

                time.sleep(0.1) 
                
    except Exception as e:
        st.error(f"Agent Crashed: {str(e)}")
        st.session_state.running = False

# Auto-run if running
if st.session_state.running and not st.session_state.waiting_for_approval:
    run_agent_step()

# If NOT running (or waiting), ensure we display the latest state in the placeholders
# Since we created placeholders at the top, they are empty if we didn't run run_agent_step 
# in this pass. So we MUST render to them now.
if not st.session_state.running or st.session_state.waiting_for_approval:
    render_logs_to_placeholder(console_placeholder)
    render_artifacts_to_placeholder(artifacts_placeholder)


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
        # If writeup already exists, just show it. If button clicked, generate it.
        if st.session_state.get("writeup") or st.button("✅ Confirm & Generate Write-up", type="primary"):
            
            if not st.session_state.get("writeup"):
                with st.spinner("Generating Write-up..."):
                    # Get the brain instance again
                    upload_dir_path = "/Users/mac/Desktop/PwnGPT/sandbox_workspace"
                    brain = PwnGPTBrain(upload_dir=upload_dir_path)
                    st.session_state.writeup = brain.generate_writeup(st.session_state.current_graph_state)
            
            # Display Writeup
            st.markdown("## 📝 CTF Write-up")
            st.markdown(st.session_state.writeup)
            
            # Generate PDF
            import utils_pdf
            upload_dir_path = "/Users/mac/Desktop/PwnGPT/sandbox_workspace"
            if not os.path.exists(upload_dir_path):
                 os.makedirs(upload_dir_path)
                 
            pdf_path = os.path.join(upload_dir_path, "PwnGPT_Report.pdf")
            logo_path = "PwnGPT.png"
            
            # We generate PDF every time to ensure it exists, or check existence
            utils_pdf.generate_pdf_report(st.session_state.writeup, pdf_path, logo_path)
            
            st.balloons()
            
            # Download Buttons
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 Download Report (PDF)", 
                        data=f, 
                        file_name="PwnGPT_Report.pdf", 
                        mime="application/pdf"
                    )
            with dl_col2:
                st.download_button(
                    label="📝 Download Report (TXT)", 
                    data=st.session_state.writeup, 
                    file_name="PwnGPT_Report.txt"
                )
    
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
