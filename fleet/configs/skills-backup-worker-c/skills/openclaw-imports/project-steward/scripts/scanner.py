import ast
import os
import pathspec
from pathlib import Path
from typing import List, Dict, Optional
from xml.sax.saxutils import escape
from common import PROJECT_ROOT, console

class Scanner:
    def __init__(self, root: Path):
        self.root = root
        self.gitignore = self._load_gitignore()

    def _load_gitignore(self) -> pathspec.PathSpec:
        gitignore_path = self.root / ".gitignore"
        lines = []
        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        # Add default ignores
        lines.extend([".git", "__pycache__", ".steward_cache", "node_modules", ".venv", "venv"])
        return pathspec.PathSpec.from_lines("gitwildmatch", lines)

    def scan(self) -> str:
        """Scans the project and returns an XML string representation."""
        xml_output = ["<project>"]
        
        for root, dirs, files in os.walk(self.root):
            # Filter directories
            dirs[:] = [d for d in dirs if not self.gitignore.match_file(os.path.join(root, d))]
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.root)
                
                if self.gitignore.match_file(str(rel_path)):
                    continue
                    
                # Skip binary files and large files
                if self._is_binary(file_path):
                    continue

                file_info = self._analyze_file(file_path, rel_path)
                xml_output.append(file_info)

        xml_output.append("</project>")
        return "\n".join(xml_output)

    def _is_binary(self, path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                return b"\0" in f.read(1024)
        except Exception:
            return True

    def _analyze_file(self, path: Path, rel_path: Path) -> str:
        """Analyzes a single file and returns its XML representation."""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

        extension = path.suffix.lower()
        summary = ""
        symbols_xml = ""

        if extension == ".py":
            summary, symbols = self._analyze_python(content)
            if symbols:
                symbols_xml = "\n    <symbols>\n" + "\n".join(symbols) + "\n    </symbols>"

        # Construct XML entry
        entry = [f'  <file path="{rel_path}">']
        if summary:
            entry.append(f'    <summary>{escape(summary)}</summary>')
        if symbols_xml:
            entry.append(symbols_xml)
        entry.append('  </file>')
        
        return "\n".join(entry)

    def _analyze_python(self, content: str) -> tuple[str, List[str]]:
        """Extracts module docstring and top-level symbols using AST."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return "", []

        module_doc = ast.get_docstring(tree) or ""
        symbols = []

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ""
                symbols.append(f'      <function name="{node.name}">{escape(doc)}</function>')
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                symbols.append(f'      <class name="{node.name}">{escape(doc)}</class>')
        
        return module_doc, symbols

if __name__ == "__main__":
    scanner = Scanner(PROJECT_ROOT)
    print(scanner.scan())
