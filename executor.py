import json
import subprocess
import tempfile
import os
import ast
import sys
import signal
import resource
from typing import Dict, Any, Tuple

class PythonValidator:
    
    def validate_script(self, script: str) -> Tuple[bool, str]:
        try:
            tree = ast.parse(script)
        except SyntaxError as e:
            return False, f"Invalid Python syntax: {str(e)}"
        
        has_main = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                has_main = True
                break
        
        if not has_main:
            return False, "Script must contain a main() function"
        
        allowed_modules = {'os', 'pandas', 'numpy', 'json', 'math', 'random', 'datetime', 'time', 'collections'}
        dangerous_modules = {
            'subprocess', '__import__', 'eval', 'exec', 'compile',
            'open', 'file', 'input', 'raw_input', 'reload', 'vars', 'globals',
            'locals', 'dir', 'getattr', 'setattr', 'delattr', 'hasattr',
            'socket', 'urllib', 'urllib2', 'httplib', 'requests', 'sys',
            'importlib', 'pkgutil', 'imp'
        }
        
        dangerous_functions = {'eval', 'exec', 'compile', '__import__'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if (alias.name in dangerous_modules or 
                        (alias.name not in allowed_modules and alias.name.startswith('_'))):
                        return False, f"Import '{alias.name}' is not allowed"
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module in dangerous_modules or 
                                  (node.module not in allowed_modules and node.module and node.module.startswith('_'))):
                    return False, f"Import from '{node.module}' is not allowed"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in dangerous_functions:
                    return False, f"Function '{node.func.id}' is not allowed"
                elif isinstance(node.func, ast.Attribute) and node.func.attr in {'system', 'popen', 'spawn'}:
                    return False, f"Method '{node.func.attr}' is not allowed"
        
        return True, "Valid"

class SecurePythonExecutor:
    
    def __init__(self):
        self.validator = PythonValidator()
        
    def execute_script(self, script: str) -> Dict[str, Any]:
        is_valid, message = self.validator.validate_script(script)
        if not is_valid:
            raise ValueError(message)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, "user_script.py")
            
            with open(script_path, 'w') as f:
                f.write(script)
            
            wrapper_script = f'''
import sys
import json
import io
import contextlib
import resource
import signal
import os

try:
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
    resource.setrlimit(resource.RLIMIT_NOFILE, (20, 20))
except (ValueError, OSError):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Script execution timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(25)

os.chdir("{temp_dir}")
stdout_capture = io.StringIO()

try:
    with contextlib.redirect_stdout(stdout_capture):
        sys.path.insert(0, "{temp_dir}")
        import user_script
        
        if hasattr(user_script, "main"):
            result = user_script.main()
        else:
            raise ValueError("No main() function found")
    
    stdout_content = stdout_capture.getvalue()
    signal.alarm(0)
    
    output = {{
        "success": True,
        "result": result,
        "stdout": stdout_content
    }}
    print(json.dumps(output))
    
except Exception as e:
    signal.alarm(0)
    output = {{
        "success": False,
        "error": str(e),
        "stdout": stdout_capture.getvalue()
    }}
    print(json.dumps(output))
'''
            
            wrapper_path = os.path.join(temp_dir, "wrapper.py")
            with open(wrapper_path, 'w') as f:
                f.write(wrapper_script)
            
            try:
                result = subprocess.run(
                    ["/usr/local/bin/python", wrapper_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=temp_dir,
                    env={
                        'PYTHONPATH': temp_dir,
                        'PYTHONIOENCODING': 'utf-8',
                        'PYTHONDONTWRITEBYTECODE': '1',
                    }
                )
                
                if result.returncode != 0:
                    return {
                        "success": False,
                        "error": f"Python execution failed: {result.stderr}",
                        "stdout": result.stdout
                    }
                
                try:
                    output = json.loads(result.stdout.strip())
                    return output
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "Failed to parse execution result",
                        "stdout": result.stdout
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": "Script execution timed out",
                    "stdout": ""
                }
    
