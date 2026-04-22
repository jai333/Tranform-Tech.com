import os

def rename_in_file(filepath):
    # Read
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            content = f.read()
        except UnicodeDecodeError:
            return # Skip binary files
            
    original_content = content
    
    # Replace
    content = content.replace('Transform.io', 'Transform.io')
    content = content.replace('Transform.io', 'Transform.io')
    content = content.replace('transform.io', 'transform.io')
    
    # Write back if changed
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

def main():
    skip_dirs = {'.git', '.github', '__pycache__', 'env', 'venv', 'node_modules'}
    
    # Run in ATS-CRM-Transform.io
    start_dir = '/Users/jmartin/Documents/GitHub/ATS-CRM-Transform.io'
    
    for root, dirs, files in os.walk(start_dir):
        # modify dirs in-place to skip
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py') or file.endswith('.html') or file.endswith('.md') or file.endswith('.txt'):
                filepath = os.path.join(root, file)
                rename_in_file(filepath)

if __name__ == '__main__':
    main()
