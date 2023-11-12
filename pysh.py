import importlib
import shlex
import sys

from typing import Iterable, Optional


def run(
    script: Iterable[str],
    globals_: Optional[dict] = None,
    fn_map: Optional[dict[str]] = None,
):
    imported = False
    func = None
    func_lines = None

    def init_globals():
        nonlocal imported
        nonlocal globals_

        if not imported:
            if globals_ is None:
                globals_ = dict(globals())
            imported = True

    def handle(line: str):
        nonlocal func
        nonlocal func_lines

        if a := shlex.split(line, comments=True):
            fn = a[0].replace('-', '_')

            if fn == 'import':
                if len(a) < 2:
                    raise ValueError(line)

                init_globals()
                for m in a[1:]:
                    globals_[m] = importlib.import_module(m)
                return
            elif fn == 'function':
                if func:
                    raise ValueError(line)
                func = fn[1]
                func_lines = []
                return
            elif fn == 'done':
                if not func:
                    raise ValueError(line)

                body = list(func_lines)

                def runner():
                    for line in body:
                        handle(line)

                init_globals()
                globals_[func] = runner

                func = None
                return

            if func:
                func_lines.append(line)
                return

            parse_fn = True
            if fn_map:
                try:
                    fn = fn_map[fn]
                except KeyError:
                    pass
                else:
                    parse_fn = isinstance(fn, str)

            if parse_fn:
                fn = eval(fn, globals_)

            fn(*a[1:])

    for line in script:
        handle(line)


def main(*args, **kwargs):
    file = sys.argv[1]
    with open(file, encoding='utf-8') as fp:
        run(fp, *args, **kwargs)


if __name__ == '__main__':
    main()
