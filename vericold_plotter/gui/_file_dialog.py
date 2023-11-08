# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import mimetypes
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Callable, Collection, Iterable, NamedTuple, TextIO, cast, final

import numpy as np
from numpy.typing import NDArray
from pyqtgraph.Qt import QtWidgets

from ._settings import Settings

__all__ = ["FileDialog"]


class MimeType(NamedTuple):
    mimetypes: Collection[str]
    saver: Callable[[str, NDArray[np.float64], Iterable[str]], None]


@final
class FileDialog(QtWidgets.QFileDialog):
    def __init__(self, settings: Settings, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent=parent)

        self.settings: Settings = settings

    def _join_file_dialog_formats(self, formats: dict[tuple[str, ...], str]) -> list[str]:
        def ensure_prefix(s: str, prefix: str) -> str:
            if s.startswith(prefix):
                return s
            return prefix + s

        f: tuple[str, ...]
        all_supported_extensions: list[str] = []
        for f in formats.keys():
            all_supported_extensions.extend(ensure_prefix(_f, "*") for _f in f)
        format_lines: list[str] = [
            "".join(
                (
                    self.tr("All supported", "file type"),
                    "(",
                    " ".join(ensure_prefix(_f, "*") for _f in all_supported_extensions),
                    ")",
                )
            )
        ]
        n: str
        for f, n in formats.items():
            format_lines.append("".join((n, "(", " ".join(ensure_prefix(_f, "*") for _f in f), ")")))
        format_lines.append(self.tr("All files", "file type") + "(* *.*)")
        return format_lines

    def _save_csv(self, filename: str, data: NDArray[np.float64], header: Iterable[str]) -> None:
        if data.ndim != 2:
            raise ValueError(f"Invalid data shape: {data.shape}")

        f_out: TextIO
        with open(filename, "wt", newline=self.settings.line_end) as f_out:
            f_out.write(self.settings.csv_separator.join(header) + "\n")
            f_out.writelines(
                (
                    (self.settings.csv_separator.join(f"{xii}" for xii in xi) if isinstance(xi, Iterable) else f"{xi}")
                    + "\n"
                )
                for xi in data.T
            )

    def _save_xlsx(self, filename: str, data: NDArray[np.float64], header: Iterable[str]) -> None:
        from pyexcelerate import Font, Format, Panes, Style, Workbook, Worksheet

        if data.ndim != 2:
            raise ValueError(f"Invalid data shape: {data.shape}")

        header = list(header)

        workbook: Workbook = Workbook()
        worksheet: Worksheet = workbook.new_sheet(Path(self.settings.opened_file_name).stem)
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

    def get_open_filenames(self) -> list[str]:
        opened_filename: str = self.settings.opened_file_name

        supported_formats: dict[tuple[str, ...], str] = {
            ("*.vcl",): self.tr("VeriCold data logfile"),
        }

        self.restoreGeometry(self.settings.open_dialog_geometry)
        self.restoreState(self.settings.open_dialog_state)
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        self.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFiles)
        self.setNameFilters(self._join_file_dialog_formats(supported_formats))
        self.setOption(QtWidgets.QFileDialog.Option.HideNameFilterDetails, True)
        self.setWindowTitle(self.tr("Open"))
        self.selectFile(opened_filename)

        if self.exec() and self.selectedFiles():
            self.settings.open_dialog_state = self.saveState()
            self.settings.open_dialog_geometry = self.saveGeometry()
            return self.selectedFiles()
        return []

    def export(self, data: NDArray[np.float64], header: Iterable[str]) -> None:
        mimetypes.init()

        exported_filename: str = self.settings.exported_file_name
        opened_filename: str = self.settings.opened_file_name

        supported_formats: list[MimeType] = [
            MimeType((mimetypes.types_map[".csv"],), self._save_csv),
        ]
        if importlib.util.find_spec("pyexcelerate") is not None:
            supported_formats.append(MimeType((mimetypes.types_map[".xlsx"],), self._save_xlsx))
        selected_format: MimeType | None = None
        if exported_filename:
            exported_file_mimetype: str | None = mimetypes.guess_type(exported_filename, strict=False)[0]
            if exported_file_mimetype is not None:
                for supported_format in supported_formats:
                    if exported_file_mimetype in supported_format.mimetypes:
                        selected_format = supported_format
                        break
        elif supported_formats:
            selected_format = supported_formats[0]

        supported_mimetypes: list[str] = []
        for supported_format in supported_formats:
            supported_mimetypes.extend(supported_format.mimetypes)

        self.restoreGeometry(self.settings.export_dialog_geometry)
        self.restoreState(self.settings.export_dialog_state)
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        self.setMimeTypeFilters(supported_mimetypes)
        self.setOption(QtWidgets.QFileDialog.Option.HideNameFilterDetails, True)
        self.setWindowTitle(self.tr("Export"))
        if selected_format is not None:
            try:
                selected_mimetype: str = list(selected_format.mimetypes)[0]
            except LookupError:
                pass
            else:
                self.selectMimeTypeFilter(selected_mimetype)
                self.selectFile(
                    str(
                        Path(exported_filename or opened_filename)
                        .with_name(Path(opened_filename).name)
                        .with_suffix(mimetypes.guess_extension(selected_mimetype, strict=False))
                    )
                )

        if self.exec() and self.selectedFiles():
            self.settings.export_dialog_state = self.saveState()
            self.settings.export_dialog_geometry = self.saveGeometry()
            new_file_name: str = self.selectedFiles()[0]
            new_file_mimetype: str | None = mimetypes.guess_type(new_file_name, strict=False)[0]
            if new_file_mimetype is None or new_file_mimetype not in supported_mimetypes:
                if supported_mimetypes:
                    new_file_mimetype = supported_mimetypes[0]

            # ensure the filename extension is correct
            new_file_mimetype_extensions: list[str]
            if new_file_mimetype is None:
                if supported_mimetypes:
                    new_file_mimetype = supported_mimetypes[0]
            else:
                new_file_mimetype_extensions = mimetypes.guess_all_extensions(new_file_mimetype, strict=False)
                if new_file_mimetype_extensions:
                    new_file_name_ext: str = Path(new_file_name).suffix
                    if new_file_name_ext not in new_file_mimetype_extensions:
                        new_file_name += new_file_mimetype_extensions[0]

            if new_file_mimetype is None:
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr("Error"),
                    self.tr("Unknown file type:\n{0}").format(new_file_name),
                )
                return

            for supported_format in supported_formats:
                if new_file_mimetype in supported_format.mimetypes:
                    supported_format.saver(new_file_name, data, header)
                    self.settings.exported_file_name = new_file_name
                    break

            # we should never reach to here
            if new_file_mimetype is None:
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr("Error"),
                    self.tr("Unsupported file type:\n{0}").format(new_file_name),
                )
