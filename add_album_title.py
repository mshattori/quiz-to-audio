#!/usr/bin/env python

from pydub import AudioSegment
import sys
import os

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('dirname')
    parser.add_argument('album')
    args = parser.parse_args()
    if not os.path.isdir(args.dirname):
        print(f'Error: "{args.dirname}" is not a directory')
        sys.exit(1)
    if not os.path.isdir('output'):
        os.mkdir('output')
    for filename in os.listdir(args.dirname):
        filepath = os.path.join(args.dirname, filename)
        audio = AudioSegment.from_file(filepath)
        title = os.path.splitext(os.path.basename(filepath))[0]
        tags = { 'title': title, 'album': args.album, 'artist': 'Homebrew'}
        # WALKMAN supports ID3v2.3, not v2.4, which is the default value of pydub
        outfilename=os.path.join('output', title + '.mp3')
        audio.export(outfilename, format='mp3', tags=tags, id3v2_version='3')
        print(outfilename)
