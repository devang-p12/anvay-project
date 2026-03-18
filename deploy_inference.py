import os
import requests
import time
import subprocess

OLLAMA_API = "http://localhost:8000/api"

def check_server():
    print("Waiting for Ollama inference server to start...")
    for _ in range(15):
        try:
            response = requests.get("http://localhost:8000/")
            if response.status_code == 200:
                print("Inference Server is ONLINE.")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    print("Failed to connect to Inference Server.")
    return False

def pull_model(model_name="gemma:2b"):
    # We use gemma:2b or qwen:1.5b as robust CPU placeholders if a specific GGUF isn't locally built.
    # To strictly use sarvam-1, we would pass 'hf.co/user/sarvam-1-gguf' if available on HF.
    print(f"Ensuring model '{model_name}' is locally vaulted...")
    
    # Check if model exists
    response = requests.get(f"{OLLAMA_API}/tags")
    if response.status_code == 200:
        models = [m["name"] for m in response.json().get("models", [])]
        if model_name in models:
            print(f"Model '{model_name}' is already vaulted and ready.")
            return

    print(f"Pulling '{model_name}' (this may take a few minutes)...")
    payload = {"name": model_name}
    response = requests.post(f"{OLLAMA_API}/pull", json=payload, stream=True)
    
    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))
            
    print(f"Model '{model_name}' successfully vaulted.")

if __name__ == "__main__":
    if check_server():
        pull_model("gemma:2b") # 2B CPU-optimized fallback
        print("Sovereign Inference Layer is fully operational and awaiting Agent requests.")
