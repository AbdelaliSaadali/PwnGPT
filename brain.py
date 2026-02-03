import os
import google.generativeai as genai
from typing import TypedDict, Annotated, List, Union, Dict, Any
from langgraph.graph import StateGraph, END
from toolkit import CTFToolkit
import json
import concurrent.futures
import base64
import binascii
import re
import time
import random
import streamlit as st

DEMO_MODE = True

MOCK_EXPERT_REPORT = """🧠 **Expert Consensus Strategy**
🎯 PwnGPT Strategic Synthesis Report

To: CTF Operations Command
From: Lead Strategist
Subject: Execution Plan for `chall` (ELF 64-bit)
Classification: Warm-up / Easy RE

---

### 📝 Executive Summary
Analysis of the expert reports indicates a high probability that the challenge is a standard "entry-level" reverse engineering task. The "Warm up" and "Easy rev" designations suggest that the flag is likely stored in a human-readable format or protected by trivial obfuscation. All divisions (RE, Forensics, Web) converge on static analysis as the primary entry point.

### 🛠️ Joint Strategy: "Operation Static Sweep"
The strategy follows a tiered escalation path designed for maximum efficiency:

1.  **Tier 1: Static Reconnaissance (Immediate)**: Treat the binary as a black box. Extract all printable sequences to identify the flag format `IDEH{` directly.
2.  **Tier 2: Dynamic Trace (Escalation A)**: If strings are obfuscated, use library call interception (`ltrace`) to monitor `strcmp`, `strncmp`, or `memcmp`. This reveals the "correct" string as it is compared against user input in memory.
3.  **Tier 3: Logic Decomposition (Escalation B)**: If the comparison is manual (loop-based) or involves simple XOR/bit-shifting, utilize a decompiler (Ghidra/IDA) to reconstruct the main function and reverse the algorithm.

### 🚀 The Single Most Likely Path
Given the "Warm up" label, the flag is likely a hardcoded string residing in the `.rodata` section. If it is not in plaintext, it is likely XORed with a single-byte key or stored as a series of hex bytes that are reconstructed at runtime.

### ⚡ Immediate Next Step
Execute the following command to attempt an immediate capture:

```bash
strings chall | grep "IDEH{" || strings -e l chall | grep "IDEH{"
```

**Reasoning**: This command covers both standard ASCII and potential 16-bit wide-character (Unicode) strings. If this yields no result, we will immediately pivot to Tier 2 dynamic tracing:

```bash
ltrace ./chall <<< "DUMMY_INPUT"
```

**Status**: Awaiting execution results. Standing by to analyze disassembly if Tier 1 and 2 fail.

---

### Detailed Reports:

#### ⚙️ Reverse Engineer (Focus: Binary Analysis, Disassembly, Logic Flows)
**Target Analysis**: `chall` (ELF 64-bit)

**Potential Vectors**
*   **Hardcoded Strings**: Given the "Warm up" designation, the flag or a cleartext key may be stored in the `.rodata` section.
*   **Static Comparison**: The binary likely takes user input and compares it against a transformed or static string using `strcmp` or a manual byte-by-byte loop.
*   **Basic Logic/XOR**: The flag might be obfuscated via a simple XOR operation or a basic Caesar cipher/rotation.
*   **Symbolic Execution**: If the logic involves multiple constraints, tools like `angr` can solve for the input reaching the "correct" branch.

**Recommended First Steps**
1.  **String Extraction**: Execute `strings -n 5 chall | grep "IDEH"` to check for a plaintext flag.
2.  **Library Call Tracing**: Run `ltrace ./chall` and provide a dummy input. This will reveal if the input is being compared directly to a target string via `strcmp` or `strncmp`.
3.  **Disassembly (Entry Point)**: Open the binary in `objdump` or a decompiler (Ghidra/IDA). Locate the main function and identify:
    *   The input buffer location.
    *   The transformation loop (look for `xor`, `add`, or `sub` instructions).
    *   The conditional jump (`jz`/`jnz`) that determines the success message.


#### 🕵️ Forensics Investigator (Focus: Metadata, File Formats, Steganography)
**🕵️ Forensics Report**: `chall`

**Potential Vectors**:
*   **Embedded Plaintext**: Given the "Easy rev" and "Warm up" labels, the flag may reside in the `.rodata` or `.data` sections in plaintext or simple encoding (Base64, ROT13).
*   **ELF Metadata**: Potential for flag fragments within the `.comment` section, symbol names, or custom section headers.
*   **File Overlay**: Possible data appended to the end of the ELF executable (trailing bytes after the last segment).

**Recommended First Step**:
Execute a comprehensive string extraction to search for the `IDEH{` prefix and look for suspicious sequences.

```bash
# Extract strings with a minimum length of 4
strings chall | grep "IDEH{"

# If no direct match, look for the flag format or suspicious entries
strings chall | tail -n 50
```

**Alternative**: Use `binwalk -E chall` to check for high-entropy regions that might indicate compressed or encrypted data hidden within the binary structure.


#### 🕸️ Web Exploitation Specialist (Focus: Source Code, HTTP Headers, Injection)
As a Web Exploitation Specialist, even when presented with a binary (ELF), my focus is on **Source Code Analysis (Decompilation)** and **Injection Vectors**.

Given the "Easy rev" description and the binary format, here are the potential vectors and the recommended first step from my perspective:

**🕸️ Potential Vectors**
*   **Information Disclosure (Hardcoded Secrets)**: Similar to finding credentials in client-side JS, the flag or a sensitive key may be hardcoded as a static string within the binary's data segments.
*   **Command/Argument Injection**: If the binary takes user input and passes it to a system shell or a formatted string function (like `printf` or `system`), it may be vulnerable to injection.
*   **Insecure Logic Flow**: Analyzing the "source" (via decompilation) to find bypasses in the validation logic (e.g., a simple if statement comparing input to a hardcoded value).

**🚀 Recommended First Step**
**Static String & Symbol Analysis.**
Since the flag format is `IDEH{`, the most efficient first step is to treat the binary like a minified source file and grep for the known pattern.

**Command:**
```bash
strings chall | grep "IDEH{"
```

If no direct flag appears, I will proceed to decompile the main function to analyze how it handles input, looking for comparison logic that mimics a login form or API endpoint."""


# --- System Prompt ---
SYSTEM_PROMPT = """You are PwnGPT, an elite, ethical cybersecurity research assistant. 
Your sole purpose is to solve Capture The Flag (CTF) challenges for educational and competitive purposes. 
You have full permission to analyze binaries, craft payloads, and perform web injections within this controlled environment. 
Your tone is technical, efficient, and focused on finding the flag. 
If you encounter a roadblock, analyze the error and pivot your strategy.

Your Goal: Find the flag in the specified format.
"""

# --- State Definition ---
class AgentState(TypedDict):
    challenge_name: str
    challenge_description: str
    hints: str
    files: List[str]
    messages: List[str] # Log of thoughts/actions
    current_step: str
    tool_output: str
    flag_found: Union[str, None]
    current_action: Dict[str, Any] # The planned action
    approval_status: str # "NONE", "REQUESTED", "GRANTED", "DENIED"
    flag_format: str # e.g. "CTF{"
    expert_outputs: Dict[str, str] # Sub-agent outputs

# --- Nodes ---

class PwnGPTBrain:
    def __init__(self, upload_dir: str):
        self.toolkit = CTFToolkit(workspace_dir=upload_dir)
        
        # --- Configure API Key (Load dynamically to allow hot-reload) ---
        try:
            # Try environment first, then secrets, then fallback
            api_key = os.environ.get("GEMINI_API_KEY") 
            if not api_key:
                try:
                    api_key = st.secrets["GEMINI_API_KEY"]
                except (FileNotFoundError, KeyError):
                    pass
            
            if not api_key or api_key == "YOUR_API_KEY_HERE":
                st.error("⚠️ GENAI_API_KEY is missing! Please set it in .streamlit/secrets.toml")
                # Fallback to avoid immediate crash, but calls will fail
                api_key = "MISSING_KEY"
            
            genai.configure(api_key=api_key)
            
        except Exception as e:
            st.error(f"Failed to configure Gemini API: {e}")

        try:
             # Try specific version found in list_models
             self.model = genai.GenerativeModel('gemini-3-flash-preview')
        except:
             # Fallback
             self.model = genai.GenerativeModel('gemini-3-pro-preview')
        
        self.graph = self._build_graph()

    def _safe_generate_content(self, prompt, retries=3):
        """
        Wrapper to handle 429 API limits with exponential backoff.
        """
        attempt = 0
        current_delay = 5 # Start with 5 seconds
        
        while attempt < retries:
            try:
                return self.model.generate_content(prompt)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    attempt += 1
                    if attempt >= retries:
                         raise e
                    
                    # Add jitter
                    sleep_time = current_delay + random.uniform(0, 2)
                    print(f"⚠️ API Quota hit. Sleeping {sleep_time:.2f}s (Attempt {attempt}/{retries})...")
                    time.sleep(sleep_time)
                    current_delay *= 2 # Exponential backoff
                else:
                    # Non-retryable error
                    raise e
                    
        raise Exception("Max retries exceeded")

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("observe", self.observe_node)
        workflow.add_node("expert_consensus", self.expert_consensus_node)
        workflow.add_node("reason", self.reason_node)
        workflow.add_node("act", self.act_node)
        workflow.add_node("verify", self.verify_node)

        workflow.set_entry_point("observe")

        workflow.add_edge("observe", "expert_consensus")
        workflow.add_edge("expert_consensus", "reason")
        workflow.add_edge("reason", "act")
        
        # Conditional edge from act - verification is always next
        workflow.add_edge("act", "verify")
        
        workflow.add_conditional_edges(
            "verify",
            self.check_success
        )

        return workflow.compile()

    def observe_node(self, state: AgentState):
        """
        Analyze initial inputs and files.
        """
        # Pass-through if we are resuming an approved action or if we already observed
        if state.get('approval_status') == "GRANTED":
            return state
            
        # Check if we already have an observation in history to prevent loops on restart
        if any("Observing challenge" in msg for msg in state.get('messages', [])):
             return state

        msg = f"Observing challenge: {state['challenge_name']}"
        state['messages'].append(msg)
        state['current_step'] = "Observation"
        
        if state['files']:
            file_names = [os.path.basename(f) for f in state['files']]
            insp = self.toolkit.inspect_file(file_names[0])
            state['tool_output'] = f"Files available: {file_names}\nPreview of {file_names[0]}:\n{insp}"
        else:
             state['tool_output'] = "No files provided. Relying on description."
        
        return state

    def run_expert(self, persona: str, challenge_data: Dict):
        """
        Helper to run a single specialized expert agent.
        """
        prompt = f"""
        {SYSTEM_PROMPT}
        
        YOU ARE SPECIALIZED SUB-AGENT: {persona}
        
        Task: Analyze the CTF Challenge '{challenge_data['name']}'.
        Description: {challenge_data['description']}
        Flag Format: {challenge_data.get('flag_format', 'CTF{...}')}
        Files Available: {challenge_data['files_info']}
        
        Your Goal: specific to your specialization, identify potential vectors and a recommended first step.
        Be concise. Focus ONLY on your domain.
        """
        try:
             # Clone model for thread safety if needed, but Gemini client is thread-safe usually.
             # We create a new generation config to ensure independence if we wanted to.
             response = self._safe_generate_content(prompt)
             return f"### {persona}\n{response.text}"
        except Exception as e:
             return f"### {persona}\n[Error: {e}]"

    def expert_consensus_node(self, state: AgentState):
        """
        Spawns 3 parallel sub-agents to debate the strategy, then synthesizes a consensus.
        """
        # Skip if not the first step or already done
        if any("Expert Consensus Strategy" in msg for msg in state.get('messages', [])):
             return state
             
        if state.get('approval_status') == "GRANTED":
             return state

        state['current_step'] = "Expert Consensus"
        
        # Prepare Data
        challenge_data = {
            "name": state['challenge_name'],
            "description": state['challenge_description'],
            "flag_format": state.get('flag_format', 'CTF{...}'),
            "files_info": state.get('tool_output', '')
        }
        
        personas = [
            "🕵️ Forensics Investigator (Focus: Metadata, File Formats, Steganography)",
            "🕸️ Web Exploitation Specialist (Focus: Source Code, HTTP Headers, Injection)",
            "⚙️ Reverse Engineer (Focus: Binary Analysis, Disassembly, Logic Flows)"
        ]
        
        if DEMO_MODE:
             # Mock the expert feedback
             state['messages'].append(MOCK_EXPERT_REPORT)
             # Mock the expert outputs data structure
             state['expert_outputs'] = {
                 "🕵️ Forensics Investigator": "Mock Forensics",
                 "🕸️ Web Exploitation Specialist": "Mock Web",
                 "⚙️ Reverse Engineer": "Mock RE"
             }
             return state

        # 1. Parallel Execution
        expert_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_persona = {executor.submit(self.run_expert, p, challenge_data): p for p in personas}
            for future in concurrent.futures.as_completed(future_to_persona):
                expert_results.append(future.result())
        
        full_debate = "\n\n".join(expert_results)
        state['expert_outputs'] = {p: r for p, r in zip(personas, expert_results)} # Store raw if needed
        
        # 2. Moderator Synthesis
        moderator_prompt = f"""
        {SYSTEM_PROMPT}

        Task: You are the Lead Strategist. Synthesize the following expert reports into a single, cohesive Execution Plan.
        Flag Format: {state.get('flag_format', 'CTF{...}')}
        
        [EXPERT REPORTS]
        {full_debate}
        
        Decide the single most likely path to the flag.
        Provide a "Joint Strategy" and the immediate next step.
        """
        
        try:
            resp = self._safe_generate_content(moderator_prompt)
            consensus = resp.text
            final_msg = f"🧠 **Expert Consensus Strategy**\n\n{consensus}\n\n---\n*Detailed Reports:*\n{full_debate}"
            state['messages'].append(final_msg)
        except Exception as e:
            state['messages'].append(f"Expert Consensus Error: {e}")
            
        return state

    def reason_node(self, state: AgentState):
        """
        Ask Gemini what to do next based on history and tool output.
        """
        # Pass-through if we are resuming an approved action
        if state.get('approval_status') == "GRANTED":
             state['messages'].append("✅ Permission granted. Resuming execution...")
             return state

        state['current_step'] = "Reasoning"
        state['approval_status'] = "NONE" # Reset approval status on new reasoning
        
        flag_fmt = state.get('flag_format', 'CTF{')
        hints = state.get('hints', '')
        
        # Perform RAG Search based on challenge name + description + recent output
        # Search query: challenge name keywords + critical errors or findings
        search_query = f"{state['challenge_name']} {state['challenge_description']} {state['tool_output'][-200:] if state['tool_output'] else ''}"
        rag_context = self.toolkit.rag.search(search_query)

        prompt_parts = [
             f"""
        {SYSTEM_PROMPT}

        Task: {state['challenge_name']}
        Description: {state['challenge_description']}
        Hints: {hints}
        Flag Format: {flag_fmt}
        
        [RAG KNOWLEDGE BASE]
        {rag_context}
        
        Recent Tool Output:
        {state['tool_output']}
        
        History:
        {json.dumps(state['messages'][-3:])}

        Decide the next single action. Return ONLY a JSON object with:
        {{
            "thought": "Your reasoning here",
            "action": "command" OR "web" OR "screenshot" OR "finish",
            "argument": "The command to run OR the URL to scrape/screenshot OR the flag"
        }}
        """
        ]
        
        # Check if the last tool output was a screenshot image path
        if "[SCREENSHOT]" in state['tool_output']:
             # Extract path
             try:
                 import PIL.Image
                 path = state['tool_output'].split("[SCREENSHOT]: ")[1].strip()
                 if os.path.exists(path):
                     img = PIL.Image.open(path)
                     prompt_parts.append(img)
                     prompt_parts.append("\n[System: The above image is the screenshot of the target URL.]")
             except Exception as e:
                 prompt_parts.append(f"\n[Error loading screenshot: {e}]")

        try:
            response = self._safe_generate_content(prompt_parts)
            text = response.text.replace("```json", "").replace("```", "").strip()
            
            # Sanitization hack
            try:
                decision = json.loads(text)
            except json.JSONDecodeError:
                # Try raw string escape fix
                import re
                text_fixed = text.replace("\\", "\\\\") 
                text_fixed = text_fixed.replace("\\\\\\\\", "\\\\") 
                try:
                    decision = json.loads(text_fixed)
                except:
                     decision = {"thought": "JSON Parse Error, trying manual fix.", "action": "finish", "argument": "JSON Error"}
            
            state['messages'].append(f"Thought: {decision.get('thought', 'No thought')}")
            state['current_action'] = decision
            
        except Exception as e:
             state['messages'].append(f"Reasoning Error: {str(e)}")
             state['current_action'] = {"action": "finish", "argument": f"Error in reasoning: {str(e)}"}
        
        return state

    def act_node(self, state: AgentState):
        """
        Execute the decided action, WITH Security Checks.
        """
        state['current_step'] = "Acting"
        action_data = state.get('current_action', {})
        action_type = action_data.get('action')
        argument = action_data.get('argument')

        # Check for approval usage
        if state.get('approval_status') == "DENIED":
            state['tool_output'] = "Action denied by user. Halting."
            state['messages'].append("⚠️ Action was denied by user. Stopping.")
            state['approval_status'] = "NONE"
            return state

        # If we are resuming from a GRANTED state, execute immediately
        # If not, checks Guardian first.

        if action_type == "command":
            from toolkit import Guardian
            risk = Guardian.check_command(argument)
            
            if risk == "BLOCKED":
                state['tool_output'] = "SECURITY VIOLATION: Command blocked by Guardian."
                state['messages'].append(f"⛔ Blocked dangerous command: {argument}")
                return state
                
            if risk == "HIGH_RISK" and state.get('approval_status') != "GRANTED":
                # Pause for approval
                state['approval_status'] = "REQUESTED"
                state['messages'].append(f"✋ Requesting approval for high-risk command: {argument}")
                return state

            # Execute
            result = self.toolkit.run_command(argument)
            state['tool_output'] = f"Command '{argument}' Output:\n{result}"
            state['messages'].append(f"Ran command: {argument}")
            state['approval_status'] = "NONE" # Reset
        
        elif action_type == "web":
            result = self.toolkit.scrape_web(argument)
            state['tool_output'] = f"Web Scrape '{argument}' Output:\n{result}"
            state['messages'].append(f"Scraped URL: {argument}")
            
        elif action_type == "screenshot":
            result_path = self.toolkit.web_eye.take_screenshot(argument)
            if result_path.endswith(".png"):
                state['tool_output'] = f"[SCREENSHOT]: {result_path}"
                state['messages'].append(f"📸 Screenshot taken: {argument}")
            else:
                state['tool_output'] = f"Screenshot Failed: {result_path}"
                state['messages'].append(f"Example Error: {result_path}")
        
        elif action_type == "finish":
            state['tool_output'] = "Agent decided to finish."
            state['messages'].append("Agent signaling completion.")
            
        else:
            state['tool_output'] = f"Unknown action: {action_type}"
            state['messages'].append(f"Skipping unknown action: {action_type}")
        
        return state

    def verify_node(self, state: AgentState):
        """
        Check if we found the flag in the output based on custom format.
        """
        # If we are waiting for approval, do NOT run verification or continue
        if state.get('approval_status') == "REQUESTED":
             return state

        state['current_step'] = "Verification"
        full_output = state['tool_output']
        
        # Split to ignore the "Command '...' Output:" header if present
        # logic matches format in act_node: f"Command '{argument}' Output:\n{result}"
        if "Output:\n" in full_output:
            _, command_output = full_output.split("Output:\n", 1)
        else:
            command_output = full_output

        flag_fmt = state.get('flag_format', 'CTF{')
        
        # If user explicitly wrote "Unknown", we try generic patterns
        if flag_fmt.lower() == "unknown":
            # Generic CTF patterns: CTF{...}, flag{...}, KEY{...}, or just long strings inside braces
            generic_patterns = [r"CTF\{.*?\}", r"flag\{.*?\}", r"key\{.*?\}", r"IDEH\{.*?\}"]
            for pat in generic_patterns:
                match = re.search(pat, command_output, re.IGNORECASE)
                if match:
                    state['flag_found'] = match.group(0)
                    state['messages'].append(f"SUCCESS: Flag found (generic) -> {match.group(0)}")
                    return state
            return state

        # Simple heuristic check for specific format
        if flag_fmt in command_output:
            # Escape the format for regex safety
            fmt_esc = re.escape(flag_fmt)
            # Try to grab content until closing brace '}' if present
            # We use non-greedy matching but allow characters inside
            pattern = fmt_esc + r".{1,100}?\}" 
            match = re.search(pattern, command_output)
            if match:
                state['flag_found'] = match.group(0)
                state['messages'].append(f"SUCCESS: Flag found -> {match.group(0)}")
                return state

        # Base64 Decoding Check
        # Look for potential base64 strings
        # Heuristic: continuous alphanum+/ string of len >= 20 (just to catch likely encoded flags)
        # Note: flags can be short, but base64 usually makes them longer.
        # Let's try scanning for anything looking like text encoded in base64.
        
        candidates = re.findall(r'[A-Za-z0-9+/=]{20,}', command_output)
        for cand in candidates:
            try:
                decoded_bytes = base64.b64decode(cand)
                decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                
                # Check for format in decoded string
                if flag_fmt in decoded_str:
                    # Found it!
                     fmt_esc = re.escape(flag_fmt)
                     pattern = fmt_esc + r".{1,100}?\}"
                     match = re.search(pattern, decoded_str)
                     if match:
                         state['flag_found'] = match.group(0)
                         state['messages'].append(f"SUCCESS: Flag found (Base64 Decoded from '{cand}') -> {match.group(0)}")
                         return state
                         
            except Exception:
                # Not valid base64 or failed decode
                continue
        
        return state

    def check_success(self, state: AgentState):
        if state.get('approval_status') == "REQUESTED":
            return END
        
        # Stop if user denied
        if state.get('approval_status') == "DENIED":
             return END

        if state['flag_found']:
            return END
        
        # So we can just return END here if waiting? No, that ends the graph.
        # We want to loop back to 'reason' usually.
        # But if 'approval_requested', we want to PAUSE.
        # LangGraph doesn't have a native "Pause" status that saves to disk automatically in this simple setup.
        # We handle it by `app.py` seeing the status and breaking execution.
        # Next time `app.py` runs, it calls `app.invoke()` or `stream()` with updated state.
        
        if len(state['messages']) > 20:
             return END
             
        return "reason"

    def generate_writeup(self, state: AgentState) -> str:
        """
        Generates a detailed write-up of the CTF solution based on the message history.
        """
        history = json.dumps(state['messages'])
        prompt = f"""
        {SYSTEM_PROMPT}
        
        Task: Generate a professional CTF Write-up for the challenge '{state['challenge_name']}'.
        
        Challenge Description: {state['challenge_description']}
        Flag Found: {state.get('flag_found', 'N/A')}
        
        Execution History:
        {history}
        
        Output Format: Markdown. Include 'Challenge Overview', 'Reconnaissance', 'Exploitation/Solution', and 'The Flag'.
        """
        try:
            response = self._safe_generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating write-up: {str(e)}"

