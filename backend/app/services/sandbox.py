"""Sandboxed code execution environment."""

import traceback

class SandboxError(Exception):
    """Exception raised for errors during sandboxed execution."""
    pass

def execute_sandboxed(code: str, variables: dict = None):
    """
    Execute python code in a restricted scope.
    """
    if variables is None:
        variables = {}
        
    local_env = variables.copy()
    
    # Basic restricted globals
    global_env = {
        "__builtins__": __builtins__,
        "math": __import__("math"),
        "datetime": __import__("datetime"),
    }
    
    try:
        exec(code, global_env, local_env)
        
        # Try to return a 'result' variable if the code set one, 
        # otherwise return the whole local context (minus private vars).
        if "result" in local_env:
            return local_env["result"]
            
        return {k: v for k, v in local_env.items() if not k.startswith('_')}
    except Exception as e:
        raise SandboxError(f"Execution failed: {str(e)}\n{traceback.format_exc()}")
