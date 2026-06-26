import os
from groq import Groq

class LLMService:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            print("Warning: GROQ_API_KEY is not set.")
        self.client = Groq(api_key=self.api_key)
        self.model_name = "llama-3.1-8b-instant"

    def generate_reply(self, prompt: str) -> str:
        """Call Groq client chat completion with the provided prompt."""
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return f"I'm sorry, I am having trouble connecting to my brain right now. Details: {str(e)}"

    def generate_json_reply(self, prompt: str) -> dict:
        """Call Groq client chat completion expecting JSON output."""
        import json
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"Error calling Groq API for JSON: {e}")
            return {
                "reply": f"I'm sorry, I am having trouble connecting to my brain right now. Details: {str(e)}",
                "suggested_replies": []
            }

# Singleton instance
llm_service = LLMService()
