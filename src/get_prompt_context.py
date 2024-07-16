import fire
import os
import pathspec
import pyperclip
import subprocess
from datetime import datetime
from pathlib import Path

def load_gitignore_patterns(directory):
    patterns = []
    for root, _, files in os.walk(directory):
        if '.gitignore' in files:
            gitignore_path = os.path.join(root, '.gitignore')
            with open(gitignore_path, 'r') as gitignore:
                adjusted_patterns = [os.path.relpath(os.path.join(root, line.strip()), directory) for line in gitignore if line.strip() and not line.startswith('#')]
                patterns.extend(adjusted_patterns)
    return patterns

def is_empty_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read().strip()
    return len(content) == 0

def get_files(directory, ignore_patterns, include_empty_files, file_types, exclude_paths):
    matched_files = []
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.relpath(os.path.join(root, file), directory)
            if any(file.endswith(ft) for ft in file_types) and not spec.match_file(file_path):
                if not any(file_path.startswith(ep) for ep in exclude_paths):
                    if include_empty_files or not is_empty_file(os.path.join(root, file)):
                        matched_files.append(file_path)
    return matched_files

def write_files_to_txt(file_paths, output_file, base_dir, notebook_files, include_empty_files):
    with open(output_file, 'w') as outfile:
        # Write the project tree structure to the file
        tree_output = subprocess.check_output(['tree', '-I', '__pycache__|data|misc|venv', '--prune', base_dir], text=True)
        outfile.write(f"Project Structure:\n```\n{tree_output}```\n\n")

        # Add note about empty files
        if not include_empty_files:
            outfile.write("Note: Empty files are not included in the list.\n\n")

        # Write the files to the file
        for file_path in file_paths:
            absolute_path = os.path.join(base_dir, file_path)
            with open(absolute_path, 'r') as infile:
                content = infile.read()
            if file_path.endswith('.py'):
                outfile.write(f"{file_path}\n```py\n{content}```\n\n")
            elif file_path.endswith('.md'):
                outfile.write(f"{file_path}\n```markdown\n{content}```\n\n")
            elif file_path.endswith('.html'):
                outfile.write(f"{file_path}\n```html\n{content}```\n\n")
            else:
                outfile.write(f"{file_path}\n```plaintext\n{content}```\n\n")

        # Write the notebook files to the file
        for notebook_path, py_file_path in notebook_files.items():
            absolute_path = os.path.join(base_dir, py_file_path)
            with open(absolute_path, 'r') as infile:
                code = infile.read()
            outfile.write(f"{notebook_path}\n```ipynb\n{code}\n```\n\n")

def convert_notebooks_to_python(notebooks_dir, output_dir, ignore_patterns):
    notebook_files = {}
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    for root, _, files in os.walk(notebooks_dir):
        for file in files:
            file_path = os.path.relpath(os.path.join(root, file), notebooks_dir)
            if file.endswith('.ipynb') and not spec.match_file(file_path):
                notebook_path = os.path.join(root, file)
                command = f'jupyter nbconvert --to script --no-prompt "{notebook_path}" --output-dir="{output_dir}" > /dev/null 2>&1'
                os.system(command)
                py_file_path = os.path.join(output_dir, Path(file).stem + '.py')
                notebook_files[file_path] = py_file_path
    return notebook_files

def get_notebooks_dirs(directory):
    notebooks_dirs = []
    for root, dirs, _ in os.walk(directory):
        if 'notebooks' in dirs:
            notebooks_dirs.append(os.path.join(root, 'notebooks'))
    return notebooks_dirs

def process_code(target_directory='Python/', exclude_paths=None, *file_types):
    # Convert exclude_paths to a list if it's a string
    if isinstance(exclude_paths, str):
        exclude_paths = [exclude_paths]
    elif exclude_paths is None:
        exclude_paths = []

    empties = False

    if not file_types:
        file_types = ['.py', '.md', '.ipynb', '.js', '.html', '.css', '.json', '.yaml']
    notebooks = '.ipynb' in file_types


    PROJECT_DIR = Path(__file__).resolve().parent.parent
    target_directory = Path(target_directory).resolve()
    
    MISC_DIR = PROJECT_DIR / 'misc'
    DATA_DIR = MISC_DIR / 'data'
    HISTORY_DIR = DATA_DIR / 'history'
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    # Set filename
    relative_target = target_directory.relative_to(PROJECT_DIR)
    if target_directory != PROJECT_DIR:
        filename = f'{relative_target.as_posix().replace("/", "_")}_code'
    else:
        filename = f'all_project_code'
    filename_notebook_suffix = 'with_notebooks' if notebooks else 'no_notebooks'
    filename_empty_suffix = 'with_empty' if empties else 'no_empty'
    file_types_suffix = '_'.join([ft[1:] for ft in file_types])
    suffix = f'_{filename_notebook_suffix}_{filename_empty_suffix}_{file_types_suffix}.txt'
    filename += suffix

    NOTEBOOKS_DIRS = get_notebooks_dirs(target_directory)
    os.chdir(PROJECT_DIR)
    
    ignore_patterns = load_gitignore_patterns(PROJECT_DIR)
    
    notebook_files = {}
    if notebooks:
        for NOTEBOOKS_DIR in NOTEBOOKS_DIRS:
            notebooks = convert_notebooks_to_python(NOTEBOOKS_DIR, MISC_DIR / 'python', ignore_patterns)
            notebooks = {str(Path(NOTEBOOKS_DIR).relative_to(PROJECT_DIR) / nb): py for nb, py in notebooks.items()}
            notebook_files.update(notebooks)
    
    file_paths = get_files(target_directory, ignore_patterns, empties, file_types)

    # Determine the base directory for reading files
    base_dir = target_directory if target_directory != PROJECT_DIR else PROJECT_DIR

    output_file_path = DATA_DIR / filename
    write_files_to_txt(file_paths, output_file_path, base_dir, notebook_files, empties)
    
    # Copy the contents of the output file to the clipboard
    with open(output_file_path, 'r') as file:
        file_content = file.read()
        pyperclip.copy(file_content)
    
    # Save the historical version
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    historical_file_path = HISTORY_DIR / f'{Path(filename).stem}_{timestamp}.txt'
    with open(historical_file_path, 'w') as file:
        file.write(file_content)
    
    print(f"All specified files have been written to {output_file_path} and copied to the clipboard.")
    print(f"Historical version saved as {historical_file_path}")


if __name__ == '__main__':
    # fire lets you call the function from the command line, e.g. `python misc/get_full_python.py --nonotebooks --noempties --noreadmes`
    fire.Fire(process_code)
