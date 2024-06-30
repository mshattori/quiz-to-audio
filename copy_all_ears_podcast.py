import os
import re
import shutil
import subprocess
from glob import glob
from pydub.utils import mediainfo

HOME = os.environ.get('HOME')
TARGET_ALBUM = 'All Ears English Podcast'
TARGET_DIR = f'{HOME}/Desktop/All_Ears_English'
TRANSCRIBE = '../callan-transcribe/transcribe-mp3.sh'

def get_tags(mp3_file):
    metadata = mediainfo(mp3_file)
    return metadata['TAG']

def normalize_for_filename(filename):
    return re.sub('\W', '', filename.replace(' ', '_'))

def adjust_subtitle(s):
    s = s.replace('OK.', 'OK,')
    s = s.replace('Yes.', 'Yes,')
    s = s.replace('Year.', 'Year,')
    s = s.replace('Right.', 'Right,')
    return s.replace('. ', '.\n\n')

if __name__ == '__main__':

    glob_path = f'{HOME}/Library/Group Containers/*.groups.com.apple.podcasts/Library/Cache/*.mp3'
    files = glob(glob_path)
    for file in files:
        tags = get_tags(file)
        album = tags.get('album')
        if album == TARGET_ALBUM:
            title = tags['title']
            dest_file = normalize_for_filename(title) + '.mp3'
            dest_file = os.path.join(TARGET_DIR, dest_file)
            if not os.path.exists(dest_file):
                print('Copying', dest_file)
                shutil.copy(file, dest_file)
                env = os.environ.copy()
                env['LANGUAGES'] = 'en-US,ja-JP'
                basename = os.path.basename(dest_file)
                subtitle_filename = os.path.splitext(basename)[0] + '.txt'
                if not os.path.exists(subtitle_filename):
                    subprocess.run(f'{TRANSCRIBE} {dest_file}', shell=True, env=env)
                markdown_file = os.path.splitext(dest_file)[0] + '.md'
                with open(markdown_file, 'w') as f:
                    print(f'# {title}', file=f)
                    with open(subtitle_filename) as subtitle_file:
                        f.write(adjust_subtitle(subtitle_file.read()))

