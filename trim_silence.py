#!/usr/bin/env python
import os
import argparse
import subprocess
import time
from pydub import AudioSegment

def trim_with_ffmpeg(input_file, output_file, min_silence=1.0, threshold_db=-20):
    # Get original audio length
    original_audio = AudioSegment.from_file(input_file)
    original_length = len(original_audio) / 1000
    print(f'Original audio length: {original_length:.1f}s')
    
    # Use FFmpeg to process and output directly to final format
    output_format = os.path.splitext(output_file)[1][1:]
    ff_cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-af", f"silenceremove=start_periods=1:start_silence={min_silence}:"
               f"start_threshold={threshold_db}dB:"
               f"stop_periods=-1:stop_silence={min_silence}:"
               f"stop_threshold={threshold_db}dB",
        output_file
    ]
    start_time = time.time()
    print(f'Trimming silence from "{input_file}" with FFmpeg...')
    subprocess.run(ff_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    end_time = time.time()
    print(f'Processing time: {end_time - start_time:.2f} seconds')

    # Get processed audio length for statistics
    processed_audio = AudioSegment.from_file(output_file)
    processed_length = len(processed_audio) / 1000
    reduction = original_length - processed_length
    reduction_percent = (reduction / original_length) * 100
    
    print(f'Processed audio length: {processed_length:.1f}s')
    print(f'Reduced by: {reduction:.1f}s ({reduction_percent:.1f}%)')
    
    return None  # No need to return audio object

def main():
    parser = argparse.ArgumentParser(description='Trims silence from an audio file and inserts a beep sound.')
    parser.add_argument('--min-silence', '-m', type=float, default=2.0, help='Minimum length of silence in seconds')
    parser.add_argument('--threshold', '-t', type=int, default=-20, help='Silence threshold in dB')
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

    trim_with_ffmpeg(args.input_file, args.output_file, args.min_silence, args.threshold)

if __name__ == '__main__':
    main()
