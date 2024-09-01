#!/usr/bin/env python
import sys
import os
import argparse
from pydub import AudioSegment
from pydub.silence import split_on_silence

def split_by_silence(input_file, output_dir, min_silence_len, silence_thresh):
    """
    Splits an audio file into segments based on silence.

    :param input_file: Path to the input audio file.
    :param min_silence_len: Minimum length of silence to consider for a split (in milliseconds).
    :param silence_thresh: Silence threshold (in dB). Lower values mean more silence will be considered.
    :return: List of AudioSegment instances representing the split audio.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Load the audio file
    audio = AudioSegment.from_file(input_file)

    # Split audio based on silence
    audio_chunks = split_on_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=True,
    )

    # Export each chunk as a separate file
    stemname = os.path.splitext(os.path.basename(input_file))[0]
    for i, chunk in enumerate(audio_chunks):
        output_filename = os.path.join(output_dir, f'{stemname}_{i}.mp3')
        chunk.export(output_filename, format='mp3')
        print(f'Created {output_filename}')

    return audio_chunks

def split_by_duration(input_file, segment_minutes, output_dir, overlap=5):
    """
    Splits an audio file into segments based on the specified duration and overlap.

    :param input_file: Path to the input audio file.
    :param segment_minutes: Duration of each segment in minutes.
    :param output_dir: Directory to save the split segments.
    :param overlap: Overlap between segments in seconds. Default is 5 seconds.
    :return: Generator yielding tuples of segment filename, start time, and end time.
    """
    if segment_minutes <= 0:
        raise ValueError('Segment length must be greater than zero minutes.')
    if overlap < 0:
        raise ValueError('Overlap must be non-negative.')

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Load the audio file
    audio = AudioSegment.from_file(input_file)

    # Calculate segment duration and overlap in milliseconds
    segment_duration_ms = segment_minutes * 60 * 1000
    overlap_ms = overlap * 1000

    # Extract the file name and extension from the input file path
    stemname = os.path.splitext(os.path.basename(input_file))[0]

    start_ms = 0
    index = 1
    while start_ms < len(audio):
        end_ms = min(start_ms + segment_duration_ms, len(audio))
        segment = audio[start_ms:end_ms]

        output_filename = os.path.join(output_dir, f'{stemname}-{index}.mp3')
        segment.export(output_filename, format='mp3')
        print(f'Created {output_filename}')

        yield output_filename, start_ms, end_ms

        start_ms += segment_duration_ms - overlap_ms
        index += 1

def main():
    parser = argparse.ArgumentParser(description='Audio file splitter')
    subparsers = parser.add_subparsers(dest='command')

    # 'silence' subcommand
    parser_silence = subparsers.add_parser('silence', help='Split audio by silence')
    parser_silence.add_argument('input_file', help='Input audio file')
    parser_silence.add_argument('--output_dir', '-d', help='Output directory', default=os.path.join(os.getcwd(), 'split_audio_files'))
    parser_silence.add_argument('--min_silence_len', type=int, default=800, help='Minimum length of silence to consider for a split (in milliseconds)')
    parser_silence.add_argument('--silence_thresh', type=int, default=-20, help='Silence threshold (in dB)')

    # 'duration' subcommand
    parser_duration = subparsers.add_parser('duration', help='Split audio by duration')
    parser_duration.add_argument('input_file', help='Input audio file')
    parser_duration.add_argument('--output_dir', '-d', help='Output directory', default=os.path.join(os.getcwd(), 'split_audio_files'))
    parser_duration.add_argument('--segment_minutes', '-m', type=int, required=True, help='Length of each segment in minutes')
    parser_duration.add_argument('--overlap', type=int, default=5, help='Overlap between segments in seconds')

    args = parser.parse_args()

    if args.command == 'silence':
        split_by_silence(args.input_file, args.output_dir, args.min_silence_len, args.silence_thresh)
    elif args.command == 'duration':
        for result in split_by_duration(args.input_file, args.segment_minutes, args.output_dir, args.overlap):
            print(result)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
