import os
import re
import ast
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union

logger = logging.getLogger('battle_arena')

class ImportFixer:
    """
    Utility class for analyzing and fixing import paths in Python files.
    Handles detecting, analyzing, and correcting import paths in a project.
    """
    
    def __init__(self, project_root: Union[str, Path]):
        """
        Initialize the import fixer with the project root directory.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = Path(project_root).resolve()
        self.module_map = {}  # Maps module names to file paths
        self.import_issues = {}  # Maps file paths to import issues
        self.fixed_files = set()  # Set of files that have been fixed
        
    def scan_project(self, exclude_dirs: List[str] = None) -> Dict[str, str]:
        """
        Scan the project directory to build a map of module names to file paths.
        
        Args:
            exclude_dirs: List of directory names to exclude from scanning
            
        Returns:
            Dictionary mapping module names to file paths
        """
        if exclude_dirs is None:
            exclude_dirs = ['venv', 'env', '.git', '__pycache__', 'build', 'dist']
            
        # Reset module map
        self.module_map = {}
        
        # Walk through project directory
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            # Process Python files
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.project_root)
                    
                    # Convert path to module name
                    module_path = str(rel_path).replace(os.sep, '.')
                    
                    # Handle __init__.py files
                    if file == '__init__.py':
                        # Get the package name
                        package_path = str(rel_path.parent).replace(os.sep, '.')
                        self.module_map[package_path] = str(file_path)
                    
                    # Regular modules
                    module_name = module_path[:-3]  # Remove .py extension
                    self.module_map[module_name] = str(file_path)
        
        logger.info(f"Found {len(self.module_map)} modules in project")
        return self.module_map
    
    def analyze_imports(self, file_path: Union[str, Path]) -> List[Dict]:
        """
        Analyze imports in a Python file to find potential issues.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            List of dictionaries describing import issues
        """
        file_path = Path(file_path)
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            # Parse the Python file
            tree = ast.parse(file_content)
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append({
                            'type': 'import',
                            'name': name.name,
                            'asname': name.asname,
                            'lineno': node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for name in node.names:
                        imports.append({
                            'type': 'from',
                            'module': module,
                            'name': name.name,
                            'asname': name.asname,
                            'level': node.level,
                            'lineno': node.lineno
                        })
            
            # Check each import
            for imp in imports:
                if imp['type'] == 'import':
                    module_name = imp['name']
                    if not self._is_valid_import(module_name) and not self._is_standard_library(module_name):
                        # Try to find a correct module name
                        suggestions = self._suggest_module_name(module_name)
                        issues.append({
                            'type': 'invalid_import',
                            'import_type': 'import',
                            'module': module_name,
                            'lineno': imp['lineno'],
                            'suggestions': suggestions
                        })
                        
                elif imp['type'] == 'from':
                    module_name = imp['module']
                    if imp['level'] > 0:  # Relative import
                        # Calculate the absolute module path
                        rel_path = file_path.relative_to(self.project_root)
                        parent_parts = list(rel_path.parent.parts)
                        
                        # Adjust for relative import level
                        if imp['level'] > len(parent_parts) + 1:
                            issues.append({
                                'type': 'invalid_relative_import',
                                'import_type': 'from',
                                'module': module_name,
                                'level': imp['level'],
                                'lineno': imp['lineno'],
                                'suggestions': []
                            })
                            continue
                            
                        # Calculate the absolute module path
                        absolute_module = '.'.join(parent_parts[:-imp['level']+1])
                        if module_name:
                            absolute_module = f"{absolute_module}.{module_name}"
                            
                        if not self._is_valid_import(absolute_module) and not self._is_standard_library(absolute_module):
                            suggestions = self._suggest_module_name(absolute_module)
                            issues.append({
                                'type': 'invalid_relative_import',
                                'import_type': 'from',
                                'module': module_name,
                                'level': imp['level'],
                                'lineno': imp['lineno'],
                                'suggestions': suggestions
                            })
                    else:  # Absolute import
                        if not self._is_valid_import(module_name) and not self._is_standard_library(module_name):
                            suggestions = self._suggest_module_name(module_name)
                            issues.append({
                                'type': 'invalid_import',
                                'import_type': 'from',
                                'module': module_name,
                                'lineno': imp['lineno'],
                                'suggestions': suggestions
                            })
                            
            # Store issues for this file
            self.import_issues[str(file_path)] = issues
            return issues
            
        except Exception as e:
            logger.error(f"Error analyzing imports in {file_path}: {str(e)}")
            return []
    
    def fix_imports(self, file_path: Union[str, Path], backup: bool = True) -> bool:
        """
        Fix import issues in a Python file.
        
        Args:
            file_path: Path to the Python file to fix
            backup: Whether to create a backup file before making changes
            
        Returns:
            True if the file was modified, False otherwise
        """
        file_path = Path(file_path)
        
        # Analyze imports if not already done
        if str(file_path) not in self.import_issues:
            self.analyze_imports(file_path)
            
        issues = self.import_issues.get(str(file_path), [])
        if not issues:
            logger.info(f"No import issues found in {file_path}")
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Create a backup if requested
            if backup:
                backup_path = str(file_path) + '.bak'
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
            # Fix each issue
            modified = False
            for issue in sorted(issues, key=lambda x: x['lineno'], reverse=True):
                if not issue['suggestions']:
                    continue
                    
                best_suggestion = issue['suggestions'][0]
                lineno = issue['lineno'] - 1  # Convert to 0-indexed
                
                if issue['import_type'] == 'import':
                    # Fix 'import module' statements
                    pattern = re.compile(r'import\s+' + re.escape(issue['module']))
                    lines[lineno] = pattern.sub(f'import {best_suggestion}', lines[lineno])
                    modified = True
                    
                elif issue['import_type'] == 'from':
                    if issue['type'] == 'invalid_relative_import':
                        # Fix relative imports by converting to absolute
                        rel_part = '.' * issue['level']
                        pattern = re.compile(r'from\s+' + re.escape(f"{rel_part}{issue['module']}"))
                        lines[lineno] = pattern.sub(f'from {best_suggestion}', lines[lineno])
                        modified = True
                    else:
                        # Fix 'from module import' statements
                        pattern = re.compile(r'from\s+' + re.escape(issue['module']))
                        lines[lineno] = pattern.sub(f'from {best_suggestion}', lines[lineno])
                        modified = True
            
            # Write back the modified file
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                self.fixed_files.add(str(file_path))
                logger.info(f"Fixed import issues in {file_path}")
                
            return modified
                
        except Exception as e:
            logger.error(f"Error fixing imports in {file_path}: {str(e)}")
            return False
    
    def fix_all_imports(self, extensions: List[str] = None, exclude_dirs: List[str] = None) -> Dict[str, List[Dict]]:
        """
        Scan the entire project and fix import issues in all files.
        
        Args:
            extensions: List of file extensions to process (default: ['.py'])
            exclude_dirs: List of directories to exclude
            
        Returns:
            Dictionary mapping file paths to lists of issues that were fixed
        """
        if extensions is None:
            extensions = ['.py']
            
        if exclude_dirs is None:
            exclude_dirs = ['venv', 'env', '.git', '__pycache__', 'build', 'dist']
            
        # Ensure we have a module map
        if not self.module_map:
            self.scan_project(exclude_dirs)
            
        # Reset fixed files
        self.fixed_files = set()
        fixed_issues = {}
        
        # Walk through project directory
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            # Process files with matching extensions
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = Path(root) / file
                    
                    # Analyze and fix imports
                    issues = self.analyze_imports(file_path)
                    if issues:
                        self.fix_imports(file_path)
                        fixed_issues[str(file_path)] = issues
        
        logger.info(f"Fixed import issues in {len(self.fixed_files)} files")
        return fixed_issues
    
    def generate_report(self) -> str:
        """
        Generate a report of import issues found in the project.
        
        Returns:
            String containing the report
        """
        if not self.import_issues:
            return "No import issues analyzed yet. Run scan_project() and analyze_imports() first."
            
        report = []
        report.append("# Import Issues Report")
        report.append(f"## Project: {self.project_root}")
        report.append(f"## Total files with issues: {len(self.import_issues)}")
        report.append(f"## Total fixed files: {len(self.fixed_files)}")
        report.append("")
        
        for file_path, issues in self.import_issues.items():
            if not issues:
                continue
                
            report.append(f"### {file_path}")
            report.append(f"Found {len(issues)} issues:")
            report.append("")
            
            for issue in issues:
                lineno = issue['lineno']
                if issue['type'] == 'invalid_import':
                    module = issue['module']
                    report.append(f"- Line {lineno}: Invalid import '{module}'")
                elif issue['type'] == 'invalid_relative_import':
                    level = issue['level']
                    module = issue['module']
                    rel_import = '.' * level + module
                    report.append(f"- Line {lineno}: Invalid relative import '{rel_import}'")
                
                if issue['suggestions']:
                    report.append(f"  Suggestions:")
                    for suggestion in issue['suggestions']:
                        report.append(f"  - {suggestion}")
                        
                report.append("")
                
            report.append("")
            
        return "\n".join(report)
    
    def _is_valid_import(self, module_name: str) -> bool:
        """
        Check if a module name is valid within the project.
        
        Args:
            module_name: The module name to check
            
        Returns:
            True if the module exists in the project, False otherwise
        """
        # Check if it's in our module map
        if module_name in self.module_map:
            return True
            
        # Check if it's a submodule of a package in our module map
        for existing_module in self.module_map:
            if module_name.startswith(existing_module + '.'):
                return True
                
        return False
    
    def _is_standard_library(self, module_name: str) -> bool:
        """
        Check if a module is part of the Python standard library.
        
        Args:
            module_name: The module name to check
            
        Returns:
            True if the module is in the standard library, False otherwise
        """
        # Get the base module (before the first dot)
        base_module = module_name.split('.')[0]
        
        # List of common standard library modules
        std_libs = {
            'abc', 'argparse', 'ast', 'asyncio', 'base64', 'collections', 'configparser',
            'contextlib', 'copy', 'csv', 'datetime', 'decimal', 'difflib', 'enum',
            'fileinput', 'fnmatch', 'functools', 'glob', 'gzip', 'hashlib', 'heapq',
            'hmac', 'html', 'http', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools',
            'json', 'logging', 'math', 'multiprocessing', 'operator', 'os', 'pathlib',
            'pickle', 'platform', 'pprint', 're', 'random', 'secrets', 'shutil',
            'signal', 'socket', 'sqlite3', 'statistics', 'string', 'subprocess',
            'sys', 'tempfile', 'threading', 'time', 'traceback', 'types',
            'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref', 'xml',
            'zipfile', 'zlib'
        }
        
        # Common third-party libraries that shouldn't trigger import fixes
        third_party = {
            'numpy', 'pandas', 'matplotlib', 'seaborn', 'sklearn', 'tensorflow',
            'torch', 'requests', 'flask', 'django', 'sqlalchemy', 'pytest',
            'bs4', 'selenium', 'PIL', 'cv2', 'pygame', 'pydantic', 'fastapi'
        }
        
        return base_module in std_libs or base_module in third_party
    
    def _suggest_module_name(self, module_name: str) -> List[str]:
        """
        Suggest correct module names for an invalid import.
        
        Args:
            module_name: The invalid module name
            
        Returns:
            List of suggested module names, sorted by relevance
        """
        if not self.module_map:
            self.scan_project()
            
        suggestions = []
        
        # Get the parts of the module name
        parts = module_name.split('.')
        base_module = parts[0]
        
        # Case 1: The module might exist with a different name
        for existing_module in self.module_map:
            # Direct matches
            if existing_module.lower() == module_name.lower():
                suggestions.append(existing_module)
                
            # Partial matches with similar structure
            existing_parts = existing_module.split('.')
            if len(parts) == len(existing_parts):
                similarity = sum(1 for a, b in zip(parts, existing_parts) if a.lower() == b.lower())
                if similarity >= max(1, len(parts) - 1):
                    suggestions.append(existing_module)
        
        # Case 2: It might be a submodule of an existing module
        for existing_module in self.module_map:
            if not module_name.startswith(existing_module):
                continue
                
            # Check if there's a file at the expected path
            suffix = module_name[len(existing_module):].lstrip('.')
            if not suffix:
                continue
                
            file_path = Path(self.module_map[existing_module])
            if file_path.name == '__init__.py':
                # Check if there's a file with the expected name
                expected_path = file_path.parent / f"{suffix.replace('.', '/')}.py"
                if expected_path.exists():
                    suggestions.append(module_name)
        
        # Case 3: It might be a module in a different location
        base_matches = [m for m in self.module_map if m.split('.')[-1] == base_module]
        for match in base_matches:
            if match not in suggestions:
                suggestions.append(match)
        
        # Case 4: Modules with similar name (edit distance)
        import difflib
        matches = difflib.get_close_matches(module_name, self.module_map.keys(), n=3, cutoff=0.6)
        for match in matches:
            if match not in suggestions:
                suggestions.append(match)
                
        return suggestions

# Helper functions

def fix_imports_in_file(file_path: str, project_root: str = None) -> bool:
    """
    Fix import issues in a single Python file.
    
    Args:
        file_path: Path to the Python file to fix
        project_root: Path to the project root (default: parent directory of file)
        
    Returns:
        True if the file was modified, False otherwise
    """
    file_path = Path(file_path).resolve()
    
    if project_root is None:
        # Try to find the project root (directory containing a recognizable project file)
        current = file_path.parent
        while current.parent != current:
            if any((current / marker).exists() for marker in ['setup.py', 'pyproject.toml', '.git']):
                project_root = current
                break
            current = current.parent
            
        if project_root is None:
            # Default to parent directory if no markers found
            project_root = file_path.parent
    
    # Create fixer and fix imports
    fixer = ImportFixer(project_root)
    fixer.scan_project()
    return fixer.fix_imports(file_path)

def fix_imports_in_project(project_root: str, extensions: List[str] = None, exclude_dirs: List[str] = None) -> Dict:
    """
    Fix import issues in an entire project.
    
    Args:
        project_root: Path to the project root directory
        extensions: List of file extensions to process (default: ['.py'])
        exclude_dirs: List of directories to exclude
        
    Returns:
        Dictionary mapping file paths to lists of issues that were fixed
    """
    fixer = ImportFixer(project_root)
    fixer.scan_project(exclude_dirs)
    return fixer.fix_all_imports(extensions, exclude_dirs)

def generate_import_report(project_root: str, exclude_dirs: List[str] = None) -> str:
    """
    Generate a report of import issues found in a project.
    
    Args:
        project_root: Path to the project root directory
        exclude_dirs: List of directories to exclude
        
    Returns:
        String containing the report
    """
    fixer = ImportFixer(project_root)
    fixer.scan_project(exclude_dirs)
    
    # Analyze imports in all Python files
    for module_path in fixer.module_map.values():
        fixer.analyze_imports(module_path)
        
    # Generate the report
    return fixer.generate_report()

def find_circular_imports(project_root: str, exclude_dirs: List[str] = None) -> Dict[str, List[List[str]]]:
    """
    Find circular imports in a project.
    
    Args:
        project_root: Path to the project root directory
        exclude_dirs: List of directories to exclude
        
    Returns:
        Dictionary mapping module names to lists of circular import chains
    """
    # Initialize the import fixer to get a module map
    fixer = ImportFixer(project_root)
    fixer.scan_project(exclude_dirs)
    
    # Build a dependency graph
    graph = {}
    for module_path in fixer.module_map.values():
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            # Parse the Python file
            tree = ast.parse(file_content)
            
            # Get the module name
            rel_path = Path(module_path).relative_to(fixer.project_root)
            module_name = str(rel_path).replace(os.sep, '.')
            if module_name.endswith('.py'):
                module_name = module_name[:-3]
                
            # Extract imports
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.add(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
            
            # Add to graph
            graph[module_name] = list(imports)
            
        except Exception as e:
            logger.error(f"Error analyzing imports in {module_path}: {str(e)}")
    
    # Find cycles in the graph using DFS
    def find_cycles(node, path=None, visited=None):
        if path is None:
            path = []
        if visited is None:
            visited = set()
            
        cycles = []
        path.append(node)
        visited.add(node)
        
        for neighbor in graph.get(node, []):
            if neighbor in path:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
            elif neighbor not in visited and neighbor in graph:
                # Continue DFS
                cycles.extend(find_cycles(neighbor, path.copy(), visited.copy()))
                
        return cycles
    
    # Find all cycles
    all_cycles = {}
    for node in graph:
        cycles = find_cycles(node)
        if cycles:
            all_cycles[node] = cycles
            
    return all_cycles

# Example usage:
"""
# Fix imports in a single file
fixed = fix_imports_in_file('path/to/file.py')
print(f"Fixed: {fixed}")

# Fix imports in an entire project
fixed_issues = fix_imports_in_project('path/to/project')
print(f"Fixed {len(fixed_issues)} files with import issues")

# Generate a report of import issues
report = generate_import_report('path/to/project')
print(report)

# Find circular imports
circular_imports = find_circular_imports('path/to/project')
for module, cycles in circular_imports.items():
    print(f"Module {module} is involved in circular imports:")
    for cycle in cycles:
        print(f"  {' -> '.join(cycle)}")
""" 