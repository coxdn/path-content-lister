import sys
import os

root_path = sys.argv[1] if len(sys.argv) > 1 else '.'

excludes = {'venv', '.idea', '__pycache__', '.git'}


def scan_directory(path):
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if d not in excludes]
        for file in files:
            yield os.path.relpath(os.path.join(root, file), start=path)


def list_files(files):
    with open('out.txt', 'w') as out_file:
        for file in files:
            full_path = os.path.join(root_path, file)
            out_file.write(f"file listing {file}:\n")
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                out_file.write(content + '\n-------------\n')
            except Exception as e:
                out_file.write(f"Error reading file {file}: {str(e)}\n-------------\n")


if __name__ == '__main__':
    all_files = list(scan_directory(root_path))
    for index, file in enumerate(all_files, 1):
        print(f"{index}. {file}")

    selected_indices = input("Enter the file numbers you want to list (separated by spaces): ")
    selected_files = [all_files[int(index) - 1] for index in selected_indices.split()]

    list_files(selected_files)
    print("Files have been listed in 'out.txt'.")
