import os
import sys
import re
from pathlib import Path
import argparse
from dotenv import load_dotenv

from pydub import AudioSegment

from speech_audio_tools.audio import (
    make_section_mp3_files,
    _collect_ordinal_numbers,
    _find_question_file,
    _find_answer_file,
    _combine_QA,
    _combine_audio_list,
    _make_number_audio,
    NUMBER_AUDIO_DIR,
)
from .quiz_tts import QuizTTS


def _parse_speed_pair(speed: str):
    if ":" in speed:
        left, right = speed.split(":")
        return float(left), float(right)
    return float(speed), float(speed)


def _make_single_mp3(
    input_directory,
    output_directory,
    title,
    speed,
    gain,
    repeat_question,
    pause_duration,
    add_number_audio,
    artist="Homebrew",
):
    numbers = _collect_ordinal_numbers(input_directory)
    if not numbers:
        print("No QA audio found in " + input_directory)
        return 1

    segments = []
    if add_number_audio:
        os.makedirs(NUMBER_AUDIO_DIR, exist_ok=True)
        number_filename = _make_number_audio(int(numbers[0]))
        number_audio = AudioSegment.from_file(number_filename)
        pause = AudioSegment.silent(duration=500)
        segments.append(number_audio + pause)

    for number in numbers:
        file_Q = _find_question_file(input_directory, number)
        file_A = _find_answer_file(input_directory, number)
        if not (file_Q and file_A):
            print("WARN: Corresponding files not found for " + number)
            continue
        segments.append(_combine_QA(file_Q, file_A, speed, repeat_question, pause_duration))

    if not segments:
        print("No segments to combine; aborting single-file export")
        return 1

    audio = _combine_audio_list(segments)
    if gain != 0.0:
        audio = audio.apply_gain(gain)

    album = os.path.basename(output_directory).replace("_", " ").replace("-", " ").title()
    out_filename = os.path.join(output_directory, f"{title}.mp3")
    tags = {"title": title, "album": album, "artist": artist}
    audio.export(out_filename, format="mp3", tags=tags, id3v2_version="3")
    print('Created "' + out_filename + '"')
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", "-e", default=".env")
    parser.add_argument("--lang-QA", default="EE", choices=("EE", "EJ", "JE"))
    parser.add_argument("--speed-QA", default="1.0")
    parser.add_argument("--invert-QA", action="store_true", default=False)
    parser.add_argument("--gain", default="0.0")
    parser.add_argument("--engine", default=None)
    parser.add_argument("--repeat-question", action="store_true", default=False)
    parser.add_argument("--pause-duration", default="500")
    parser.add_argument("--add-number-audio", action="store_true", default=False)
    parser.add_argument("--split-by-comma", action="store_true", default=False)
    parser.add_argument(
        "--section-unit",
        type=int,
        default=None,
        help="Number of QAs per section MP3 (default: 10).",
    )
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="Combine all QAs into one MP3 (overrides section splitting).",
    )
    parser.add_argument("quiz_filename")
    parser.add_argument("output_directory")
    args = parser.parse_args(argv)

    load_dotenv(args.env_file, override=True)

    section_unit_explicit = args.section_unit is not None
    if args.single_file and section_unit_explicit:
        parser.error("--single-file cannot be used together with --section-unit")
    section_unit = args.section_unit if section_unit_explicit else 10

    quiz_file = args.quiz_filename
    output_directory = args.output_directory

    lang_Q, lang_A = "en-US", "en-US"
    if args.lang_QA == "EJ":
        lang_A = "ja-JP"
    if args.lang_QA == "JE":
        lang_Q = "ja-JP"

    try:
        speed_Q, speed_A = _parse_speed_pair(args.speed_QA)
    except Exception:
        print('Invalid speed format. The correct format is "0.9", "1.0:0.9", etc.')
        return 1

    engine_Q = engine_A = "neural"
    if args.engine:
        if ":" in args.engine:
            engine_Q, engine_A = args.engine.split(":")
        else:
            engine_Q = engine_A = args.engine

    if not os.path.isfile(quiz_file):
        print("File not found: " + quiz_file)
        return 1
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    if not os.path.isdir(output_directory):
        print("Not a directory: " + output_directory)
        return 1

    parent, dirname = os.path.split(os.path.normpath(output_directory))
    raw_directory = os.path.join(parent, ".raw_" + dirname)
    os.makedirs(raw_directory, exist_ok=True)
    print("Raw audio directory: " + raw_directory)

    tts = QuizTTS(lang_Q, lang_A, engine_Q, engine_A, speed_Q, speed_A)
    tts.quiz_list_to_audio(quiz_file, raw_directory, args.invert_QA, args.split_by_comma)

    gain = float(args.gain)
    pause_duration = int(args.pause_duration)
    if args.single_file:
        quiz_stem = Path(quiz_file).stem
        return _make_single_mp3(
            raw_directory,
            output_directory,
            title=quiz_stem,
            speed=(1.0, 1.0),
            gain=gain,
            repeat_question=args.repeat_question,
            pause_duration=pause_duration,
            add_number_audio=args.add_number_audio,
        )

    make_section_mp3_files(
        raw_directory,
        output_directory,
        speed=(1.0, 1.0),
        gain=gain,
        repeat_question=args.repeat_question,
        pause_duration=pause_duration,
        add_number_audio=args.add_number_audio,
        section_unit=section_unit,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
