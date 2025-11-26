"""
Python Code Analyzer - Function Interaction and Dependency Mapper
Scans a Python project and creates a knowledge graph of function interactions,
parameters, and dependencies.
"""

import ast
import os
import sys
import re
import fnmatch
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json


# Compatibility for ast.unparse (Python 3.9+)
if sys.version_info >= (3, 9):
    def unparse_ast(node):
        return ast.unparse(node)
else:
    def unparse_ast(node):
        """Fallback for Python < 3.9 - returns simplified representation."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Attribute):
            return f"{unparse_ast(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return f"{unparse_ast(node.func)}()"
        else:
            return str(type(node).__name__)


@dataclass
class FunctionInfo:
    """Information about a Python function."""
    name: str
    file_path: str
    line_number: int
    parameters: List[str] = field(default_factory=list)
    return_annotation: Optional[str] = None
    docstring: Optional[str] = None
    calls: Set[str] = field(default_factory=set)  # Functions this function calls
    called_by: Set[str] = field(default_factory=set)  # Functions that call this
    decorators: List[str] = field(default_factory=list)
    is_method: bool = False
    class_name: Optional[str] = None


@dataclass
class ClassInfo:
    """Information about a Python class."""
    name: str
    file_path: str
    line_number: int
    methods: List[str] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)


class GitIgnoreParser:
    """Parser for .gitignore files."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.patterns: List[Tuple[str, bool, bool]] = []  # (pattern, is_negation, is_directory)
        self._load_gitignore_files()
    
    def _load_gitignore_files(self):
        """Load all .gitignore files in the project."""
        gitignore_files = list(self.project_root.rglob(".gitignore"))
        
        for gitignore_file in gitignore_files:
            try:
                with open(gitignore_file, 'r', encoding='utf-8') as f:
                    gitignore_dir = gitignore_file.parent
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if not line or line.startswith('#'):
                            continue
                        
                        # Check for negation
                        is_negation = line.startswith('!')
                        if is_negation:
                            pattern = line[1:]
                        else:
                            pattern = line
                        
                        # Check if it's a directory pattern (ends with /)
                        is_directory = pattern.endswith('/')
                        if is_directory:
                            pattern = pattern[:-1]
                        
                        # Store pattern with its relative path context
                        if not os.path.isabs(pattern):
                            # Make pattern relative to gitignore file location
                            rel_to_root = gitignore_dir.relative_to(self.project_root)
                            if rel_to_root != Path('.'):
                                pattern = str(rel_to_root / pattern)
                        
                        self.patterns.append((pattern, is_negation, is_directory))
            except Exception as e:
                print(f"Warning: Could not read {gitignore_file}: {e}")
    
    def _matches_pattern(self, path: Path, pattern: str, is_directory: bool) -> bool:
        """Check if a path matches a gitignore pattern."""
        # Convert path to relative path from project root
        try:
            rel_path = path.relative_to(self.project_root)
        except ValueError:
            return False
        
        # Convert to string with forward slashes for pattern matching
        path_str = str(rel_path).replace('\\', '/')
        path_parts = path_str.split('/')
        
        # Normalize pattern (remove leading slash if present, it means root-relative)
        pattern = pattern.lstrip('/')
        
        # Handle directory patterns
        if is_directory:
            # For directory patterns, check if any directory in the path matches
            return any(fnmatch.fnmatch(part, pattern) for part in path_parts)
        
        # Handle patterns with path separators (e.g., "subdir/file.py")
        if '/' in pattern:
            # Check if pattern matches the end of the path or any subpath
            pattern_parts = pattern.split('/')
            # Try matching from different starting positions
            for i in range(len(path_parts) - len(pattern_parts) + 1):
                subpath = '/'.join(path_parts[i:i+len(pattern_parts)])
                if fnmatch.fnmatch(subpath, pattern):
                    return True
            return False
        else:
            # Simple pattern (no path separators) - matches filename or any directory name
            # Check filename
            if fnmatch.fnmatch(path_parts[-1], pattern):
                return True
            # Check any directory name in path
            return any(fnmatch.fnmatch(part, pattern) for part in path_parts[:-1])
    
    def should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored based on .gitignore rules."""
        is_dir = path.is_dir()
        matches_ignore = False
        matches_negation = False
        
        for pattern, is_negation, is_directory in self.patterns:
            # Skip directory patterns if checking a file
            if is_directory and not is_dir:
                continue
            
            if self._matches_pattern(path, pattern, is_directory):
                if is_negation:
                    matches_negation = True
                else:
                    matches_ignore = True
        
        # Negation patterns override ignore patterns
        if matches_negation:
            return False
        return matches_ignore


class CodeAnalyzer:
    """Analyzes Python code to extract function interactions and dependencies."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.gitignore = GitIgnoreParser(self.project_root)
        self.functions: Dict[str, FunctionInfo] = {}  # full_name -> FunctionInfo
        self.classes: Dict[str, ClassInfo] = {}  # full_name -> ClassInfo
        self.imports: Dict[str, Set[str]] = defaultdict(set)  # file -> imported modules
        self.import_details: Dict[str, List[Dict]] = defaultdict(list)  # file -> [{"from": module, "imports": [names], "is_relative": bool}]
        self.file_functions: Dict[str, List[str]] = defaultdict(list)  # file -> function names
        
        # Hierarchy tracking: Folder -> File -> Module -> Function
        self.folders: Dict[str, Dict] = {}  # folder_path -> {files: [], subfolders: []}
        self.files: Dict[str, Dict] = {}  # file_path -> {module: str, folder: str, functions: []}
        self.modules: Dict[str, Dict] = {}  # module_name -> {file: str, functions: [], classes: []}
        
    def _get_full_function_name(self, name: str, class_name: Optional[str] = None, 
                                file_path: str = "") -> str:
        """Generate a unique full name for a function."""
        if class_name:
            return f"{file_path}::{class_name}.{name}"
        return f"{file_path}::{name}"
    
    def _get_relative_path(self, file_path: Path) -> str:
        """Get relative path from project root."""
        try:
            return str(file_path.relative_to(self.project_root))
        except ValueError:
            return str(file_path)
    
    def _get_module_name(self, file_path: str) -> str:
        """Extract module name from file path."""
        # Convert file path to module name
        # e.g., "sample_project/models.py" -> "sample_project.models"
        module_path = file_path.replace('\\', '/').replace('/', '.')
        if module_path.endswith('.py'):
            module_path = module_path[:-3]
        # Remove __init__ suffix if present
        if module_path.endswith('.__init__'):
            module_path = module_path[:-9]
        return module_path
    
    def _resolve_relative_import(self, import_module: str, current_file: str) -> Optional[str]:
        """Resolve relative import (e.g., '.models') to actual module name."""
        if not import_module or not import_module.startswith('.'):
            return import_module
        
        # Get current module path
        current_module = self._get_module_name(current_file)
        
        # Count dots to determine relative level
        dots = 0
        module_part = import_module
        while module_part.startswith('.'):
            dots += 1
            module_part = module_part[1:]
        
        if not module_part:
            # Just dots, means parent package
            parts = current_module.split('.')
            if dots <= len(parts):
                return '.'.join(parts[:-(dots-1)]) if dots > 1 else '.'.join(parts[:-1])
            return None
        
        # Resolve relative path
        parts = current_module.split('.')
        if dots == 1:
            # Same package
            parent = '.'.join(parts[:-1]) if len(parts) > 1 else ''
            return f"{parent}.{module_part}" if parent else module_part
        else:
            # Go up N levels
            if dots - 1 <= len(parts):
                parent = '.'.join(parts[:-(dots-1)])
                return f"{parent}.{module_part}"
            return None
    
    def _get_folder_path(self, file_path: str) -> str:
        """Extract folder path from file path."""
        # Get directory containing the file
        path_obj = Path(file_path)
        if path_obj.is_absolute():
            try:
                folder = path_obj.parent.relative_to(self.project_root)
            except ValueError:
                folder = path_obj.parent
        else:
            folder = Path(file_path).parent
        
        # Normalize path to use forward slashes for consistency
        folder_str = str(folder).replace('\\', '/') if str(folder) != '.' else ''
        return folder_str
    
    def _register_file_in_hierarchy(self, file_path: str, relative_path: str):
        """Register file in folder/module hierarchy."""
        folder_path = self._get_folder_path(relative_path)
        file_ext = Path(relative_path).suffix
        
        # Only extract module name for Python files
        module_name = self._get_module_name(relative_path) if file_ext == '.py' else None
        
        # Register folder
        if folder_path not in self.folders:
            self.folders[folder_path] = {
                "path": folder_path,
                "files": [],
                "subfolders": set()
            }
        
        # Register file (all file types)
        if relative_path not in self.files:
            self.files[relative_path] = {
                "path": relative_path,
                "name": Path(relative_path).name,
                "extension": file_ext,
                "module": module_name,
                "folder": folder_path,
                "functions": [],
                "is_python": file_ext == '.py'
            }
            self.folders[folder_path]["files"].append(relative_path)
        
        # Register module (only for Python files)
        if module_name and module_name not in self.modules:
            self.modules[module_name] = {
                "name": module_name,
                "file": relative_path,
                "folder": folder_path,
                "functions": [],
                "classes": []
            }
        
        # Update folder hierarchy (track parent folders recursively)
        if folder_path:
            # Normalize path separators
            folder_path = folder_path.replace('\\', '/')
            parts = folder_path.split('/') if folder_path else []
            
            for i in range(len(parts) + 1):
                parent_folder = '/'.join(parts[:i]) if i > 0 else ''
                
                if parent_folder not in self.folders:
                    self.folders[parent_folder] = {
                        "path": parent_folder,
                        "files": [],
                        "subfolders": set()
                    }
                
                if i < len(parts):
                    child_folder = '/'.join(parts[:i+1])
                    self.folders[parent_folder]["subfolders"].add(child_folder)
    
    def _extract_docstring(self, node) -> Optional[str]:
        """Extract docstring from AST node."""
        if (isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
        return None
    
    def _extract_parameters(self, node: ast.FunctionDef) -> List[str]:
        """Extract parameter names and annotations."""
        params = []
        for arg in node.args.args:
            param_name = arg.arg
            if arg.annotation:
                param_name += f": {unparse_ast(arg.annotation)}"
            params.append(param_name)
        return params
    
    def _extract_decorators(self, node: ast.FunctionDef) -> List[str]:
        """Extract decorator names."""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(unparse_ast(decorator))
            elif isinstance(decorator, ast.Call):
                decorators.append(unparse_ast(decorator.func))
        return decorators
    
    def _extract_function_calls(self, node: ast.AST, 
                                current_class: Optional[str] = None,
                                current_file: str = "") -> Set[str]:
        """Recursively extract function calls from AST node."""
        calls = set()
        
        class CallVisitor(ast.NodeVisitor):
            def __init__(self, calls_set, current_class, current_file):
                self.calls = calls_set
                self.current_class = current_class
                self.current_file = current_file
            
            def visit_Call(self, node):
                # Extract function name
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    # Check if it's a method call
                    calls.add(f"{self.current_file}::{func_name}")
                elif isinstance(node.func, ast.Attribute):
                    # Method call or attribute access
                    if isinstance(node.func.value, ast.Name):
                        # Could be self.method() or obj.method()
                        if node.func.value.id == 'self' and self.current_class:
                            calls.add(f"{self.current_file}::{self.current_class}.{node.func.attr}")
                        else:
                            calls.add(f"{self.current_file}::{node.func.attr}")
                    elif isinstance(node.func.value, ast.Call):
                        # Chained call
                        calls.add(f"{self.current_file}::{node.func.attr}")
                self.generic_visit(node)
        
        visitor = CallVisitor(calls, current_class, current_file)
        visitor.visit(node)
        return calls
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            relative_path = self._get_relative_path(file_path)
            
            # Register file in hierarchy
            self._register_file_in_hierarchy(str(file_path), relative_path)
            
            current_class = None
            
            class Visitor(ast.NodeVisitor):
                def __init__(self, analyzer, file_path, relative_path):
                    self.analyzer = analyzer
                    self.file_path = file_path
                    self.relative_path = relative_path
                    self.current_class = None
                
                def visit_Import(self, node):
                    for alias in node.names:
                        module_name = alias.asname if alias.asname else alias.name
                        self.analyzer.imports[relative_path].add(alias.name)
                        self.analyzer.import_details[relative_path].append({
                            "from": alias.name,
                            "imports": [alias.name],
                            "is_relative": False,
                            "line": node.lineno
                        })
                    self.generic_visit(node)
                
                def visit_ImportFrom(self, node):
                    if node.module:
                        is_relative = node.level > 0  # level > 0 means relative import
                        resolved_module = self.analyzer._resolve_relative_import(
                            node.module, relative_path
                        ) if is_relative else node.module
                        
                        imported_names = [alias.name for alias in node.names]
                        
                        self.analyzer.imports[relative_path].add(node.module)
                        self.analyzer.import_details[relative_path].append({
                            "from": node.module,
                            "resolved_module": resolved_module,
                            "imports": imported_names,
                            "is_relative": is_relative,
                            "line": node.lineno
                        })
                    self.generic_visit(node)
                
                def visit_ClassDef(self, node):
                    class_name = node.name
                    full_class_name = f"{self.relative_path}::{class_name}"
                    
                    base_classes = [unparse_ast(base) for base in node.bases]
                    class_info = ClassInfo(
                        name=class_name,
                        file_path=self.relative_path,
                        line_number=node.lineno,
                        base_classes=base_classes
                    )
                    self.analyzer.classes[full_class_name] = class_info
                    
                    old_class = self.current_class
                    self.current_class = class_name
                    self.generic_visit(node)
                    self.current_class = old_class
                
                def visit_FunctionDef(self, node):
                    func_name = node.name
                    full_name = self.analyzer._get_full_function_name(
                        func_name, self.current_class, self.relative_path
                    )
                    
                    # Extract function information
                    params = self.analyzer._extract_parameters(node)
                    return_ann = unparse_ast(node.returns) if node.returns else None
                    docstring = self.analyzer._extract_docstring(node)
                    decorators = self.analyzer._extract_decorators(node)
                    
                    # Extract function calls
                    calls = self.analyzer._extract_function_calls(
                        node, self.current_class, self.relative_path
                    )
                    
                    func_info = FunctionInfo(
                        name=func_name,
                        file_path=self.relative_path,
                        line_number=node.lineno,
                        parameters=params,
                        return_annotation=return_ann,
                        docstring=docstring,
                        calls=calls,
                        decorators=decorators,
                        is_method=bool(self.current_class),
                        class_name=self.current_class
                    )
                    
                    self.analyzer.functions[full_name] = func_info
                    self.analyzer.file_functions[self.relative_path].append(full_name)
                    
                    # Register function in hierarchy
                    if self.relative_path in self.analyzer.files:
                        self.analyzer.files[self.relative_path]["functions"].append(full_name)
                    module_name = self.analyzer._get_module_name(self.relative_path)
                    if module_name in self.analyzer.modules:
                        self.analyzer.modules[module_name]["functions"].append(full_name)
                    
                    if self.current_class:
                        self.analyzer.classes[
                            f"{self.relative_path}::{self.current_class}"
                        ].methods.append(full_name)
                        # Register class in module
                        if module_name in self.analyzer.modules:
                            class_full_name = f"{self.relative_path}::{self.current_class}"
                            if class_full_name not in self.analyzer.modules[module_name]["classes"]:
                                self.analyzer.modules[module_name]["classes"].append(class_full_name)
                    
                    self.generic_visit(node)
            
            visitor = Visitor(self, file_path, relative_path)
            visitor.visit(tree)
            
        except SyntaxError as e:
            print(f"Warning: Syntax error in {file_path}: {e}")
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _build_call_graph(self):
        """Build bidirectional call graph relationships."""
        for func_name, func_info in self.functions.items():
            for called_func in func_info.calls:
                # Try to find the actual function
                # First, check exact match
                if called_func in self.functions:
                    self.functions[called_func].called_by.add(func_name)
                else:
                    # Try to find by name only (within same file)
                    file_path = func_info.file_path
                    for other_func_name, other_func_info in self.functions.items():
                        if (other_func_info.file_path == file_path and 
                            other_func_info.name == called_func.split('::')[-1].split('.')[-1]):
                            other_func_info.called_by.add(func_name)
    
    def _should_skip_path(self, path: Path) -> bool:
        """Check if a path should be skipped based on gitignore and common exclusions."""
        # Check gitignore first
        if self.gitignore.should_ignore(path):
            return True
        
        # Also check for common patterns that might not be in gitignore
        parts = path.parts
        for part in parts:
            # Skip hidden files/folders (except .gitignore itself)
            if part.startswith('.') and part != '.gitignore':
                return True
            # Skip common build/cache directories
            if part in ['__pycache__', 'node_modules', '.pytest_cache', '.mypy_cache']:
                return True
        
        return False
    
    def analyze(self) -> Dict:
        """Analyze the entire project recursively through all subfolders."""
        print(f"Analyzing project: {self.project_root}")
        
        # Check if .gitignore exists
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            print(f"Found .gitignore file - will respect ignore patterns")
            print(f"  Loaded {len(self.gitignore.patterns)} ignore patterns")
        
        # Find all files recursively (not just Python files)
        # We need to manually walk the directory tree to respect gitignore
        all_files = []
        python_files = []
        
        def walk_directory(dir_path: Path):
            """Recursively walk directory, respecting gitignore."""
            try:
                for item in dir_path.iterdir():
                    # Skip if matches gitignore
                    if self._should_skip_path(item):
                        continue
                    
                    if item.is_file():
                        all_files.append(item)
                        if item.suffix == '.py':
                            python_files.append(item)
                    elif item.is_dir():
                        # Recursively process subdirectories
                        walk_directory(item)
            except PermissionError:
                # Skip directories we can't access
                pass
        
        # Start walking from project root
        walk_directory(self.project_root)
        
        # Separate Python files for code analysis
        python_files = [f for f in all_files if f.suffix == '.py']
        
        print(f"Found {len(all_files)} total files")
        print(f"Found {len(python_files)} Python files (for code analysis)")
        
        # Register all files in hierarchy (not just Python files)
        for file_path in all_files:
            relative_path = self._get_relative_path(file_path)
            self._register_file_in_hierarchy(str(file_path), relative_path)
        
        # Show folder structure being analyzed
        folders_found = set()
        for file_path in all_files:
            relative_path = self._get_relative_path(file_path)
            folder = self._get_folder_path(relative_path)
            if folder:
                folders_found.add(folder)
        
        if folders_found:
            print(f"Scanning {len(folders_found)} folders (including subfolders):")
            for folder in sorted(folders_found):
                file_count = sum(1 for f in all_files if self._get_folder_path(self._get_relative_path(f)) == folder)
                py_count = sum(1 for f in python_files if self._get_folder_path(self._get_relative_path(f)) == folder)
                print(f"  📁 {folder}/ ({file_count} total files, {py_count} Python files)")
        
        # Analyze Python files for code structure
        for file_path in python_files:
            self._analyze_file(file_path)
        
        # Build call graph
        self._build_call_graph()
        
        print(f"\nAnalysis complete:")
        print(f"  • {len(self.folders)} folders processed")
        print(f"  • {len(self.files)} files tracked")
        print(f"  • {len(self.functions)} functions found")
        print(f"  • {len(self.classes)} classes found")
        print(f"  • {len(self.modules)} modules found")
        
        return self.get_summary()
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        total_params = sum(len(f.parameters) for f in self.functions.values())
        functions_with_docs = sum(1 for f in self.functions.values() if f.docstring)
        functions_with_calls = sum(1 for f in self.functions.values() if f.calls)
        functions_called = sum(1 for f in self.functions.values() if f.called_by)
        
        # Count folders (excluding root/empty)
        total_folders = len([f for f in self.folders.keys() if f])
        
        return {
            "total_folders": total_folders,
            "total_files": len(self.file_functions),
            "total_modules": len(self.modules),
            "total_functions": len(self.functions),
            "total_classes": len(self.classes),
            "total_parameters": total_params,
            "functions_with_docstrings": functions_with_docs,
            "functions_that_call_others": functions_with_calls,
            "functions_that_are_called": functions_called,
            "average_parameters_per_function": total_params / len(self.functions) if self.functions else 0
        }
    
    def get_graph_data(self) -> Dict:
        """Get graph data structure for visualization."""
        nodes = []
        edges = []
        
        # Add folder nodes
        for folder_path, folder_info in sorted(self.folders.items()):
            if folder_path:  # Skip root folder
                nodes.append({
                    "id": f"folder::{folder_path}",
                    "label": Path(folder_path).name if folder_path else "root",
                    "type": "folder",
                    "path": folder_path,
                    "file_count": len(folder_info["files"]),
                    "subfolder_count": len(folder_info["subfolders"])
                })
        
        # Add file nodes (all file types)
        for file_path, file_info in sorted(self.files.items()):
            nodes.append({
                "id": f"file::{file_path}",
                "label": file_info["name"],
                "type": "file",
                "path": file_path,
                "extension": file_info.get("extension", ""),
                "module": file_info.get("module"),
                "folder": file_info["folder"],
                "function_count": len(file_info.get("functions", [])),
                "is_python": file_info.get("is_python", False)
            })
        
        # Add module nodes
        for module_name, module_info in sorted(self.modules.items()):
            nodes.append({
                "id": f"module::{module_name}",
                "label": module_name.split('.')[-1],  # Just the module name, not full path
                "type": "module",
                "name": module_name,
                "file": module_info["file"],
                "folder": module_info["folder"],
                "function_count": len(module_info["functions"]),
                "class_count": len(module_info["classes"])
            })
        
        # Add function nodes
        for func_name, func_info in self.functions.items():
            module_name = self._get_module_name(func_info.file_path)
            folder_path = self._get_folder_path(func_info.file_path)
            node = {
                "id": func_name,
                "label": func_info.name,
                "type": "method" if func_info.is_method else "function",
                "file": func_info.file_path,
                "module": module_name,
                "folder": folder_path,
                "line": func_info.line_number,
                "parameters": func_info.parameters,
                "parameter_count": len(func_info.parameters),
                "has_docstring": bool(func_info.docstring),
                "call_count": len(func_info.calls),
                "called_by_count": len(func_info.called_by),
                "class": func_info.class_name
            }
            nodes.append(node)
        
        # Add hierarchy edges: folder -> file -> module -> function
        # Folder to File edges
        for file_path, file_info in self.files.items():
            if file_info["folder"]:
                edges.append({
                    "source": f"folder::{file_info['folder']}",
                    "target": f"file::{file_path}",
                    "type": "contains",
                    "relationship": "folder_contains_file"
                })
        
        # File to Module edges
        for file_path, file_info in self.files.items():
            edges.append({
                "source": f"file::{file_path}",
                "target": f"module::{file_info['module']}",
                "type": "defines",
                "relationship": "file_defines_module"
            })
        
        # Module to Function edges
        for module_name, module_info in self.modules.items():
            for func_name in module_info["functions"]:
                edges.append({
                    "source": f"module::{module_name}",
                    "target": func_name,
                    "type": "contains",
                    "relationship": "module_contains_function"
                })
        
        # Folder hierarchy edges (parent -> child)
        for folder_path, folder_info in self.folders.items():
            if folder_path:
                parent_parts = Path(folder_path).parts
                if len(parent_parts) > 0:
                    parent_folder = str(Path(*parent_parts[:-1])) if len(parent_parts) > 1 else ''
                    if parent_folder in self.folders:
                        edges.append({
                            "source": f"folder::{parent_folder}",
                            "target": f"folder::{folder_path}",
                            "type": "contains",
                            "relationship": "folder_contains_folder"
                        })
        
        # Add call edges
        for func_name, func_info in self.functions.items():
            for called_func in func_info.calls:
                if called_func in self.functions:
                    edges.append({
                        "source": func_name,
                        "target": called_func,
                        "type": "calls",
                        "relationship": "function_call"
                    })
        
        # Add called_by edges (reverse)
        for func_name, func_info in self.functions.items():
            for caller in func_info.called_by:
                edges.append({
                    "source": caller,
                    "target": func_name,
                    "type": "called_by",
                    "relationship": "dependency"
                })
        
        # Add import edges: file -> module (imports from)
        for importing_file, import_list in self.import_details.items():
            importing_module = self._get_module_name(importing_file)
            
            for import_info in import_list:
                imported_module = import_info.get("resolved_module") or import_info.get("from")
                
                # Try to find the imported module in our project
                target_module_id = None
                target_file_id = None
                
                # Check if it's a module we know about
                if imported_module in self.modules:
                    target_module_id = f"module::{imported_module}"
                    target_file_id = f"file::{self.modules[imported_module]['file']}"
                else:
                    # Try to find by partial match (e.g., "models" might match "sample_project.models")
                    for known_module in self.modules.keys():
                        if known_module.endswith(f".{imported_module}") or known_module == imported_module:
                            target_module_id = f"module::{known_module}"
                            target_file_id = f"file::{self.modules[known_module]['file']}"
                            break
                
                # Create edge from importing file to imported module/file
                if importing_file in self.files:
                    if target_file_id:
                        edges.append({
                            "source": f"file::{importing_file}",
                            "target": target_file_id,
                            "type": "imports",
                            "relationship": "file_imports_from_file",
                            "imports": import_info.get("imports", []),
                            "is_relative": import_info.get("is_relative", False)
                        })
                    if target_module_id:
                        edges.append({
                            "source": f"module::{importing_module}",
                            "target": target_module_id,
                            "type": "imports",
                            "relationship": "module_imports_from_module",
                            "imports": import_info.get("imports", []),
                            "is_relative": import_info.get("is_relative", False)
                        })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "summary": self.get_summary(),
            "hierarchy": {
                "folders": {k: {
                    "path": v["path"],
                    "files": v["files"],
                    "subfolders": list(v["subfolders"])
                } for k, v in self.folders.items()},
                "files": self.files,
                "modules": self.modules
            },
            "imports": {
                file_path: imports for file_path, imports in self.import_details.items()
            }
        }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = "."
    
    analyzer = CodeAnalyzer(project_root)
    analyzer.analyze()
    
    # Output graph data as JSON
    graph_data = analyzer.get_graph_data()
    print("\n" + "="*50)
    print("ANALYSIS SUMMARY")
    print("="*50)
    for key, value in graph_data["summary"].items():
        print(f"{key}: {value}")
    
    # Determine project folder name for results directory
    project_path = Path(project_root).resolve()
    if project_path.is_file():
        project_folder_name = project_path.parent.name
    elif str(project_path) == "." or str(project_path) == Path.cwd():
        project_folder_name = Path.cwd().name
    else:
        project_folder_name = project_path.name
    
    # Create results directory
    results_dir_name = f"{project_folder_name}_results"
    results_dir = Path(results_dir_name)
    results_dir.mkdir(exist_ok=True)
    
    # Save to JSON
    output_file = results_dir / "code_graph.json"
    with open(output_file, 'w') as f:
        json.dump(graph_data, f, indent=2)
    print(f"\nGraph data saved to {output_file}")

