import sys


def insert_text_after(s: str, what: str, where: str) -> str:
    index: int = 0
    quote_indices: list[int] = []
    quote_index: int = 0
    while (quote_index := s.find("'", quote_index)) != -1:
        quote_indices.append(quote_index)
        quote_index += 1
    while (index := s.find(where, index)) != -1:
        if any(a <= index <= b for a, b in zip(quote_indices[:-1:2], quote_indices[1::2], strict=True)):
            for a, b in zip(quote_indices[:-1:2], quote_indices[1::2], strict=True):
                if a <= index <= b:
                    index = b
                    break
            continue
        index += len(where)
        s = s[:index] + what + s[index:]
        index += len(what)
    return s


def remove_quotes(s: str) -> str:
    quote_indices: list[int] = []
    quote_index: int = 0
    while (quote_index := s.find("'", quote_index)) != -1:
        quote_indices.append(quote_index)
        quote_index += 1
    for b, a in zip(quote_indices[-1::-2], quote_indices[-2::-2], strict=True):
        s = s[:a] + s[b + 1 :]
    return s


def test_insert_text_after() -> None:
    assert insert_text_after("banana", "!!!", "a") == "ba!!!na!!!na!!!"
    assert insert_text_after("banana", "!", "na") == "bana!na!"
    assert insert_text_after("banana", "!!!", "na") == "bana!!!na!!!"
    assert insert_text_after("banana", "!!!", "spam") == "banana"
    assert insert_text_after("ba'na'na", "!!!", "na") == "ba'na'na!!!"


def test_remove_quotes() -> None:
    assert remove_quotes("ba'na'na") == "bana"
    assert remove_quotes("ba'na''na'na") == "bana"
    assert remove_quotes("ba''na") == "bana"
    assert remove_quotes("ba'''na'na") == "bana"


def test_adding_seconds_to_time_string() -> None:
    from pyqtgraph.Qt.QtCore import QCoreApplication, QLocale, QTime

    QCoreApplication(sys.argv)

    # NB: do NOT test for ‘m’ before ‘mm’
    fix_ups: dict[str, str] = {
        "h.mm": ".ss",
        "h:mm": ":ss",
        "H.mm": ".ss",
        "H:mm": ":ss",
        "h.m": ".s",
        "h:m": ":s",
        "H.m": ".s",
        "H:m": ":s",
        "H'h'mm": "'m'ss",
        "h'h'mm": "'m'ss",
        "H'h'm": "'m's",
        "h'h'm": "'m's",
        "ཆུ་ཚོད་ hh སྐར་མ་ mm": " སྐར་ཆ་ ss",
        "ཆུ་ཚོད་ HH སྐར་མ་ mm": " སྐར་ཆ་ ss",
        "ཆུ་ཚོད་ h སྐར་མ་ mm": " སྐར་ཆ་ ss",
        "ཆུ་ཚོད་ H སྐར་མ་ mm": " སྐར་ཆ་ ss",
        "ཆུ་ཚོད་ hh སྐར་མ་ m": " སྐར་ཆ་ s",
        "ཆུ་ཚོད་ HH སྐར་མ་ m": " སྐར་ཆ་ s",
        "ཆུ་ཚོད་ h སྐར་མ་ m": " སྐར་ཆ་ s",
        "ཆུ་ཚོད་ H སྐར་མ་ m": " སྐར་ཆ་ s",
    }

    for lang in QLocale.Language.__members__.values():
        locale: QLocale = QLocale(lang)
        for fmt in QLocale.FormatType.__members__.values():
            template: str = locale.timeFormat(fmt)
            template_without_literals: str = remove_quotes(template)
            if any(s in template_without_literals for s in fix_ups.values()):
                continue
            # NB: test for ‘m’ always after ‘mm’
            for hm, s in fix_ups.items():
                if hm in template:
                    template = insert_text_after(template, s, hm)
                    break
            else:
                raise AssertionError(template)
            time: QTime = QTime(3, 14, 15, 925)
            assert locale.toString(time.second()) in locale.toString(time, template), locale.toString(time, template)


if __name__ == "__main__":
    test_insert_text_after()
    test_remove_quotes()
    test_adding_seconds_to_time_string()
