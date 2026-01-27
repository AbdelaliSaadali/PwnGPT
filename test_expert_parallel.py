
from brain import PwnGPTBrain
import time
from unittest.mock import MagicMock
import google.generativeai as genai

def test_expert_parallelism():
    print("Initializing Brain...")
    
    # Mock the API configuration and Model to avoid actual network calls
    genai.configure = MagicMock()
    
    mock_response = MagicMock()
    mock_response.text = "Mocked Strategy: Analyze the headers."
    
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    
    # Monkeypatch genai.GenerativeModel constructor.
    original_constructor = genai.GenerativeModel
    genai.GenerativeModel = MagicMock(return_value=mock_model)
    
    try:
        brain = PwnGPTBrain(upload_dir="./test_uploads")
        
        initial_state = {
            "challenge_name": "Test Challenge",
            "challenge_description": "A simple test challenge.",
            "hints": "",
            "files": [],
            "messages": [],
            "current_step": "Start",
            "tool_output": "",
            "flag_found": None,
            "current_action": {},
            "approval_status": "NONE",
            "flag_format": "IDEH{"
        }
        
        print("Starting Graph...")
        app = brain.graph
        
        step_count = 0
        current_state = initial_state
        
        iterator = app.stream(current_state)
        for event in iterator:
            step_count += 1
            for node, state in event.items():
                print(f"--- Node: {node} ---")
                current_state = state
                if node == "expert_consensus":
                    print("Expert Consensus Node Triggered!")
                    
                    # Verify model call count
                    call_count = mock_model.generate_content.call_count
                    print(f"Model Call Count: {call_count}")
                    
                    if call_count >= 4:
                         print("✅ Parallel Experts Triggered (3+1 calls)")
                    else:
                         print(f"❌ Expected 4 model calls, got {call_count}")

                    # NEW: Verify Flag Format Propagation
                    print("\nVerifying Flag Format Propagation...")
                    found_format = False
                    for call in mock_model.generate_content.call_args_list:
                        args, _ = call
                        prompt_text = str(args[0])
                        if "Flag Format: IDEH{" in prompt_text:
                            found_format = True
                            # break # check all or just find one? Find one is enough proof it's being used.
                    
                    if found_format:
                        print("✅ SUCCESS: Found 'Flag Format: IDEH{' in expert prompts.")
                    else:
                        print("❌ FAILURE: Did not find 'Flag Format: IDEH{' in any prompt.")
                        for i, call in enumerate(mock_model.generate_content.call_args_list):
                            print(f"--- Prompt {i} ---")
                            print(str(call[0])[:200])

                    return
            
            if step_count > 5:
                print("❌ Timeout: Did not hit expert consensus in 5 steps.")
                break
                
    except Exception as e:
        print(f"❌ Exception: {e}")
    finally:
        # Restore
        genai.GenerativeModel = original_constructor

if __name__ == "__main__":
    test_expert_parallelism()
