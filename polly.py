import boto3
import os
import re
import random
import shutil
import json
import io
from tempfile import mkdtemp
from glob import glob
from contextlib import closing
from pydub import AudioSegment

random.seed(0)  # make it consistent

# Pattern to match a paren that can contain inner parens
PAREN_PATTERN = r'\([^()]*(?:\([^()]+\)[^()]*)*\)'

def split_quiz(quiz):
    q_text, a_text = quiz.split(' := ')
    q_text = re.sub(PAREN_PATTERN, '', q_text)
    a_text = re.sub(PAREN_PATTERN, '', a_text)
    if re.search('[()]', q_text) or re.search('[()]', a_text):
        raise ValueError('Unmatched paren: "{}"'.format(quiz))

    q_text, a_text = q_text.strip(), a_text.strip()
    if len(q_text) == 0 or len(a_text) == 0:
        raise ValueError(f'Q or A is empty: {quiz}')
    # Replace slash '/' sign with comma plus 'or'
    q_text = re.sub(r'\s*/\s*', ', or ', q_text)
    a_text = re.sub(r'\s*/\s*', ', or ', a_text)
    return (q_text, a_text)

class SpeakerGroup(object):
    EXCLUDE_VOICES = ('Ivy', 'Justin', 'Kevin', 'Matthew')

    @classmethod
    def make_speaker_groups(cls, lang_Q, lang_A, engine):
        if lang_Q == lang_A:
            speakers = cls.get_speaker_names(lang_Q, engine)
            n = int(len(speakers)/2)
            group_Q = SpeakerGroup(lang_Q, speakers[0:n])
            group_A = SpeakerGroup(lang_A, speakers[n:])
        else:
            speakers_Q = cls.get_speaker_names(lang_Q, engine)
            group_Q = SpeakerGroup(lang_Q, speakers_Q)
            speakers_A = cls.get_speaker_names(lang_A, engine)
            group_A = SpeakerGroup(lang_A, speakers_A)
        return group_Q, group_A

    @classmethod
    def get_speaker_names(cls, lang, engine):
        polly = boto3.client('polly')
        resp = polly.describe_voices(Engine=engine, LanguageCode=lang)
        voices = [voice['Name'] for voice in resp['Voices']]
        voices = list(filter(lambda v: v not in cls.EXCLUDE_VOICES, voices))
        random.shuffle(voices)
        return voices

    def __init__(self, lang, speakers):
        self._lang = lang
        self._speakers = speakers

    @property
    def lang(self):
        return self._lang

    def get_speaker(self):
        random.shuffle(self._speakers)
        return self._speakers[0]

class QuizPolly(object):
    def __init__(self, lang_Q, lang_A, engine='neural'):
        self.polly = boto3.client('polly')
        self.engine = engine
        group_Q, group_A = SpeakerGroup.make_speaker_groups(lang_Q, lang_A, engine)
        self.lang_Q = lang_Q
        self.lang_A = lang_A
        self.voice_group_Q = group_Q
        self.voice_group_A = group_A

    def quiz_list_to_audio(self, quiz_list, audio_directory, invert_QA=False):
        os.stat(audio_directory)  # to make sure that the directory exists and otherwise raise an exception
        self.original_directory = audio_directory
        self.quiz_audio_dict = QuizAudioDict(audio_directory)
        new_directory = mkdtemp()
        for index, quiz in enumerate(quiz_list):
            self._quiz_to_audio(index, quiz, new_directory, invert_QA)
        self.quiz_audio_dict.copy_files(new_directory)
        shutil.rmtree(audio_directory)
        os.rename(new_directory, audio_directory)

    def _quiz_to_audio(self, index, quiz, output_directory, invert_QA):
        try:
            q_text, a_text = split_quiz(quiz)
        except ValueError as e:
            print('Failed to convert: ({}) "{}"'.format(index+1, quiz))
            raise e
        if invert_QA:
            q_text, a_text = a_text, q_text
        q_lang, a_lang = self.voice_group_Q.lang, self.voice_group_A.lang
        # Raw audio filename convention:
        #   [:number:]-[Q|A]-[:voice:].mp3
        #   - number: 3-digit number with left 0 padding
        q_voice, a_voice = self._decide_speakers(index)
        number = '{:03d}'.format(index+1)
        q_filename = os.path.join(output_directory, '-'.join([number, 'Q', q_voice]) + '.mp3')
        self._make_audio(q_text, q_lang, q_filename, q_voice)
        a_filename = os.path.join(output_directory, '-'.join([number, 'A', a_voice]) + '.mp3')
        self._make_audio(a_text, a_lang, a_filename, a_voice)
    
    def _make_audio(self, text, lang, filename, voice):
        original_filename = os.path.join(self.original_directory, os.path.basename(filename))
        if not self.quiz_audio_dict.exists(text) or not os.path.exists(original_filename):
            # It's a new text, OR NO dict file and/or NO audio file.
            self.text_to_audio(text, lang, filename, voice)
        self.quiz_audio_dict.update_filename(text, os.path.basename(filename))

    def _decide_speakers(self, index):
        speaker_Q = self.voice_group_Q.get_speaker()
        speaker_A = self.voice_group_A.get_speaker()
        if (self.voice_group_Q.lang == self.voice_group_A.lang) and (index % 2 == 1):
            # shufful Q and A each time
            speaker_Q, speaker_A = speaker_A, speaker_Q
        return speaker_Q, speaker_A

    def text_to_audio(self, text, lang, output_filename, voice=None):
        if os.path.exists(output_filename):
            print('Skip existing file "{}"'.format(output_filename))
            return
        if not voice:
            if self.lang_Q == lang:
                voice = self.voice_group_Q.get_speaker()
            elif self.lang_A == lang:
                voice = self.voice_group_A.get_speaker()
        print('Making "{file}" for "{text}"'.format(file=os.path.basename(output_filename), text=text))
        audio = self._text_to_audio_segment_with_split(text, lang, voice)
        audio.export(output_filename, format='mp3')

    def _text_to_audio_segment_with_split(self, text, lang, voice):
        def split_by_synonym_blocks(text):
            blocks = []
            while True:
                m = re.search(r'\[\=([^]]+)\]', text)
                if not m:
                    blocks.append(text)
                    break
                blocks.append(text[0:m.start()])
                blocks.append('equals ' + m.group(1))
                text = text[m.end():]
            return [b.strip() for b in blocks if b.strip()]
        def split_by_commas(text):
            blocks = re.split(r'[,;、]\s*', text)
            return [b.strip() for b in blocks if b.strip()]

        synonym_pause = AudioSegment.silent(duration=1200)
        comma_pause = AudioSegment.silent(duration=500)
        audio_segment_list = []
        for block in split_by_synonym_blocks(text):
            sub_segment_list = []
            for sub_block in split_by_commas(block):
                audio = self._text_to_audio_segment(sub_block, lang, voice)
                sub_segment_list.extend([audio, comma_pause])
            if sub_segment_list:
                sub_segment_list.pop()  # Remove the last pause
            audio_segment_list.extend(sub_segment_list)
            audio_segment_list.append(synonym_pause)
        if audio_segment_list:
            audio_segment_list.pop()  # Remove the last pause
        # Join segments
        combined_audio = audio_segment_list[0]
        for segment in audio_segment_list[1:]:
            combined_audio += segment
        return combined_audio

    def _text_to_audio_segment(self, text, lang, voice):
        resp = self.polly.synthesize_speech(
                            Engine=self.engine,
                            LanguageCode=lang,
                            OutputFormat='mp3',
                            Text=text,
                            VoiceId=voice)
        with closing(resp['AudioStream']) as stream:
            audio_content = stream.read()
        return AudioSegment.from_file(io.BytesIO(audio_content), format='mp3')


class QuizAudioDict:
    _DICT_FILENAME = '.quiz_audio_dict.json'

    def __init__(self, original_directory):
        self.orig_directory = original_directory
        self.orig_dict = {}
        self.initial = True  # If True, the dict file NOT yet created
        dict_filename = os.path.join(original_directory, self._DICT_FILENAME)
        if os.path.exists(dict_filename):
            self.initial = False
            with open(dict_filename, encoding='utf-8') as f:
                loaded_dict = json.load(f)
            for filename, text in loaded_dict.items():
                if not os.path.exists(os.path.join(original_directory, filename)):
                    print(f'"{filename}" had been removed')
                    continue
                self.orig_dict[text] = filename
        self.new_dict = {}
        self.new_list = []

    def exists(self, text):
        if self.initial:
            # Always return True to prevent it from creating new file, because audio files
            # could have been created before QuizAudioDict was implemented.
            return True
        return (text in self.orig_dict or text in self.new_dict)

    def update_filename(self, text, filename):
        if self.initial:
            # At initial attempt, assume that it already exists in the orig dict.
            self.orig_dict[text] = filename
        self.new_list.append((filename, text))
        self.new_dict[text] = filename

    def copy_files(self, new_directory):
        '''Copy original files to the new directory with updated name.
        '''
        dict_records = {}
        for (filename, text) in self.new_list:
            dict_records[filename] = text
            new_filepath = os.path.join(new_directory, filename)
            if os.path.exists(new_filepath):
                continue
            if text in self.orig_dict:
                orig_filepath = os.path.join(self.orig_directory, self.orig_dict[text])
            elif text in self.new_dict:
                orig_filepath = os.path.join(new_directory, self.new_dict[text])
            else:
                raise ValueError(f'Text not exist: "{text}"')
            shutil.copy2(orig_filepath, new_filepath)

        dict_filename = os.path.join(new_directory, self._DICT_FILENAME)
        with open(dict_filename, 'w', encoding='utf-8') as f:
            json.dump(dict_records, f, ensure_ascii=False, indent=2)
