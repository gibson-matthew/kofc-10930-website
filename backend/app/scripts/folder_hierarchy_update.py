import os
import json

def build_tree(root_path):
    tree = {}

    for current_path, dirs, files in os.walk(root_path):
        # Normalize path
        rel_path = os.path.relpath(current_path, root_path)
        parent = tree

        # Walk down the tree dict to the correct parent
        if rel_path != ".":
            for part in rel_path.split(os.sep):
                parent = parent.setdefault(part, {})

        # Add directories
        for d in dirs:
            parent.setdefault(d, {})

        # Add files
        for f in files:
            parent[f] = None  # None = leaf node (file)

    return tree


def format_for_llm(tree, indent=0):
    lines = []
    for name, content in tree.items():
        prefix = "  " * indent + "- " + name
        lines.append(prefix)
        if isinstance(content, dict):
            lines.extend(format_for_llm(content, indent + 1))
    return lines


if __name__ == "__main__":
    root = "./"
    tree = build_tree(root)
    output = "\n".join(format_for_llm(tree))

    print("=== Folder Hierarchy ===")
    print(output)

    # Optional: also save JSON for structured LLM consumption
    with open("folder_structure.json", "w") as f:
        json.dump(tree, f, indent=2)
