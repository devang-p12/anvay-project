import time
import requests
import json

# We bound port 11434 to 8000 in docker-compose to match the prompt specifications
API_URL = "http://localhost:8000/v1/completions"

def run_benchmark():
    print("Initiating Sovereign TTFT (Time To First Token) Benchmark...")
    
    payload = {
        # Using the same dummy model string. Ollama allows mapping models via APIs.
        "model": "gemma:2b", 
        "prompt": "Evaluate the geopolitical importance of the Kabul region.",
        "max_tokens": 100,
        "stream": True # Streaming required to measure TTFT
    }
    
    start_time = time.time()
    try:
        response = requests.post(API_URL, json=payload, stream=True)
        
        first_token_time: float | None = None
        token_count: int = 0
        
        print("Response stream started...")
        for chunk in response.iter_lines():
            if chunk:
                # Capture TTFT roughly
                if first_token_time is None:
                    first_token_time = time.time() - start_time
                    print(f"\n[BENCHMARK] Time to First Token (TTFT): {first_token_time*1000:.2f} ms")
                
                token_count += 1
                
        total_time = time.time() - start_time
        
        if first_token_time is not None:
            print(f"[BENCHMARK] Total Generation Time: {total_time:.2f} seconds")
            if total_time > 0:
                print(f"[BENCHMARK] Throughput: {token_count / total_time:.2f} tokens/second")
            if token_count > 0:
                print(f"[BENCHMARK] Latency per generation token: {(total_time - first_token_time) / token_count * 1000:.2f} ms/token")
                
    except Exception as e:
        print(f"Benchmark failed: {e}")

if __name__ == "__main__":
    run_benchmark()
