import os
import re
from glob import glob
from pydub import AudioSegment
from pydub import effects
from collections import OrderedDict

# https://stackoverflow.com/questions/43408833/how-to-increase-decrease-playback-speed-on-wav-file
def speed_change(sound, speed=1.0):
    # Manually override the frame_rate. This tells the computer how many
    # samples to play per second
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    })

    # convert the sound with altered frame rate to a standard frame rate
    # so that regular playback programs will work right. They often only
    # know how to play audio at standard frame rate (like 44.1k)
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)

def _combine_QA(file_Q, file_A, repeat_question=True, pause_duration=500, end_duration=1500):
    seg_Q = AudioSegment.from_file(file_Q, 'mp3')
    seg_A = AudioSegment.from_file(file_A, 'mp3')
    pause = AudioSegment.silent(duration=pause_duration)
    # !!! speed down 5%
    seg_Q = speed_change(seg_Q, 0.95)
    seg_A = speed_change(seg_A, 0.95)
    seg = seg_Q
    if repeat_question:
        seg += pause + seg_Q
    seg += pause + seg_A + AudioSegment.silent(duration=end_duration)
    return seg

def _collect_ordinal_numbers(input_directory):
    """parse filenames '<number>-Q-<voice>.mp3' in a directory and collect 'number's.
    """
    numbers_set = set()

    for question_file in glob(os.path.join(input_directory, '*-Q-*.mp3')):
        number_match_pattern = os.path.join(input_directory, '(\d+)-Q-(\w+).mp3')
        m = re.match(number_match_pattern, question_file)
        if not m:
            print('WARN: Unexpected file', question_file)
            continue
        numbers_set.add(m.group(1))
        
    return sorted(list(numbers_set))

def _find_mp3_file(input_directory, number, pattern):
    glob_pattern = os.path.join(input_directory, number + pattern + '.mp3')
    files = glob(glob_pattern)
    if len(files) < 1:
        return None
    return files[0]

def _find_question_file(input_directory, number):
    return _find_mp3_file(input_directory, number, '-Q-*')

def _find_answer_file(input_directory, number):
    return _find_mp3_file(input_directory, number, '-A-*')

def _combine_audio_list(audio_list):
    seg = AudioSegment.empty()
    for a in audio_list:
        seg = seg + a
    return seg

def make_section_mp3_files(input_directory, output_directory, section_unit=10, artist='Homebrew'):
    numbers = _collect_ordinal_numbers(input_directory)

    # separate numbers into sections
    # one section has 10 numbers when the section unit is 10 
    for i in range(0, len(numbers), section_unit):
        numbers_in_section = numbers[i:i+section_unit]
        start, end = numbers_in_section[0], numbers_in_section[-1]
        # make a section filename: e.g. '001-010.mp3'
        section_filename = os.path.join(output_directory, '{}-{}.mp3'.format(start, end))
        if os.path.exists(section_filename):
            continue
        section_audio_segments = []

        for number in numbers_in_section:
            # join corresponding Q & A audio files
            file_Q = _find_question_file(input_directory, number)
            file_A = _find_answer_file(input_directory, number)
            if not (file_Q and file_A):
                print('WARN: Corresponding files not found for ', number)
                continue
            file_QA = _combine_QA(file_Q, file_A)
            section_audio_segments.append(file_QA)

        section_audio = _combine_audio_list(section_audio_segments)
        album = os.path.basename(output_directory).replace('_', ' ')
        tags = { 'title': '{}-{} {}'.format(start, end, album), 'album': album, 'artist': artist }
        # WALKMAN supports ID3v2.3, not v2.4, which is the default value of pydub
        section_audio.export(section_filename, format='mp3', tags=tags, id3v2_version='3')
        print('Created "{}"'.format(section_filename))
    