import os
import sys
import subprocess
from pathlib import Path
import json


def run_quiz2audio(tmp_path: Path):
    quiz_file = tmp_path / "quiz.txt"
    quiz_file.write_text("cat := 猫\nhello := こんにちは\n")
    out_dir = tmp_path / "out"
    cmd = [
        "uv",
        "run",
        "quiz2audio",
        str(quiz_file),
        str(out_dir),
        "--engine",
        "dummy",
        "--lang-QA",
        "EJ",
        "--section-unit",
        "1",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=Path(__file__).parents[1], env=env)
    return quiz_file, out_dir, proc


def run_quiz2audio_single(tmp_path: Path):
    quiz_file = tmp_path / "quiz_single.txt"
    quiz_file.write_text("apple := りんご\nbanana := バナナ\n")
    out_dir = tmp_path / "out_single"
    cmd = [
        "uv",
        "run",
        "quiz2audio",
        str(quiz_file),
        str(out_dir),
        "--engine",
        "dummy",
        "--lang-QA",
        "EJ",
        "--single-file",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=Path(__file__).parents[1], env=env)
    return quiz_file, out_dir, proc


def test_quiz2audio_generates_sections(tmp_path):
    quiz_file, out_dir, proc = run_quiz2audio(tmp_path)

    raw_dir = quiz_file.parent / f".raw_{out_dir.name}"
    assert raw_dir.exists()
    raw_files = list(raw_dir.glob("*.mp3"))
    assert len(raw_files) >= 2

    section_files = list(out_dir.glob("*.mp3"))
    assert len(section_files) >= 1
    for f in section_files:
        assert f.stat().st_size > 0


def test_quiz_parser_importable():
    sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
    from quiz_to_audio.quiz_parser import load_quiz

    sample = "Q1 := A1\n#comment\n\n(Q2)\nQ2 := A2\n"
    path = Path("tmp_quiz.txt")
    path.write_text(sample)
    try:
        result = load_quiz(str(path))
        assert result == [("Q1", "A1"), ("Q2", "A2")]
    finally:
        path.unlink(missing_ok=True)


def test_single_file_mode(tmp_path):
    quiz_file, out_dir, proc = run_quiz2audio_single(tmp_path)

    # Should not create sectioned files; only single combined file with stem name
    combined = out_dir / f"{quiz_file.stem}.mp3"
    assert combined.exists()
    assert combined.stat().st_size > 0

    # Raw directory still produced
    raw_dir = quiz_file.parent / f".raw_{out_dir.name}"
    assert raw_dir.exists()


def test_single_file_conflicts_with_section_unit(tmp_path):
    quiz_file = tmp_path / "quiz_conflict.txt"
    quiz_file.write_text("one := 1\n")
    out_dir = tmp_path / "out_conflict"
    cmd = [
        "uv",
        "run",
        "quiz2audio",
        str(quiz_file),
        str(out_dir),
        "--single-file",
        "--section-unit",
        "5",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parents[1], env=env)
    assert proc.returncode != 0
    assert "--single-file cannot be used together with --section-unit" in proc.stderr


def test_album_override_single_file(tmp_path):
    quiz_file = tmp_path / "quiz_album.txt"
    quiz_file.write_text("sun := 太陽\n")
    out_dir = tmp_path / "out_album"
    cmd = [
        "uv",
        "run",
        "quiz2audio",
        str(quiz_file),
        str(out_dir),
        "--engine",
        "dummy",
        "--single-file",
        "--album",
        "Custom Album",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=Path(__file__).parents[1], env=env)
    combined = out_dir / f"{quiz_file.stem}.mp3"
    assert combined.exists()
    assert combined.stat().st_size > 0
