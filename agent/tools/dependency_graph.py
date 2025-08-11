# tools/dependency_graph.py
import ast
import os
from pathlib import Path
from typing import Dict, Set, List
from collections import defaultdict

ROOT_PATH = Path(__file__).parent.parent

class DependencyGraph:
    def __init__(self):
        self.defines: Dict[str, str] = {}  # name → file
        self.uses: Dict[str, Set[str]] = defaultdict(set)  # file → {names used}
        self.graph: Dict[str, Set[str]] = defaultdict(set)  # file → depends_on_file
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # file → used_by

    def parse_file(self, file_path: str):
        """Parse a single file to extract definitions and usages"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
        except Exception:
            return

        rel_path = os.path.relpath(file_path, ROOT_PATH)

        # Extract defined names
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.defines[node.name] = rel_path
            elif isinstance(node, ast.ClassDef):
                self.defines[node.name] = rel_path

        # Extract used names
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
        self.uses[rel_path] = used_names

    def build(self):
        """Scan all Python files and build full graph"""
        self.defines.clear()
        self.uses.clear()
        self.graph.clear()
        self.reverse_graph.clear()

        for root, _, files in os.walk(ROOT_PATH):
            for file in files:
                if file.endswith(".py") and "venv" not in root and "__pycache__" not in root:
                    self.parse_file(os.path.join(root, file))

        # Build file-to-file dependencies
        for file, used_names in self.uses.items():
            for name in used_names:
                if name in self.defines:
                    def_file = self.defines[name]
                    if def_file != file:
                        self.graph[file].add(def_file)
                        self.reverse_graph[def_file].add(file)

    def get_dependents(self, file_path: str) -> Set[str]:
        """Get all files that depend on this file"""
        rel_path = os.path.relpath(file_path, ROOT_PATH)
        return self.reverse_graph.get(rel_path, set())

    def get_dependencies(self, file_path: str) -> Set[str]:
        """Get all files this file depends on"""
        rel_path = os.path.relpath(file_path, ROOT_PATH)
        return self.graph.get(rel_path, set())

    def will_break_others(self, function_name: str) -> List[str]:
        """Check if changing this function breaks others"""
        broken = []
        for caller_file, used_names in self.uses.items():
            if function_name in used_names:
                def_file = self.defines.get(function_name)
                if def_file and os.path.relpath(caller_file, ROOT_PATH) != def_file:
                    broken.append(caller_file)
        return broken

    def update_capability_usage(self):
        """Update 'used_by' in capabilities registry"""
        from .capabilities_registry import load_capabilities, save_capabilities

        caps = load_capabilities()
        for module, funcs in caps.items():
            for name, data in funcs.items():
                file = data["file"]
                data["used_by"] = list(self.reverse_graph.get(file, []))
        save_capabilities(caps)