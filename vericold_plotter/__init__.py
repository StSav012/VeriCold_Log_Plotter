# -*- coding: utf-8 -*-
from __future__ import annotations

import sys


def gui() -> int:
    try:
        from .gui import run
    except ImportError:
        import traceback

        traceback.print_exc()
        return 1
    except SyntaxError:
        print("Get a newer Python!", file=sys.stderr)
        return 1
    else:
        return run()
