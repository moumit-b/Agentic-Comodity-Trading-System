"""
Quick script to switch Groq models for testing.
Usage: python switch_model.py <model_number>
"""
import sys

MODELS = {
    "1": ("llama-3.3-70b-versatile", "Best reasoning - Comprehensive analysis"),
    "2": ("llama-3.1-70b-versatile", "Strong reasoning - Balanced"),
    "3": ("mixtral-8x7b-32768", "Fast with good quality"),
    "4": ("llama-3.1-8b-instant", "Fastest - Simple queries"),
}

def switch_model(choice):
    if choice not in MODELS:
        print("Invalid choice!")
        print("\nAvailable models:")
        for num, (model, desc) in MODELS.items():
            print(f"  {num}. {model:<30} - {desc}")
        return

    model_name, description = MODELS[choice]

    # Read config.py
    with open('config.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Update GROQ_MODEL line
    for i, line in enumerate(lines):
        if line.strip().startswith('GROQ_MODEL ='):
            lines[i] = f'GROQ_MODEL = "{model_name}"  # {description}\n'
            break

    # Write back
    with open('config.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"\n✓ Switched to: {model_name}")
    print(f"  Description: {description}")
    print(f"\nNext steps:")
    print(f"  1. Restart Streamlit: venv\\Scripts\\streamlit.exe run app_v2.py")
    print(f"  2. Click '🔄 Clear Cache & Restart' in sidebar")
    print(f"  3. Test with your prompt!")

if __name__ == "__main__":
    print("=" * 60)
    print("Groq Model Switcher for Pharmaceutical Research")
    print("=" * 60)

    if len(sys.argv) > 1:
        switch_model(sys.argv[1])
    else:
        print("\nAvailable models:")
        for num, (model, desc) in MODELS.items():
            print(f"  {num}. {model:<30} - {desc}")

        choice = input("\nEnter model number (1-4): ")
        switch_model(choice.strip())
