from os import PathLike
from typing import BinaryIO, Final

__all__ = ["parse"]


try:
    import numpy as np
    from numpy.typing import NDArray

    def parse(filename: str | PathLike[str] | BinaryIO) -> tuple[list[str], NDArray[np.float64]]:
        def _parse(file_handle: BinaryIO) -> tuple[list[str], NDArray[np.float64]]:
            file_handle.seek(0x1800)
            titles: list[str] = []
            while file_handle.tell() < 0x2000:
                title: str = file_handle.read(32).rstrip(b"\0").decode("ascii")
                if title:
                    titles.append(title)
                else:
                    break
            file_handle.seek(0x3000)
            dt: np.dtype[np.generic] = np.dtype(np.float64).newbyteorder("<")
            data: NDArray[dt] = np.frombuffer(file_handle.read(), dtype=dt)
            i: int = 0
            data_item_size: int | None = None
            while i < data.size:
                if data_item_size is None:
                    data_item_size = int(round(data[i] / dt.itemsize))
                elif int(round(data[i] / dt.itemsize)) != data_item_size:
                    raise RuntimeError("Inconsistent data: some records are faulty")
                i += int(round(data[i] / dt.itemsize))
            if data_item_size is None:
                return [], np.empty(0)
            return titles, data.reshape((data_item_size, -1), order="F")[: len(titles)].astype(np.float64)

        if isinstance(filename, BinaryIO):
            return _parse(filename)
        f_in: BinaryIO
        with open(filename, "rb") as f_in:
            return _parse(f_in)

except ImportError:
    import struct

    def parse(filename: str | PathLike[str] | BinaryIO) -> tuple[list[str], list[list[float]]]:
        def _parse(file_handle: BinaryIO) -> tuple[list[str], list[list[float]]]:
            file_handle.seek(0x1800)
            titles: list[str] = []
            while file_handle.tell() < 0x2000:
                title: str = file_handle.read(32).rstrip(b"\0").decode("ascii")
                if title:
                    titles.append(title)
                else:
                    break
            file_handle.seek(0x3000)
            data: list[list[float]] = [[] for _ in range(len(titles))]
            while True:
                data_size_data: bytes = file_handle.read(double_size)
                if not data_size_data:
                    break
                data_size: int = int(struct.unpack_from("<d", data_size_data)[0])
                data[0].append(data_size)
                line_data: bytes = file_handle.read(data_size - double_size)
                if len(line_data) != data_size - double_size:
                    raise OSError("Corrupted or incomplete data found")
                count: int = len(line_data) // double_size + 1
                if count != len(titles):
                    raise RuntimeError(f"Do not know how to process {count} channels")
                for index, item in enumerate(struct.unpack_from(f"<{len(titles) - 1}d", line_data), start=1):
                    data[index].append(item)
            return titles, data

        double_size: Final[int] = struct.calcsize("<d")

        if isinstance(filename, BinaryIO):
            return _parse(filename)
        f_in: BinaryIO
        with open(filename, "rb") as f_in:
            return _parse(f_in)
