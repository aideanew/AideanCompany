import re
from pathlib import Path
from typing import List, Optional, Dict
from common import ROADMAP_FILE, console
from datetime import datetime

class Locker:
    def __init__(self):
        self.roadmap_path = ROADMAP_FILE
        if not self.roadmap_path.exists():
            self._create_roadmap()

    def _create_roadmap(self):
        content = "# Roadmap\n\n- [ ] Initial Setup (id: init)"
        self.roadmap_path.write_text(content, encoding="utf-8")

    def get_active_task(self) -> Optional[Dict[str, str]]:
        """Returns the currently active (in-progress) task."""
        content = self.roadmap_path.read_text(encoding="utf-8")
        # Match task with status [/] or [Status: In Progress]
        # Regex to capture name and id
        # Format: - [Status] Name (id: ID) ...
        
        # Supporting user's detailed format:
        # - [/] Task Name (id: ID) ...
        match = re.search(r'- \[\/\] (.*?) \(id: (.*?)\)', content)
        if match:
            return {"name": match.group(1), "id": match.group(2)}
        return None

    def lock_task(self, task_id: str, files: List[str]) -> bool:
        """Marks a task as in-progress and associates files."""
        content = self.roadmap_path.read_text(encoding="utf-8")
        
        # Regex to find the task line (loose matching for various states)
        # Matches: - [?] Name (id: task_id) ...
        pattern = re.compile(r'- \[[ x\/]\] (.*?) \(id: ' + re.escape(task_id) + r'\)(.*)', re.MULTILINE)
        match = pattern.search(content)
        
        if not match:
            console.print(f"[red]Task {task_id} not found.[/red]")
            return False

        task_name = match.group(1)
        # rest contains existing metadata like Start Time, etc. We preserve what we can but update status.
        
        files_str = ", ".join(files)
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # New format compliant with user requirements:
        # - [/] TaskName (id: ID) [Lock: Locked] [Progress: In Progress] [Start: Time] [Files: ...]
        
        new_line = f'- [/] {task_name} (id: {task_id}) [Lock: Locked] [Progress: In Progress] [Start: {start_time}] [Files: {files_str}]'
        
        new_content = content.replace(match.group(0), new_line)
        self.roadmap_path.write_text(new_content, encoding="utf-8")
        console.print(f"[green]Task {task_id} locked with {len(files)} files.[/green]")
        return True

    def commit_task(self, task_id: str) -> bool:
        """Marks a task as done and removes locks."""
        content = self.roadmap_path.read_text(encoding="utf-8")
        
        pattern = re.compile(r'- \[\/\] (.*?) \(id: ' + re.escape(task_id) + r'\)(.*)', re.MULTILINE)
        match = pattern.search(content)
        
        if not match:
            console.print(f"[red]Active task {task_id} not found.[/red]")
            return False

        task_name = match.group(1)
        rest = match.group(2) 
        
        # Parse out start time if present to keep it? simplified for now.
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Unlock and Mark Done
        # - [x] TaskName (id: ID) [Lock: Unlocked] [Progress: Completed] [End: Time] ...
        
        # Extract previous files if possible, or just keep the text? 
        # Let's try to preserve the [Files: ...] part if it exists in 'rest'
        files_part = ""
        files_match = re.search(r'\[Files: (.*?)\]', rest)
        if files_match:
            files_part = f" [Files: {files_match.group(1)}]"

        new_line = f'- [x] {task_name} (id: {task_id}) [Lock: Unlocked] [Progress: Completed] [End: {end_time}]{files_part}'
        
        new_content = content.replace(match.group(0), new_line)
        self.roadmap_path.write_text(new_content, encoding="utf-8")
        console.print(f"[green]Task {task_id} completed.[/green]")
        return True

    def add_task(self, title: str, task_id: str, parent_id: Optional[str] = None) -> bool:
        """Adds a new task to the roadmap."""
        content = self.roadmap_path.read_text(encoding="utf-8")
        
        # Check if ID exists
        if f"(id: {task_id})" in content:
            console.print(f"[red]Task ID {task_id} already exists.[/red]")
            return False
            
        new_task_line = f"- [ ] {title} (id: {task_id})"
        
        if parent_id:
            # Find parent and append indented
            pattern = re.compile(r'(.*?) \(id: ' + re.escape(parent_id) + r'\)(.*)', re.MULTILINE)
            match = pattern.search(content)
            if match:
                # Determine parent indentation
                parent_line = match.group(0)
                indent = len(parent_line) - len(parent_line.lstrip())
                child_indent = " " * (indent + 2)
                
                # Insert after parent (and its current children?)
                # This is tricky with regex. Simple append after parent line is safest for now.
                insertion_point = match.end()
                new_content = content[:insertion_point] + f"\n{child_indent}{new_task_line}" + content[insertion_point:]
                self.roadmap_path.write_text(new_content, encoding="utf-8")
                console.print(f"[green]Subtask {task_id} added under {parent_id}.[/green]")
                return True
            else:
                console.print(f"[red]Parent ID {parent_id} not found. Appending to root.[/red]")
        
        # Append to end if no parent or parent not found
        with open(self.roadmap_path, "a", encoding="utf-8") as f:
            f.write(f"\n{new_task_line}")
        console.print(f"[green]Task {task_id} added to roadmap.[/green]")
        return True

if __name__ == "__main__":
    locker = Locker()
