# -*- coding: utf-8 -*-
from typing import List, Optional, Union

import numpy as np
from numpy.typing import NDArray


class DataModel:
    def __init__(self) -> None:
        self._data: NDArray[np.float64] = np.empty((0, 0), dtype=np.float64)
        self._header: List[str] = []

    @property
    def header(self) -> List[str]:
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

    def __getitem__(self, column_index: Union[int, slice, NDArray[np.int]]) -> NDArray[np.float64]:
        return self._data[column_index]

    def item(self, row_index: int, column_index: int) -> float:
        return float(self._data[column_index, row_index])

    def set_data(self, new_data: Union[List[List[float]], NDArray[np.float64]],
                 new_header: Optional[List[str]] = None) -> None:
        self._data = np.array(new_data)
        good: NDArray[np.bool] = ~np.all(self._data == 0.0, axis=1)
        if new_header is not None and 'LineNumber' in new_header:
            good[new_header.index('LineNumber')] = False
        self._data = self._data[good]
        if new_header is not None:
            self._header = [str(s) for s, g in zip(new_header, good) if g]
