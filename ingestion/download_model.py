import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "sarvamai/sarvam-1"

def download_model():
    print(f"Starting pre-download for {MODEL_ID}...")
    print("This may take a few minutes depending on your internet speed (approx 4GB)...")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, 
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None
    )
    
    print(f"\nModel {MODEL_ID} and Tokenizer downloaded and cached successfully!")

if __name__ == "__main__":
    download_model()
