#!/usr/bin/env python
import argparse
from audio import join_files

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Join audio files")

    parser.add_argument('--output-filename', '-o', required=True, help='Output filename (e.g., out.mp3)')
    parser.add_argument('--title', required=True, help='Title of the track')
    parser.add_argument('--album', required=True, help='Album name')
    parser.add_argument('--artist', required=True, help='Artist name')
    parser.add_argument('inputs', nargs='+', help='Input audio files')

    args = parser.parse_args()

    join_files(args.inputs, args.output_filename, args.title, args.album, args.artist)
    print('Created', args.output_filename)
