# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

if __name__ == "__main__":
    try:
        import gui
    except ImportError:
        import traceback

        traceback.print_exc()
    except SyntaxError:
        print("Get a newer Python!", file=sys.stderr)
    else:
        gui.run()
