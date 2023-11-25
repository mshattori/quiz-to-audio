#!/usr/bin/env python
import os
import sys
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2
from audio import _make_number_audio

def process_audio_files(input_dir, output_dir):
    # List and sort mp3 files in the directory
    audio_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.mp3')])

    number = 1
    for file in audio_files:
        # Construct the full file path
        file_path = os.path.join(input_dir, file)

        # Get the number audio segment
        number_filename = _make_number_audio(number)
        number_audio_segment = AudioSegment.from_file(number_filename)

        pause = AudioSegment.silent(duration=500)

        # Load the original audio file
        original_audio = AudioSegment.from_file(file_path)

        # Insert the number audio segment at the beginning
        combined_audio = number_audio_segment + pause + original_audio

        # Update the title in metadata
        audio_file = MP3(file_path, ID3=ID3)
        if audio_file.tags is None:
            audio_file.add_tags()

        original_title = audio_file.tags.get('TIT2')
        new_title = f"{number:02d} {original_title.text[0]}" if original_title else f"{number:02d} Unknown Title"
        audio_file.tags['TIT2'] = TIT2(encoding=3, text=new_title)
        # Convert tags to dictionary for export
        tag_dict = {tag.FrameID: tag.text[0] for tag in audio_file.tags.values()}

        file_path = os.path.join(output_dir, file)

        # Save the combined audio with updated metadata
        combined_audio.export(file_path, format="mp3", tags=tag_dict, id3v2_version="3")
        print(f'Created {file_path}')

        number += 1

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Insert number audio")
    parser.add_argument('input_dir', help='Input directory that stores mp3 files')
    parser.add_argument('output_dir', help='Input directory that stores mp3 files')
    args = parser.parse_args()

    if not os.path.exists(args.input_dir):
        print(f'Directory not found: {args.input_dir}')
        sys.exit(1)
    os.makedirs(args.output_dir, exist_ok=True)

    process_audio_files(args.input_dir, args.output_dir)

