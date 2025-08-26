from collections.abc import Iterable, Sequence

import numpy as np
from numpy.typing import NDArray

__all__ = ["DataModel"]


class DataModel:
    def __init__(self) -> None:
        self._data: NDArray[np.float64] = np.empty((0, 0), dtype=np.float64)
        self._header: list[str] = []

    @property
    def header(self) -> list[str]:
        return self._header

    @property
    def row_count(self) -> int:
        return self._data.shape[1]

    @property
    def column_count(self) -> int:
        return self._data.shape[0]

    @property
    def data(self) -> NDArray[np.float64]:
        return self._data

    def __getitem__(self, column_index: int | slice | NDArray[np.int_]) -> NDArray[np.float64]:
        return self._data[column_index]

    def item(self, row_index: int, column_index: int) -> float:
        return float(self._data[column_index, row_index])

    def set_data(
        self,
        new_data: Iterable[Iterable[float]] | NDArray[np.float64],
        new_header: Sequence[str] | None = None,
    ) -> None:
        self._data = np.asarray(new_data, dtype=np.float64)
        good: NDArray[np.bool_] = np.full(self._data.shape[0], True, dtype=np.bool_)
        if new_header is not None and "LineSize(bytes)" in new_header:
            good[new_header.index("LineSize(bytes)")] = False
        if new_header is not None and "LineNumber" in new_header:
            good[new_header.index("LineNumber")] = False
        self._data = self._data[good]
        if new_header is not None:
            self._header = [str(s) for s, g in zip(new_header, good) if g]
            i: int
            c: str
            for i, c in enumerate(self._header):
                if c.endswith("(K)"):  # temperature values must be positive
                    self._data[i, self._data[i] <= 0.0] = np.nan
                if c.endswith(("(secs)", "(s)")):  # time values must be positive
                    self._data[i, self._data[i] == 0.0] = np.nan
