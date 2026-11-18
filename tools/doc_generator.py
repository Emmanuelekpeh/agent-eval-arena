import os
import inspect
import markdown
from typing import List, Dict
import sys
sys.path.append('..')

class DocGenerator:
    def __init__(self, output_dir='docs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_module_docs(self, module, filename: str):
        doc_content = f"# {module.__name__} Documentation\n\n"
        
        # Get all classes in the module
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and obj.__module__ == module.__name__:
                doc_content += self._document_class(obj)
        
        # Save documentation
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w') as f:
            f.write(doc_content)
    
    def _document_class(self, cls) -> str:
        doc = f"## {cls.__name__}\n\n"
        
        # Add class docstring
        if cls.__doc__:
            doc += f"{cls.__doc__}\n\n"
        
        # Document methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_'):  # Skip private methods
                doc += self._document_method(method)
        
        return doc
    
    def _document_method(self, method) -> str:
        doc = f"### {method.__name__}\n\n"
        
        if method.__doc__:
            doc += f"{method.__doc__}\n\n"
        
        # Get signature
        sig = inspect.signature(method)
        doc += f"**Signature:** `{method.__name__}{sig}`\n\n"
        
        return doc
