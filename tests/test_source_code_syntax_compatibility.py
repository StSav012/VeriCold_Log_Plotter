from ast import parse
from collections.abc import Callable, Iterator
from functools import partial
from operator import eq, ge, gt, le, lt, ne
from pathlib import Path
from sys import version_info

# noinspection PyCompatibility
from tomllib import loads


def version(s: str) -> tuple[int | str, ...]:
    v: tuple[int | str, ...] = ()
    for p in s.split("."):
        try:
            v = *v, int(p)
        except ValueError:
            v = *v, p
    return v


def matching_versions(limits: str) -> Iterator[tuple[int, int]]:
    parts: list[str] = limits.split(",")
    conditions: set[Callable[[tuple[int, int]], bool]] = set()
    op_map: dict[str, Callable[[object, object], bool]] = {
        # NB: the signs are reversed for `partial`
        ">": lt,
        ">=": le,
        "==": eq,
        "<=": ge,
        "<": gt,
        "!=": ne,
    }
    ops: list[str] = sorted(op_map.keys(), key=len, reverse=True)
    for part in parts:
        part = part.strip()
        for op in ops:
            if part.startswith(op):
                conditions.add(partial(op_map[op], version(part.removeprefix(op).lstrip())))
                break
    for major in range(version_info[0] + 1):
        for minor in range(version_info[1] + 1):
            if all(condition((major, minor)) for condition in conditions):
                yield major, minor


def list_files(path: Path, suffix: str = "") -> list[Path]:
    filenames: list[Path] = []
    if path.is_dir():
        for file in path.iterdir():
            filenames.extend(list_files(file, suffix=suffix))
    elif path.is_file() and (not suffix or path.suffix == suffix):
        filenames.append(path)
    return filenames


def test_source_code_syntax_compatibility() -> None:
    root: Path = Path.cwd().parent
    project = loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    name: str = project["name"]
    python_limits: str = project["requires-python"]
    files: dict[Path, str] = {f: f.read_text(encoding="utf-8") for f in list_files(root / name, ".py")}
    for feature_version in matching_versions(python_limits):
        for filename, source in files.items():
            parse(source=source, filename=filename, feature_version=feature_version)


if __name__ == "__main__":
    test_source_code_syntax_compatibility()
