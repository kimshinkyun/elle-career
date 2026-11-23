from dataclasses import dataclass, field, asdict


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list = field(default_factory=list)   # list[Word]

    def to_dict(self):
        return asdict(self)


def segments_from_dicts(items):
    out = []
    for s in items:
        words = [Word(float(w["start"]), float(w["end"]), str(w["text"]).strip()) for w in s.get("words", [])]
        out.append(Segment(float(s["start"]), float(s["end"]), str(s["text"]).strip(), words))
    return out
