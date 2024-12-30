#!/usr/bin/env python3

import os
from pathlib import Path

def collect_file_contents():
    # Output file path
    output_file = "/tmp/project_context.txt"
    
    # Clear or create the output file
    with open(output_file, 'w') as f:
        f.write("")
    
    # Get the current working directory
    current_dir = Path('.')
    
    # Find all Python and shell files
    for file_path in current_dir.rglob('*'):
        # Skip if it's in pyenv directory
        if 'pyenv' in str(file_path.parent).split(os.sep):
            continue
            
        # Check if it's a file and has the right extension
        if file_path.is_file() and file_path.suffix in ['.py', '.sh']:
            try:
                # Read the file contents
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Format the output
                output = f"""=== File: {file_path} ===
----------------------------------------
{content}

"""
                
                # Print to console and append to file
                print(output)
                with open(output_file, 'a') as f:
                    f.write(output)
                    
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")

    print(f"\nAll file contents have been saved to {output_file}")

if __name__ == "__main__":
    collect_file_contents()
