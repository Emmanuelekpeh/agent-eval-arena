import os
import sys
import inspect

def fix_imports(file_path=None):
    """
    Fixes import issues by adding the project root to sys.path
    Similar to what IDEs like PyCharm do automatically.
    
    Args:
        file_path: Path to the file calling this function. If None, uses the caller's file.
    
    Returns:
        str: The path that was added to sys.path
    """
    # If no file_path provided, get the caller's file path
    if file_path is None:
        frame = inspect.stack()[1]
        file_path = frame.filename
    
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(file_path))
    
    # Walk up until finding project root (where there's no __init__.py)
    # Or until finding common project root markers
    path = current_dir
    while True:
        # Check for root markers
        if (os.path.exists(os.path.join(path, "setup.py")) or
            os.path.exists(os.path.join(path, ".git")) or
            os.path.exists(os.path.join(path, "README.md")) or
            os.path.exists(os.path.join(path, "main.py"))):
            break
        
        # If we can go no further up, stop
        parent = os.path.dirname(path)
        if parent == path:
            # Reached filesystem root, use one directory above the caller
            path = os.path.dirname(current_dir)
            break
        
        path = parent
    
    # Add project root to sys.path if not already there
    if path not in sys.path:
        sys.path.insert(0, path)
        print(f"ImportFix: Added {path} to sys.path")
    
    return path

# Auto-fix imports when this module is imported
caller_frame = inspect.stack()[1]
fix_imports(caller_frame.filename) 