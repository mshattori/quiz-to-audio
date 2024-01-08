import sys
import os
import argparse
from pydub import AudioSegment
from pydub.silence import split_on_silence

def split_audio_by_silence(input_file, output_dir, min_silence_len, silence_thresh):
    """
    Splits an audio file into segments based on silence.

    :param input_file: Path to the input audio file.
    :param min_silence_len: Minimum length of silence to consider for a split (in milliseconds).
    :param silence_thresh: Silence threshold (in dB). Lower values mean more silence will be considered.
    :return: List of AudioSegment instances representing the split audio.
    """
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
        output_filename = os.path.join(output_dir, f"{stemname}_{i}.mp3")
        chunk.export(output_filename, format="mp3")
        print(f"Created {output_filename}")

    return audio_chunks

def main(args):
    stemname = os.path.splitext(os.path.basename(args.input_file))[0]
    output_dir = os.path.join(args.output_dir, stemname)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    split_audio_by_silence(args.input_file, output_dir, args.min_silence_len, args.silence_thresh)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Split audio file by silence")
    parser.add_argument('input_file', help='Input audio file')
    parser.add_argument('--output_dir', help='Output directory', default=os.path.join(os.getcwd(), 'split_audio_files'))
    parser.add_argument('--min_silence_len', type=int, default=800, help='Minimum length of silence to consider for a split (in milliseconds)')
    parser.add_argument('--silence_thresh', type=int, default=-20, help='Silence threshold (in dB)')
    args = parser.parse_args()

    main(args)
