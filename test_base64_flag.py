import unittest
from brain import PwnGPTBrain
import base64

class TestBase64Validation(unittest.TestCase):
    def test_base64_decoding(self):
        # Setup
        # We only need to test the verify_node
        brain = PwnGPTBrain(upload_dir=".")
        
        # Create a mock state with the encoded flag
        flag_content = "CTF{hidden_in_blocks}"
        encoded_flag = base64.b64encode(flag_content.encode()).decode()
        # Make it look like real output
        tool_output = f"Scanning memory... Found string: {encoded_flag} ... Done."
        
        state = {
            "challenge_name": "Test",
            "challenge_description": "Test",
            "hints": "",
            "files": [],
            "messages": [],
            "current_step": "Act",
            "tool_output": tool_output,
            "flag_found": None,
            "current_action": {},
            "approval_status": "NONE",
            "flag_format": "CTF{"
        }
        
        print(f"Testing with encoded flag: {encoded_flag}")
        
        # Run verify_node
        new_state = brain.verify_node(state)
        
        # Verify
        if new_state.get('flag_found') == flag_content:
             print("✅ Success: Flag decoded and found.")
        else:
             print(f"❌ Failed: Flag not found. Found: {new_state.get('flag_found')}")
             
        self.assertEqual(new_state.get('flag_found'), flag_content)

if __name__ == "__main__":
    unittest.main()
