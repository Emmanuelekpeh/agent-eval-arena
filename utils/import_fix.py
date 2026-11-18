import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('battle_arena')

def fix_imports(file_path, dry_run=True):
    """
    Fix import statements in the given file.
    
    Args:
        file_path (str): Path to the file to fix
        dry_run (bool): If True, don't modify files, just report issues
        
    Returns:
        dict: Statistics about changes made
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return {'error': 'File not found'}
        
    with open(path, 'r') as f:
        content = f.read()
    
    # Track statistics
    stats = {
        'original_length': len(content),
        'changes': 0,
        'file': str(path)
    }
    
    # Common patterns to fix
    patterns = [
        # Relative imports that should be absolute
        (r'from \.\.([^\s]+) import', r'from systems\1 import'),
        (r'from \.([^\s]+) import', r'from systems.\1 import'),
        # Direct imports from parent directories that should use full paths
        (r'import ([^\.]+)\.([^\s]+)', r'import \1.\2'),
        # Fix circular imports by using lazy imports
        (r'from systems\.core import system_manager', 
         'def _get_system_manager():\n    from systems.core import system_manager\n    return system_manager\n\nsystem_manager = _get_system_manager()')
    ]
    
    modified_content = content
    for pattern, replacement in patterns:
        new_content, count = re.subn(pattern, replacement, modified_content)
        if count > 0:
            modified_content = new_content
            stats['changes'] += count
    
    if not dry_run and stats['changes'] > 0:
        with open(path, 'w') as f:
            f.write(modified_content)
        stats['new_length'] = len(modified_content)
        
    return stats

def fix_all_imports(root_dir='systems', extension='.py', dry_run=True):
    """
    Fix imports in all Python files in the given directory.
    
    Args:
        root_dir (str): Root directory to search for files
        extension (str): File extension to match
        dry_run (bool): If True, don't modify files, just report issues
        
    Returns:
        list: Statistics for all processed files
    """
    root = Path(root_dir)
    if not root.exists() or not root.is_dir():
        logger.error(f"Directory not found: {root_dir}")
        return [{'error': 'Directory not found'}]
        
    all_stats = []
    
    for path in root.rglob(f'*{extension}'):
        if not path.is_file():
            continue
            
        file_stats = fix_imports(str(path), dry_run)
        all_stats.append(file_stats)
        
        if file_stats.get('changes', 0) > 0:
            status = "would fix" if dry_run else "fixed"
            logger.info(f"{status} {file_stats['changes']} imports in {path}")
    
    return all_stats

def analyze_import_graph(root_dir='systems', extension='.py'):
    """
    Analyze the import graph to detect circular dependencies.
    
    Args:
        root_dir (str): Root directory to search for files
        extension (str): File extension to match
        
    Returns:
        dict: Information about the import graph including circular dependencies
    """
    root = Path(root_dir)
    if not root.exists() or not root.is_dir():
        logger.error(f"Directory not found: {root_dir}")
        return {'error': 'Directory not found'}
    
    # Map of module -> list of imported modules
    import_graph = {}
    
    # Extract imports from all files
    for path in root.rglob(f'*{extension}'):
        if not path.is_file():
            continue
            
        with open(path, 'r') as f:
            content = f.read()
        
        # Construct module name from file path
        rel_path = path.relative_to(root.parent)
        module_name = str(rel_path).replace('/', '.').replace('\\', '.').replace(extension, '')
        
        # Extract imports using regex
        imports = []
        
        # Match "import X" and "import X as Y"
        for match in re.finditer(r'import\s+([^\s,]+)(?:\s+as\s+[^\s,]+)?', content):
            imports.append(match.group(1))
        
        # Match "from X import Y" and get X
        for match in re.finditer(r'from\s+([^\s,.]+(?:\.[^\s,.]+)*)\s+import', content):
            imports.append(match.group(1))
        
        # Match relative imports and resolve them
        for match in re.finditer(r'from\s+(\.+)([^\s,.]*)\s+import', content):
            dots = match.group(1)
            module = match.group(2)
            
            # Resolve relative import
            parts = module_name.split('.')
            if dots:
                # Remove as many segments as there are dots
                parts = parts[:-len(dots)]
            
            if module:
                parts.append(module)
                
            resolved = '.'.join(parts)
            imports.append(resolved)
        
        import_graph[module_name] = imports
    
    # Find circular dependencies
    circular_deps = []
    
    def detect_cycles(module, path=None):
        if path is None:
            path = []
        
        if module in path:
            # Found a cycle
            cycle_start = path.index(module)
            circular_deps.append(path[cycle_start:] + [module])
            return
        
        if module not in import_graph:
            return
            
        for imported in import_graph[module]:
            detect_cycles(imported, path + [module])
    
    # Check for cycles starting from each module
    for module in import_graph:
        detect_cycles(module)
    
    # Remove duplicates
    unique_circular_deps = []
    for cycle in circular_deps:
        # Normalize the cycle by starting with the alphabetically first module
        min_index = cycle.index(min(cycle))
        normalized = cycle[min_index:] + cycle[:min_index]
        
        # Convert to tuple for hashability
        cycle_tuple = tuple(normalized)
        
        if cycle_tuple not in [tuple(c) for c in unique_circular_deps]:
            unique_circular_deps.append(normalized)
    
    return {
        'modules': len(import_graph),
        'import_graph': import_graph,
        'circular_dependencies': unique_circular_deps
    } 