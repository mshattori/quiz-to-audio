#!/usr/bin/env python
from pydub import AudioSegment, silence
import argparse
import os

def trim_silence(input_file, min_silence_len=2000, silence_thresh=-25, keep_silence=500):
    """
    Removes silent sections from the specified file and inserts .number_audio/beep.mp3 instead.

    :param input_file: Input file path.
    :param min_silence_len: Minimum length of silence in milliseconds.
    :param silence_thresh: Silence threshold in dBFS.
    :param keep_silence: Length of silence to keep after splitting in milliseconds.
    """

    sound = AudioSegment.from_file(input_file)
    
    # Load beep sound
    dirname = os.path.dirname(__file__)
    beep_sound = AudioSegment.from_file(os.path.join(dirname, '.number_audio', 'beep.mp3'))

    # Find non-silent chunks
    chunks = silence.split_on_silence(sound, min_silence_len=min_silence_len, silence_thresh=silence_thresh, keep_silence=keep_silence)
    print(f'Found {len(chunks)} non-silent chunks')
    if len(chunks) < 2:
        print('No non-silent chunks found')
        return sound

    # Combine chunks with beep sound
    combined = AudioSegment.empty()
    for i, chunk in enumerate(chunks):
        if i != 0:
            combined += beep_sound
        combined += chunk

    return combined

def main():
    parser = argparse.ArgumentParser(description='Trims silence from an audio file and inserts a beep sound.')
    parser.add_argument('--min-silence', '-m', type=int, default=2000, help='Minimum length of silence in milliseconds')
    parser.add_argument('--threshold', '-t', type=int, default=-25, help='Silence threshold in dBFS')
    parser.add_argument('--keep', '-k', type=int, default=500, help='Length of silence to keep in milliseconds')
    parser.add_argument('input_file', help='Input audio file')
    parser.add_argument('output_file', help='Output audio file')

    args = parser.parse_args()

    # Check if the input file exists
    if not os.path.isfile(args.input_file):
        print(f'Error: Input file "{args.input_file}" does not exist.')
        return

    # Check if the output directory exists, if not create it
    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    trimmed_audio = trim_silence(args.input_file, args.min_silence, args.threshold, args.keep)

    format=os.path.splitext(args.output_file)[1][1:]
    trimmed_audio.export(args.output_file, format=format)

if __name__ == '__main__':
    main()
