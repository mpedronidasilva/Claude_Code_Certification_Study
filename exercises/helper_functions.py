from anthropic import Anthropic
from dotenv import load_dotenv, find_dotenv
import os 

class Helper:
    """Thin wrapper around the Anthropic SDK. Loads credentials from .env and maintains message history."""

    def __init__(self):
        load_dotenv(find_dotenv())
        self.messages = []
        self.client = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url=os.getenv("BASE_URL"),
            default_headers={"Authorization": f"Bearer {os.getenv('ANTHROPIC_API_KEY')}"}
        )    
        self.model  = os.getenv("BASE_MODEL")
        self.system = None


    def add_user_message(self, text):
        """Append a user turn to the message list."""
        self.messages.append({"role":"user", "content":text})


    def add_assistant_message(self, text):
        """Append an assistant turn to the message list."""
        self.messages.append({"role":"assistant", "content":text})


    def chat(self, system=None, temperature=0.02, stop_sequences=None):
        """Send messages to the API and return the assistant's reply text. Optionally inject a system prompt."""
        params = {
            "model":self.model,
            "max_tokens":1000,
            "messages":self.messages,
            "temperature":temperature,
            "stop_sequences":stop_sequences
        }
        if system:
            params["system"] = system
        
        if stop_sequences:
            params["stop_sequences"] = stop_sequences


        message = self.client.messages.create(**params)
        response_text= message.content[0].text

        #Avoid break stuff if the last response came from an assistant instead of user
        self.add_assistant_message(response_text)
        return response_text