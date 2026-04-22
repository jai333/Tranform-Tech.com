import os

def rename_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return
        
    original = content
    content = content.replace('Transform.io', 'Transform.io')
    content = content.replace('transform.io', 'transform.io')
    content = content.replace('TRANSFORM.IO', 'TRANSFORM.IO')
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")

def main():
    skip_dirs = {'.git', '.github', '__pycache__', 'venv', 'env', 'node_modules'}
    
    dirs_to_process = [
        '/Users/jmartin/Documents/GitHub/ATS-CRM-Transform.io',
        '/Users/jmartin/Documents/GitHub/transform-io'
    ]
    
    count = 0
    for start_dir in dirs_to_process:
        for root, dirs, files in os.walk(start_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if file.endswith(('.html', '.py', '.txt', '.md', '.css', '.js')):
                    rename_in_file(os.path.join(root, file))
                    count += 1

if __name__ == '__main__':
    main()
