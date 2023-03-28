import torch
from transformers import pipeline

device = torch.device("cpu")#"cuda" if torch.cuda.is_available() else "cpu")
generator = pipeline('text-generation', model='EleutherAI/gpt-neo-125M', device=0 if device.type == 'cuda' else -1)

def ai_gen(p):
    return generator(p, max_new_tokens=50000)[0]['generated_text'].strip().replace(p, "")

if __name__ == "__main__":
    while True:
        print(ai_gen(input("> ")))