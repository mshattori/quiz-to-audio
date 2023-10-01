import boto3
import os
import re
import random
from glob import glob
from contextlib import closing

random.seed(0)  # make it consistent

def split_quiz(quiz):
    q_text, a_text = quiz.split(' := ')
    q_text = re.sub('\(.*\)', '', q_text)
    a_text = re.sub('\(.*\)', '', a_text)
    if re.search('[()]', q_text) or  re.search('[()]', a_text):
        raise ValueError('Unmatched paren: "{}"'.format(quiz))

    return q_text.strip(), a_text.strip()

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

    def quiz_list_to_audio(self, quiz_list, output_directory, invert_QA=False):
        os.stat(output_directory)  # to make sure that the directory exists and otherwise raise an exception
        for index, quiz in enumerate(quiz_list):
            self._quiz_to_audio(index, quiz, output_directory, invert_QA)

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
        if len(glob(q_filename.replace(q_voice, '*'))) == 0:
            self.text_to_audio(q_text, q_lang, q_filename, q_voice)
        a_filename = os.path.join(output_directory, '-'.join([number, 'A', a_voice]) + '.mp3')
        if len(glob(a_filename.replace(a_voice, '*'))) == 0:
            self.text_to_audio(a_text, a_lang, a_filename, a_voice)
    
    def _decide_speakers(self, index):
        speaker_Q = self.voice_group_Q.get_speaker()
        speaker_A = self.voice_group_A.get_speaker()
        if (self.voice_group_Q.lang == self.voice_group_A.lang) and (index % 2 == 1):
            # shufful Q and A each time
            speaker_Q, speaker_A = speaker_A, speaker_Q
        return speaker_Q, speaker_A

    def text_to_audio(self, text, lang, output_filename, voice=None):
        if not voice:
            if self.lang_Q == lang:
                voice = self.voice_group_Q.get_speaker()
            elif self.lang_A == lang:
                voice = self.voice_group_A.get_speaker()

        if os.path.exists(output_filename):
            print('Skip existing file "{}"'.format(output_filename))
            return
        print('Making "{}"'.format(output_filename))

        resp = self.polly.synthesize_speech(
                            Engine=self.engine,
                            LanguageCode=lang,
                            OutputFormat='mp3',
                            Text=text,
                            VoiceId=voice)
        with closing(resp['AudioStream']) as stream:
            with open(output_filename, 'wb') as file:
                file.write(stream.read())
