import unittest
from unittest.mock import MagicMock, patch
from brain import PwnGPTBrain
import time

class TestRateLimit(unittest.TestCase):
    def test_backoff_on_429(self):
        # Mock genai.GenerativeModel
        mock_model = MagicMock()
        
        # Setup side_effect to raise 429 twice then succeed
        error_429 = Exception("429 Quota exceeded for metric")
        mock_response = MagicMock()
        mock_response.text = "Success after retry!"
        
        mock_model.generate_content.side_effect = [
            error_429,
            error_429,
            mock_response
        ]
        
        # Patch GenerativeModel constructor
        with patch('google.generativeai.GenerativeModel', return_value=mock_model):
            # Init brain (don't need real keys, mocks handle it)
            brain = PwnGPTBrain(upload_dir=".")
            
            print("Testing safe_generate_content with mocked 429s...")
            start_time = time.time()
            
            # This should take at least 5s + 10s = 15s (approx) due to backoff
            # attempt 1: fails, sleeps 5s+jitter
            # attempt 2: fails, sleeps 10s+jitter
            # attempt 3: succeeds
            
            # To speed up test, we can patch time.sleep, but we want to verify logic flow mostly.
            # Let's verify calls. We will mock time.sleep to avoid waiting 15s.
            with patch('time.sleep') as mock_sleep:
                 response = brain._safe_generate_content("test prompt")
                 
                 print(f"Result: {response.text}")
                 self.assertEqual(response.text, "Success after retry!")
                 
                 # Verify retries happened
                 self.assertEqual(mock_model.generate_content.call_count, 3)
                 
                 # Verify sleep called twice
                 self.assertEqual(mock_sleep.call_count, 2)
                 print("✅ Logic verified: 3 calls, 2 sleeps.")

if __name__ == "__main__":
    unittest.main()
