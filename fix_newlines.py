import os

def fix_newlines_in_file(file_path):
    """Reads a file, replaces literal '\\n' and other escapes with actual characters, and saves it back."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Perform the replacements
        corrected_content = content.replace('\\n', '\n')  # Fix literal newline
        corrected_content = corrected_content.replace('\\\"', '"') # Fix literal escaped double quote
        corrected_content = corrected_content.replace("\\\'", "'") # Fix literal escaped single quote
        corrected_content = corrected_content.replace('\\r', '\r')  # Fix literal carriage return

        # Check if changes were made
        if corrected_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(corrected_content)
            print(f"Successfully fixed newline characters in: {file_path}")
            return True
        else:
            print(f"No problematic escape sequences found in: {file_path}")
            return False

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return False
    except Exception as e:
        print(f"An error occurred while processing {file_path}: {e}")
        return False

# --- Main execution ---
target_file = "systems/agents/evolutionary_agent.py"
print(f"Attempting to fix file: {target_file}")
if fix_newlines_in_file(target_file):
    print("File processing complete.")
else:
    print("File processing failed or no changes needed.") 