import os
import requests
import json
import sys

def chat_with_claude(api_key):
    print("--- 🤖 Claude Chat (via OpenRouter) ---")
    print("Type 'exit' or 'quit' to stop.")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost:9000", # Optional for OpenRouter
        "X-Title": "SME AI Auditor Chat Test"     # Optional for OpenRouter
    }
    
    history = []
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        history.append({"role": "user", "content": user_input})
        
        data = {
            "model": "anthropic/claude-3-haiku", # Using Haiku for speed, but you can change to claude-3.5-sonnet
            "messages": history
        }
        
        try:
            print("Thinking...", end="\r")
            response = requests.post(url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                bot_message = response.json()['choices'][0]['message']['content']
                print(f"\nClaude: {bot_message}")
                history.append({"role": "assistant", "content": bot_message})
            else:
                print(f"\n❌ Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    # Pulling the key directly from the one you provided
    key = "REDACTED_OPENROUTER_KEY"
    chat_with_claude(key)
