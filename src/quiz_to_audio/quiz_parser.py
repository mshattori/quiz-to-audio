import re
from typing import List, Tuple

PAREN_PATTERN = r"\([^()]*?(?:\([^()]+\)[^()]*)*\)"


def _is_skip_line(line: str) -> bool:
    stripped = line.strip()
    return (
        len(stripped) == 0
        or stripped.startswith("#")
        or ":=" not in line
        or re.fullmatch(r"\s*\(.*\)\s*", line)
    )


def _split_quiz(quiz: str) -> Tuple[str, str]:
    q_text, a_text = quiz.split(" := ")
    q_text = re.sub(PAREN_PATTERN, "", q_text)
    a_text = re.sub(PAREN_PATTERN, "", a_text)
    if re.search(r"[()]", q_text) or re.search(r"[()]", a_text):
        raise ValueError(f'Unmatched paren: "{quiz}"')

    q_text, a_text = q_text.strip(), a_text.strip()
    if len(q_text) == 0 or len(a_text) == 0:
        raise ValueError(f'Q or A is empty: "{quiz}"')
    q_text = re.sub(r"\s*/\s*", ", or ", q_text)
    a_text = re.sub(r"\s*/\s*", ", or ", a_text)
    return q_text, a_text


def load_quiz(quiz_file: str) -> List[Tuple[str, str]]:
    with open(quiz_file, encoding="utf-8") as f:
        lines = f.readlines()
    quiz_lines = [l.strip() for l in lines if not _is_skip_line(l)]
    return [_split_quiz(quiz) for quiz in quiz_lines]


__all__ = ["load_quiz"]
