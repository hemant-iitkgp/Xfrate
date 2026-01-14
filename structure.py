import os

def print_tree(path, prefix=""):
    try:
        items = sorted(os.listdir(path))
    except PermissionError:
        return

    for index, item in enumerate(items):
        full_path = os.path.join(path, item)
        connector = "└── " if index == len(items) - 1 else "├── "
        print(prefix + connector + item)

        if os.path.isdir(full_path):
            extension = "    " if index == len(items) - 1 else "│   "
            print_tree(full_path, prefix + extension)

# Change this to your folder path
root_folder = "."
print_tree(root_folder)
