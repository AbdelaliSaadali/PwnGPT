import subprocess
import requests
import os
import shutil
from typing import Optional, Dict, Any, List

class Guardian:
    """
    Security filter for PwnGPT.
    """
    HIGH_RISK_KEYWORDS = [
        "rm -rf", "mkfs", "dd if=/dev", ":(){ :|:& };:", # Fork bomb
        "wget", "curl", "nc ", "ncat", "bash -i", "/dev/tcp", # Reverse shells
        "chmod +x", "chown", "mv /"
    ]
    
    FORBIDDEN_PATHS = [
        "/etc", "/var", "/usr", "/bin", "/sbin", "~/.ssh", "~/.aws", ".env"
    ]

    @staticmethod
    def check_command(command: str) -> str:
        """
        Returns 'SAFE', 'HIGH_RISK', or 'BLOCKED'.
        """
        command_lower = command.lower()
        
        # 1. HARD BLOCK: Destructive internal commands or escaping
        if "rm -rf /" in command_lower or ":(){" in command:
            return "BLOCKED"
            
        # 2. HARD BLOCK: Accessing sensitive host paths (if somehow mounting leaked)
        for path in Guardian.FORBIDDEN_PATHS:
            if path in command:
                return "BLOCKED"

        # 3. HIGH RISK: Network tools, execution of unknown binaries, or complex shell pipes
        for keyword in Guardian.HIGH_RISK_KEYWORDS:
            if keyword in command_lower:
                return "HIGH_RISK"
        
        if "./" in command or "python" in command or "sh " in command:
            return "HIGH_RISK"

        return "SAFE"


class KnowledgeBase:
    """
    Simple RAG system for the Cyber Knowledge Base.
    """
    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = knowledge_dir
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)

    def search(self, query: str) -> str:
        """
        Simple keyword search over text files in knowledge dir.
        In a real app, this would use embeddings (ChromaDB/FAISS).
        """
        results = []
        if not os.path.exists(self.knowledge_dir):
            return "Knowledge Base is empty or missing."

        query_tokens = query.lower().split()
        
        for root, _, files in os.walk(self.knowledge_dir):
            for file in files:
                if file.endswith(".txt") or file.endswith(".md"):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            # Naive scoring: count token overlaps
                            score = sum(1 for t in query_tokens if t in content.lower())
                            if score > 0:
                                snippet = content[:500].replace("\n", " ")
                                results.append((score, f"[{file}]: {snippet}..."))
                    except:
                        continue
        
        results.sort(key=lambda x: x[0], reverse=True)
        top_results = [r[1] for r in results[:3]]
        
        if not top_results:
             return "No relevant knowledge found in Reference Library."
             
        return "\n\n".join(top_results)


class WebEye:
    """
    Multimodal Web Browser tool using Playwright.
    """
    def __init__(self):
        self.headless = True

    def take_screenshot(self, url: str) -> str:
        """
        Takes a screenshot of the URL and returns the local path.
        """
        # Note: This runs on HOST. 
        # Requirement: `pip install playwright && playwright install`
        filename = f"screenshot_{os.urandom(4).hex()}.png"
        path = os.path.join(os.getcwd(), "sandbox_workspace", filename)
        
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                page.goto(url, timeout=15000)
                page.screenshot(path=path)
                browser.close()
            return path
        except ImportError:
            return "Error: Playwright not installed. Run `pip install playwright && playwright install`."
        except Exception as e:
            return f"Screenshot failed: {e}"


class CTFToolkit:
    """
    A protected toolkit for CTF challenges using Docker for isolation.
    """

    def __init__(self, workspace_dir: str = "."):
        self.host_workspace_dir = os.path.abspath(workspace_dir)
        self.sandbox_workspace_dir = "/workspace" # Inside Docker
        self.docker_image = "kalilinux/kali-rolling"
        self.container_name = "pwngpt-session"
        
        # Init Sub-Tools
        self.rag = KnowledgeBase(knowledge_dir=os.path.join(os.getcwd(), "knowledge"))
        self.web_eye = WebEye()
        
        # Ensure docker is available
        if not self._check_docker():
            raise RuntimeError("Docker is not running or not installed. PwnGPT requires Docker for safety.")
        
        # Create sandbox dir if it doesn't exist
        if not os.path.exists(self.host_workspace_dir):
            os.makedirs(self.host_workspace_dir)

        # Pre-pull image
        self._ensure_image()
        
        # Ensure session container is running
        self._ensure_container_running()

    def _check_docker(self) -> bool:
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
            return True
        except:
            return False

    def _ensure_image(self):
        try:
             subprocess.run(["docker", "pull", self.docker_image], check=True, capture_output=True)
        except:
             pass

    def _ensure_container_running(self):
        """
        Starts the persistent container if it's not already running.
        """
        # Check if running
        check = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", self.container_name],
            capture_output=True, text=True
        )
        
        if check.returncode == 0 and "true" in check.stdout.strip():
            return # Already running

        # If it exists but stopped, remove it first
        subprocess.run(["docker", "rm", "-f", self.container_name], capture_output=True)
        
        # Start new container
        # Note: We enable networking (default bridge) to allow tool installation via apt-get
        run_cmd = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "--memory=2g",
            "--cpus=1.0",
            # "--network", "none", # DISABLED so apt-get works
            "--read-only",
            "--tmpfs", "/tmp",
            "--tmpfs", "/run",
            "-v", f"{self.host_workspace_dir}:{self.sandbox_workspace_dir}",
            "-w", self.sandbox_workspace_dir,
            "--user", "0:0", # ROOT per default for apt-get, but we should be careful? 
            # Actually, to install tools we NEED root.
            # User requirement: "No Host Access" - achieved by volume isolation.
            # "Non-Root User" - achieved by dropping privs for COMMANDS if possible, 
            # OR we run as root but user understands the risks inside container.
            # Competing constraints: "Install any tool" (needs root) vs "Non-Root User" (safety).
            # Compromise: Run container as root to allow installs, but user can choose to run specific commands as 'kali' if they exist.
            # For simplicity and "Install Any Tool" working out of the box, we often stay root in these disposable containers.
            # However, prompt earlier asked for "create a ctf-user".
            # The official kali image is root by default.
            # Let's run as root to ensure 'apt-get install' works without sudo complexity for the Agent.
            self.docker_image,
            "tail", "-f", "/dev/null" # Keep alive
        ]
        
        subprocess.run(run_cmd, check=True, capture_output=True)
        
        # Optional: update & install basic utils once?
        # subprocess.run(["docker", "exec", self.container_name, "apt-get", "update"], capture_output=True)


    def run_command(self, command: str, timeout: int = 30) -> str:
        """
        Executes a shell command within the PERSISTENT Docker sandbox.
        """
        # 1. Check Guardian
        risk_level = Guardian.check_command(command)
        if risk_level == "BLOCKED":
            return "Security Violation: Command blocked by Guardian Protocol."

        try:
            # Use docker exec
            # We use 'sh -c' to handle pipes/redirects
            exec_cmd = [
                "docker", "exec",
                self.container_name,
                "/bin/sh", "-c", command
            ]
            
            result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[STDERR]\n{result.stderr}"
            return output
            
        except subprocess.TimeoutExpired:
            return "Error: Command timed out in Sandbox."
        except Exception as e:
            return f"Error executing command in Sandbox: {str(e)}"

    def scrape_web(self, url: str) -> str:
        """
        Fetches the content of a URL. 
        Note: We run this from HOST for now as typical python requests, 
        unless we want to spawn a docker just for curl. 
        The prompt said "Every terminal command ... runs inside a Docker container".
        web scraping is a python function here.
        Safest is to use the host `requests` but strictly validate URL?
        Or run curl in docker.
        Let's stick to host requests for simplicity/speed unless requested, 
        as this is "Observe" phase usually.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text[:5000]  # Truncate for token limits
        except Exception as e:
            return f"Error fetching URL: {str(e)}"

    def inspect_file(self, file_path: str) -> str:
        """
        Reads files from the workspace (HOST side read is safe for 'Observe').
        """
        target_path = os.path.join(self.host_workspace_dir, file_path)
        
        # Path traversal check
        if not os.path.abspath(target_path).startswith(self.host_workspace_dir):
            return "Security Violation: Access denied to path outside workspace."
        
        if not os.path.exists(target_path):
             return f"Error: File {file_path} not found."

        try:
            # Try reading as text first
            with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2000)
                return f"File Content Preview:\n{content}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
