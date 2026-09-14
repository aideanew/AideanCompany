import ast
from pathlib import Path
from typing import List, Tuple
from common import console

class Validator:
    def validate(self, file_path: Path) -> bool:
        """Validates docstrings in a file. Returns True if valid."""
        if file_path.suffix != ".py":
            # Currently only supports Python
            return True

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception as e:
            console.print(f"[red]Error parsing {file_path}: {e}[/red]")
            return False

        missing = []

        # Check module docstring
        if not ast.get_docstring(tree):
            missing.append("Module level docstring")

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    missing.append(f"Function '{node.name}'")
            elif isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    missing.append(f"Class '{node.name}'")
                # Check methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not ast.get_docstring(item):
                            missing.append(f"Method '{node.name}.{item.name}'")

        if missing:
            console.print(f"[yellow]Docstring validation failed for {file_path.name}:[/yellow]")
            for item in missing:
                console.print(f"  - Missing {item}")
            return False
        
        console.print(f"[green]{file_path.name} passed validation.[/green]")
        return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        Validator().validate(Path(sys.argv[1]))
