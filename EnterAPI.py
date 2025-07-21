import os
from dotenv import load_dotenv

def write_env_variable(file_path, key, value):
    """Write or update a key-value pair in the .env file."""
    lines = []
    found = False

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")

    with open(file_path, "w") as f:
        f.writelines(lines)

def main():
    print("🔐 Save your API keys securely into a .env file\n")

    hf_key = input("Enter your Hugging Face API key: ").strip()
    gemini_key = input("Enter your Gemini API key: ").strip()

    env_path = ".env"

    write_env_variable(env_path, "HUGGINGFACE_API_KEY", hf_key)
    write_env_variable(env_path, "GEMINI_API_KEY", gemini_key)

    print(f"\n✅ Keys saved successfully in {env_path}")

if __name__ == "__main__":
    main()
