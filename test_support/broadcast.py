import ast
import inspect
import textwrap

ALLOWED_IMPORT = ['numpy', 'math']

# ================= 1. Broadcasting Rule Checker =================
class BroadcastingChecker(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
        # Python builtins that hide element-wise iteration
        self.banned_builtins = {
            'map', 'filter', 'eval', 'exec', 'open', '__import__',
            'iter', 'next',   # manual iterator protocol
        }
        # NumPy helpers that still hide element-wise iteration
        self.banned_numpy_funcs = {
            'apply_along_axis', 'apply_over_axes', 'vectorize', 'frompyfunc',
            'nditer', 'ndindex', 'ndenumerate', 'Arrayterator', 'fromiter',
            'fromfunction',   # calls a user function for every index tuple
        }
        self.banned_attributes = {'flat', 'flatiter'}
        # Stack of enclosing function names for recursion detection
        self._func_name_stack: list[str] = []

    def report(self, node, message):
        line = getattr(node, 'lineno', '?')
        col  = getattr(node, 'col_offset', None)
        loc  = f"Line {line}" 
        self.violations.append(f"{loc}: {message}")

    def visit_For(self, node): self.report(node, "For loop is not allowed."); self.generic_visit(node)
    def visit_AsyncFor(self, node): self.report(node, "Async For loop is not allowed."); self.generic_visit(node)
    def visit_While(self, node): self.report(node, "While loop is not allowed."); self.generic_visit(node)
    def visit_ListComp(self, node): self.report(node, "List comprehension is not allowed."); self.generic_visit(node)
    def visit_SetComp(self, node): self.report(node, "Set comprehension is not allowed."); self.generic_visit(node)
    def visit_DictComp(self, node): self.report(node, "Dict comprehension is not allowed."); self.generic_visit(node)
    def visit_GeneratorExp(self, node): self.report(node, "Generator expression is not allowed."); self.generic_visit(node)

    # ----- function-scope tracking (for recursion detection) -----
    def visit_FunctionDef(self, node):
        self._func_name_stack.append(node.name)
        self.generic_visit(node)
        self._func_name_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in self.banned_builtins:
                self.report(node, f"Built-in function '{name}()' is banned.")
            elif name in self.banned_numpy_funcs:
                self.report(node, f"Function '{name}()' is banned.")
            # Direct self-recursion effectively implements a loop
            elif name in self._func_name_stack:
                self.report(node, f"Recursive call '{name}()' is not allowed (hides a loop).")

        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in self.banned_numpy_funcs:
                self.report(node, f"NumPy pseudo broadcasting helper/iterator '{attr}()' is banned.")

        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr in self.banned_attributes:
            self.report(node, f"Attribute '.{node.attr}' is banned.")
        self.generic_visit(node)


# ================= 2. Import Dependency Collector =================
class ImportCollector(ast.NodeVisitor):
    """Collect all import statements in source code, including those inside functions."""
    def __init__(self):
        self.imports = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.imports.add(node.module or '')
        self.generic_visit(node)


# ================= 3. Core Utility Functions =================

def get_source_code(target):
    """Normalize a function object, module object, or string into dedented source code."""
    if isinstance(target, str):
        source = target
    else:
        try:
            source = inspect.getsource(target)
        except OSError:
            raise ValueError("Cannot retrieve source code. Ensure the function is defined in a file, not purely dynamically.")
    
    return textwrap.dedent(source)

def analyze_function(func) -> list[str]:
    """Check whether a function object satisfies the broadcasting coding requirements."""
    source = get_source_code(func)
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"Syntax Error: {e}"]

    checker = BroadcastingChecker()
    checker.visit(tree)
    return checker.violations

def check_module_imports(module, allowed_modules=ALLOWED_IMPORT) -> list[str]:
    source = get_source_code(module)

    tree = ast.parse(source)
    collector = ImportCollector()
    collector.visit(tree)

    allowed_modules = set(allowed_modules)
    
    violations = []

    for mod in collector.imports:
        if mod not in allowed_modules and mod[:4] != 'core':
            violations.append(f"Module '{mod}' is not allowed to be imported in module '{module.__name__}'.")
    
    return violations

if __name__ == "__main__":

    print("\n=== Check broadcasting NumPy style ===")
    def example_function(x):
        import numpy as np
        eval('print(1)')
        example_function(x + 1)
        np.apply_along_axis(np.sum, 0, x)
        for i in range(10): print(i)
        while 1: print(1)
        li = [i for i in range(5)]
    
    print(analyze_function(example_function))
