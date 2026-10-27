"""Load real application routes without local settings or database startup.

The production module initializes MySQL at import time. These tests execute
its actual imports, definitions and route registrations, stopping before the
top-level startup calls. No route/function body is rewritten or replaced.
Tests must explicitly supply fake persistence and synthetic request data.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]


def load_isolated_application(module_name: str = "_dermamatrix_consent_test_app") -> ModuleType:
    source = BACKEND_DIR / "app.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    startup = next(
        index for index, node in enumerate(tree.body)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name) and node.value.func.id == "load_local_env"
    )
    tree.body = tree.body[:startup]
    module = ModuleType(module_name)
    module.__file__ = str(source)
    sys.modules[module_name] = module
    with patch("pymysql.connect", side_effect=AssertionError("Tests must not open a real database")):
        exec(compile(tree, str(source), "exec"), module.__dict__)
    module.app.config.update(TESTING=True, SECRET_KEY="synthetic-test-secret", SESSION_COOKIE_SECURE=False)
    return module
