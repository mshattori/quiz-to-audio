#!/usr/bin/env python
import sys
from polly import *
from audio import *

if len(sys.argv) < 3:
    print('Usage: quiz2audio.py quiz-filename output-directory\n')
    sys.exit(1)

quiz_file = sys.argv[1]
output_directory = sys.argv[2]

if not os.path.isfile(quiz_file):
    print('File not found: ' + quiz_file)
    sys.exit(1)
if not os.path.exists(output_directory):
    os.makedirs(audio_directory)
if not os.path.isdir(output_directory):
    print('Not a directory: ' + output_directory)
    sys.exit(1)
parent, dirname = os.path.split(os.path.normpath(output_directory))
raw_directory = os.path.join(parent, '.raw_' + dirname)
if not os.path.exists(raw_directory):
    os.makedirs(raw_directory)
    print('Created: ' + raw_directory)
else:
    print('Raw audiro directory: ' + raw_directory)

with open(quiz_file) as f:
    quiz_list = [l.rstrip('\n') for l in f.readlines() if l.find(':=') != -1 ]

QuizPolly().quiz_list_to_audio(quiz_list, raw_directory)

make_section_mp3_files(raw_directory, output_directory)
