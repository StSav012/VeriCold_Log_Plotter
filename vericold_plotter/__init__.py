import logging
import os
import sys
from collections.abc import Iterable
from typing import TextIO

import numpy as np
from numpy.typing import NDArray

from .log_parser import parse

__all__ = ["cli", "gui"]

logger: logging.Logger = logging.getLogger("VeriCold")


def _load_file(filenames: Iterable[str]) -> tuple[NDArray[np.float64], list[str]]:
    titles: list[str]
    data: NDArray[np.float64]

    all_titles: list[list[str]] = []
    all_data: list[NDArray[np.float64]] = []
    for filename in filenames:
        try:
            titles, data = parse(filename)
        except (OSError, RuntimeError) as ex:
            logger.warning(" ".join(repr(a) for a in ex.args))
            continue
        else:
            all_titles.append(titles)
            all_data.append(data)
            logger.info(f"loaded {filename}")
    if not all_titles or not all_data:
        logger.error("No data loaded")
        return np.empty(0), []

    # use only the files with identical columns
    titles = all_titles[-1]
    i: int = len(all_titles) - 2
    while i >= 0 and all_titles[i] == titles:
        i -= 1
    data = np.column_stack(all_data[i + 1 :])

    return data, titles


def _save_csv(
    filename: str,
    data: NDArray[np.float64],
    header: Iterable[str],
    *,
    csv_separator: str = "\t",
    line_end: str = os.linesep,
) -> None:
    if data.ndim != 2:
        logger.error(f"Invalid data shape: {data.shape}")
        return

    f_out: TextIO
    with open(filename, "w", newline=line_end) as f_out:
        f_out.write(csv_separator.join(header) + "\n")
        f_out.writelines(
            ((csv_separator.join(f"{xii}" for xii in xi) if isinstance(xi, Iterable) else f"{xi}") + "\n")
            for xi in data.T
        )


def _save_xlsx(filename: str, data: NDArray[np.float64], header: Iterable[str], *, sheet_name: str) -> None:
    from contextlib import suppress
    from datetime import datetime
    from typing import cast

    from pyexcelerate import Font, Format, Panes, Style, Workbook, Worksheet

    if data.ndim != 2:
        logger.error(f"Invalid data shape: {data.shape}")
        return

    header = list(header)

    workbook: Workbook = Workbook()
    worksheet: Worksheet.Worksheet = workbook.new_sheet(sheet_name)
    worksheet.panes = Panes(y=1)  # freeze first row

    header_style: Style = Style(font=Font(bold=True))
    datetime_style: Style = Style(format=Format("yyyy-mm-dd hh:mm:ss"), size=-1)
    auto_size_style: Style = Style(size=-1)

    col: int
    row: int
    for col in range(data.shape[0]):
        worksheet.set_cell_value(1, col + 1, header[col])
        if header[col].endswith(("(s)", "(secs)")):
            for row in range(data.shape[1]):
                # `NaN`, overflow, or `localtime()` or `gmtime()` failure
                with suppress(ValueError, OverflowError, OSError):
                    worksheet.set_cell_value(row + 2, col + 1, datetime.fromtimestamp(cast(float, data[col, row])))
                worksheet.set_cell_style(row + 2, col + 1, datetime_style)
        else:
            for row in range(data.shape[1]):
                worksheet.set_cell_value(row + 2, col + 1, data[col, row])
                worksheet.set_cell_style(row + 2, col + 1, auto_size_style)
    worksheet.set_row_style(1, header_style)
    workbook.save(filename)


def cli() -> int:
    import argparse
    from pathlib import Path

    try:
        import pyexcelerate
    except ImportError:
        pyexcelerate = None

    package: str | None = sys.modules["__main__"].__package__
    prog: str = Path(sys.argv[0]).name if package is None else " ".join([sys.executable, "-m", package])
    ap: argparse.ArgumentParser = argparse.ArgumentParser(
        prog=prog,
        description="Convert VeriCold log files to CSV" + (" or XLSX" if pyexcelerate is not None else ""),
    )
    try:
        from ._version import version
    except ImportError:
        version = ""
    if version:
        ap.add_argument("-V", "--version", action="version", version=f"{prog} {version}")
    ap.add_argument("log_file", nargs=argparse.ONE_OR_MORE, help="VeriCold log file to convert")
    if pyexcelerate is not None:
        ap.add_argument(
            "-f",
            "--format",
            "--output-format",
            choices=("csv", "xlsx"),
            default="csv",
            help="output format",
            type=str.casefold,
        )
    ap.add_argument("-o", "--out", metavar="out_file", help="filename to save to", required=True)
    args: argparse.Namespace = ap.parse_intermixed_args()
    try:
        if pyexcelerate is None or args.format == "csv":
            _save_csv(args.out, *_load_file(args.log_file))
        elif pyexcelerate is not None and args.format == "xlsx":
            sheet_name: str = ", ".join(Path(lf).stem for lf in args.log_file)
            if len(sheet_name) > 31:
                # Excel does not permit worksheet names longer than 31 characters
                sheet_name = sheet_name[:30] + "…"
            _save_xlsx(
                args.out,
                *_load_file(args.log_file),
                sheet_name=sheet_name,
            )
        else:
            raise ValueError(f"Unsupported output format: {args.format}")
    except Exception as ex:
        logger.error(ex)
        return 1
    else:
        return 0


def gui() -> int:
    try:
        from .gui import run
    except ImportError:
        import traceback

        traceback.print_exc()
        return 1
    else:
        return run()
