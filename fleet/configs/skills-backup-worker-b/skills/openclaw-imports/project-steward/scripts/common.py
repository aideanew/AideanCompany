import os
from pathlib import Path
from rich.console import Console

# Constants
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
SKILL_ROOT = Path(__file__).parent.parent.absolute()
ASSETS_DIR = SKILL_ROOT / "assets"
DOCS_DIR = PROJECT_ROOT / "docs"
STRUCTURE_FILE = DOCS_DIR / "structure.md"
ROADMAP_FILE = DOCS_DIR / "roadmap.md"
ERRORS_FILE = DOCS_DIR / "errors.md"
CACHE_DIR = PROJECT_ROOT / ".steward_cache"

# Console for rich output
console = Console()

def get_project_root() -> Path:
    return PROJECT_ROOT

def ensure_docs_dir():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
