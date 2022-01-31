"""Functions relating to the parsing of sourcecode into functions, etc.
"""
import ast
from pathlib import Path
from typing import Optional

import intervaltree


class ScopeFinder:
    def __init__(self, filename: Path):
        self.tree = file_to_tree(filename)

    def query(self, lineno) -> Optional[str]:
        matches = self.tree[lineno]
        if matches:
            return ".".join(
                [
                    d.data.name
                    for d in sorted(matches, key=lambda i: i.length(), reverse=True)
                ]
            )
            # return min(matches, key=lambda i: i.length()).data.name

    def __getitem__(self, lineno: int) -> Optional[str]:
        return self.query(lineno)


def compute_size(node):
    min_lineno = node.lineno
    max_lineno = node.lineno
    for node in ast.walk(node):
        if hasattr(node, "lineno"):
            min_lineno = min(min_lineno, node.lineno)
            max_lineno = max(max_lineno, node.lineno)
    return (min_lineno, max_lineno + 1)


def file_to_tree(filename: Path):
    with filename.open("r") as f:
        parsed = ast.parse(f.read(), filename=str(filename))
    tree = intervaltree.IntervalTree()
    for node in ast.walk(parsed):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start, end = compute_size(node)
            tree[start:end] = node
    return tree


if __name__ == "__main__":
    file = Path(
        "/Users/latkins/charm/dragonligandfold/dragonligandfold/experiments/cotrain/full_ipa.py"
    )

    finder = ScopeFinder(file)

    with file.open("r") as f:
        for i, line in enumerate(f):
            print(f"{line.rstrip():20} | {finder[i]}")

    breakpoint()
