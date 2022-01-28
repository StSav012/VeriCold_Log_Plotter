# -*- coding: utf-8 -*-
import sys

if __name__ == '__main__':
    try:
        import gui
    except ImportError as ex:
        tb = sys.exc_info()[2]
        print(ex.with_traceback(tb), file=sys.stderr)
    except SyntaxError:
        print('Get a newer Python!', file=sys.stderr)
    else:
        gui.run()
