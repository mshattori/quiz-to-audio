import os
import argparse
from pydub import AudioSegment

def clip_audio(input_file, output_file, offset, tail_offset):
    """
    Clips an audio file by removing parts from the beginning and the end.

    :param input_file: Path to the input audio file.
    :param output_file: Path to the output audio file.
    :param offset: Offset from the start of the audio file in milliseconds.
    :param tail_offset: Offset from the end of the audio file in milliseconds.
    """
    # Load the audio file
    audio = AudioSegment.from_file(input_file)

    # Clip the audio
    if offset > 0:
        audio = audio[offset:]
    if tail_offset > 0:
        audio = audio[:-tail_offset]

    # Export the clipped audio
    audio.export(output_file, format="mp3")


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Clip an audio file.')
    parser.add_argument('--offset', type=int, help='Offset from the start in milliseconds', required=False, default=0)
    parser.add_argument('--tail-offset', type=int, help='Offset from the end in milliseconds', required=False, default=0)
    parser.add_argument('input_file', type=str, help='Input audio file')
    args = parser.parse_args()

    # Determine the output file name
    output_file = os.path.splitext(args.input_file)[0] + '.clipped.mp3'

    # Clip the audio
    clip_audio(args.input_file, output_file, args.offset, args.tail_offset)
