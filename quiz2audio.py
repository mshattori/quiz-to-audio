#!/usr/bin/env python
import os
import sys
import re
from tts import QuizTTS
from audio import make_section_mp3_files

def main():
    import argparse
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', '-e', default='.env')
    parser.add_argument('--lang-QA', default='EE', choices=('EE', 'EJ', 'JE'))
    parser.add_argument('--speed-QA', default='1.0')
    parser.add_argument('--invert-QA', action='store_true', default=False)
    parser.add_argument('--gain', default='0.0')
    parser.add_argument('--engine', default=None)
    parser.add_argument('--repeat-question', action='store_true', default=False)
    parser.add_argument('--pause-duration', default='500')
    parser.add_argument('--add-number-audio', action='store_true', default=False)
    parser.add_argument('--split-by-comma', action='store_true', default=False)
    parser.add_argument('quiz_filename')
    parser.add_argument('output_directory')
    args = parser.parse_args()

    load_dotenv(args.env_file, override=True)

    quiz_file = args.quiz_filename 
    output_directory = args.output_directory 
    # Convert language code
    lang_Q, lang_A = 'en-US', 'en-US'
    if args.lang_QA == 'EJ':
        lang_A = 'ja-JP'
    if args.lang_QA == 'JE':
        lang_Q = 'ja-JP'
    # Convert speed
    speed = args.speed_QA
    if not re.fullmatch(r'\d+(\.\d+)?(:\d+(\.\d+)?)?', speed):
        print('Invalid speed format. The correct format is "0.9", "1.0:0.9", etc.')
        sys.exit(1)
    if speed.find(':') > 0:
        speed_Q, speed_A = speed.split(':')
        speed_Q, speed_A = float(speed_Q), float(speed_A)
    else:
        speed_Q, speed_A = float(speed), float(speed)
    # Convert engine
    engine_Q, engine_A = None, None
    if args.engine:
        if args.engine.find(':') == -1:
            engine_Q, engine_A = args.engine, args.engine
        else:
            engine_Q, engine_A = args.engine.split(':')
    if not os.path.isfile(quiz_file):
        print('File not found: ' + quiz_file)
        sys.exit(1)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    if not os.path.isdir(output_directory):
        print('Not a directory: ' + output_directory)
        sys.exit(1)
    parent, dirname = os.path.split(os.path.normpath(output_directory))
    raw_directory = os.path.join(parent, '.raw_' + dirname)
    if not os.path.exists(raw_directory):
        os.makedirs(raw_directory)
        print('Created: ' + raw_directory)
    else:
        print('Raw audio directory: ' + raw_directory)

    tts = QuizTTS(lang_Q, lang_A, engine_Q, engine_A, speed_Q, speed_A)
    tts.quiz_list_to_audio(quiz_file, raw_directory, args.invert_QA, args.split_by_comma)

    speed = (1.0, 1.0)  # No speed change here
    make_section_mp3_files(
        raw_directory,
        output_directory,
        speed,
        float(args.gain),
        args.repeat_question,
        int(args.pause_duration),
        args.add_number_audio
    )

if __name__ == '__main__':
    main()
