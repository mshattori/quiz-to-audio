#!/usr/bin/env python
import os
import sys
import re
from polly import QuizPolly
from audio import make_section_mp3_files

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--lang-QA', default='EE', choices=('EE', 'EJ', 'JE'))
    parser.add_argument('--speed-QA', default='1.0')
    parser.add_argument('--invert-QA', action='store_true', default=False)
    parser.add_argument('--repeat-question', action='store_true', default=False)
    parser.add_argument('--pause-duration', default='500')
    parser.add_argument('--add-number-audio', action='store_true', default=False)
    parser.add_argument('--split-by-comma', action='store_true', default=False)
    parser.add_argument('quiz_filename')
    parser.add_argument('output_directory')
    args = parser.parse_args()

    quiz_file = args.quiz_filename 
    output_directory = args.output_directory 
    lang_Q, lang_A = 'en-US', 'en-US'
    if args.lang_QA == 'EJ':
        lang_A = 'ja-JP'
    if args.lang_QA == 'JE':
        lang_Q = 'ja-JP'
    speed = args.speed_QA
    if not re.fullmatch(r'\d+(\.\d+)?(:\d+(\.\d+)?)?', speed):
        print('Invalid speed format. The correct format is "0.9", "1.0:0.9", etc.')
        sys.exit(1)
    if speed.find(':') > 0:
        speed_Q, speed_A = speed.split(':')
        speed = (float(speed_Q), float(speed_A))
    else:
        speed = (float(speed), float(speed))

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

    with open(quiz_file) as f:
        quiz_list = [l.rstrip('\n') for l in f.readlines() if not _is_skip_line(l)]

    QuizPolly(lang_Q, lang_A).quiz_list_to_audio(quiz_list, raw_directory, args.invert_QA, args.split_by_comma)

    make_section_mp3_files(
        raw_directory,
        output_directory,
        speed,
        args.repeat_question,
        int(args.pause_duration),
        args.add_number_audio
    )

def _is_skip_line(l):
    return (len(l.strip()) <= 0 or
            l.lstrip()[0] == '#' or
            l.find(':=') == -1 or
            re.fullmatch('\s*\(.*\)\s*', l))

if __name__ == '__main__':
    main()
