import json

class ResumeJSONParser:
    def __init__(self):
        pass

    def parse_json(self, json_content: str) -> dict:
        """Parse JSON string to dictionary"""
        try:
            resume_data = json.loads(json_content)
            print("JSON validation successful!")
        except json.JSONDecodeError as e:
            print(f"Error in JSON formatting: {e}")
            # Try to clean up the JSON if it contains markdown code blocks
            try:
                clean_json = json_content.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                resume_data = json.loads(clean_json.strip())
                print("JSON validation successful after cleanup!")
            except:
                print("Could not recover from JSON error")
                return None
        return resume_data