#!/usr/bin/env python
"""
This script sets the 'title' and 'album' ID3 tags for all audio files
in a given directory.

For each audio file, the script automatically sets the ID3 title tag from the
filename (without its extension). The ID3 album tag is set to a value
provided as a command-line argument.

It takes a source directory and an album name as command-line arguments.
The script iterates through each file in the source directory, checking for
common audio formats (.mp3, .m4a, .wav). For each valid audio file, it
uses the pydub library to perform the following actions:

1.  Loads the audio data from the file.
2.  Generates a 'title' tag from the filename by removing the file extension.
3.  Assembles a dictionary of ID3 tags, including the generated title,
    the user-provided album name, and a hardcoded artist name ('Homebrew').
4.  Exports the audio data as a new MP3 file into a specified output
    directory (defaults to 'output').
5.  During export, it specifically sets the ID3 tag version to 2.3 to ensure
    compatibility with devices like Walkman, which may not support the
    default version 2.4.

The script prints the path of each newly created file upon successful export.
"""

from pydub import AudioSegment
import sys
import os

if __name__ == '__main__':
    import argparse

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Sets the title and album name for all audio files in a directory. The title is derived from the filename.')

    # Required arguments
    parser.add_argument('--dirname', '-d', required=True, help='Directory containing audio files')
    parser.add_argument('--album', required=True, help='Album name to be tagged in the audio files')

    # Optional argument
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
        # Check file extension and skip if it's not an audio file
        if not os.path.splitext(filename)[1] in ('.mp3', '.m4a', '.wav'):
            print(f'Skipping {filename}')
            continue

        filepath = os.path.join(args.dirname, filename)
        
        # Load the audio file
        audio = AudioSegment.from_file(filepath)
        
        # Use the filename (without extension) as the title
        title = os.path.splitext(os.path.basename(filepath))[0]

        # Create tags for the audio file
        tags = {'title': title, 'album': args.album, 'artist': 'Homebrew'}

        # Define the output filename and export the audio file with tags
        outfilename = os.path.join(args.output_dir, title + '.mp3')
        
        # NOTE: WALKMAN supports ID3v2.3, not v2.4 which is the default for pydub
        audio.export(outfilename, format='mp3', tags=tags, id3v2_version='3')
        print(f'Exported: {outfilename}')
