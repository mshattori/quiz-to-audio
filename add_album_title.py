#!/usr/bin/env python

from pydub import AudioSegment
import sys
import os

if __name__ == '__main__':
    import argparse

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Add album title to audio files.')

    # Required arguments
    parser.add_argument('--dirname', '-d', required=True, help='Directory containing audio files')
    parser.add_argument('--album', required=True, help='Album name to be tagged in audio files')

    # Optional argument with default value
    parser.add_argument('--output-dir', '-o', default='output', help='Directory to save output files (default: output)')

    args = parser.parse_args()

    # Check if the input directory exists
    if not os.path.isdir(args.dirname):
        print(f'Error: "{args.dirname}" is not a directory')
        sys.exit(1)

    # Create output directory if it does not exist
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)

    # Process each audio file in the input directory
    for filename in sorted(os.listdir(args.dirname)):
        if not os.path.splitext(filename)[1] in ('.mp3', '.m4a', '.wav'):
            print(f'Skipping {filename}')
            continue

        filepath = os.path.join(args.dirname, filename)
        audio = AudioSegment.from_file(filepath)
        title = os.path.splitext(os.path.basename(filepath))[0]

        # Create tags for the audio file
        tags = {'title': title, 'album': args.album, 'artist': 'Homebrew'}

        # Define output filename and export audio file with tags
        outfilename = os.path.join(args.output_dir, title + '.mp3')
        # NOTE: WALKMAN supports ID3v2.3, not v2.4, which is the default value of pydub
        audio.export(outfilename, format='mp3', tags=tags, id3v2_version='3')
        print(f'Exported: {outfilename}')
