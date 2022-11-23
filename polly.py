import boto3
import os
import re
import random
from glob import glob
from contextlib import closing

def split_quiz(quiz):
    q_text, a_text = quiz.split(' := ')
    q_text = re.sub('\(.*\)', '', q_text)
    a_text = re.sub('\(.*\)', '', a_text)
    if re.search('[()]', q_text) or  re.search('[()]', a_text):
        raise ValueError('Unmatched paren: "{}"'.format(quiz))

    return q_text.strip(), a_text.strip()

voice_exclusions = ['Ivy', 'Justin', 'Kevin']

class QuizPolly(object):
    def __init__(self, lang='en-US', engine='neural'):
        self.polly = boto3.client('polly')
        self.lang = lang
        self.engine = engine
        resp = self.polly.describe_voices(Engine=self.engine, LanguageCode=self.lang)
        voices = [voice['Name'] for voice in resp['Voices'] if voice['Name'] not in voice_exclusions]
        random.seed(0)  # make it consistent
        random.shuffle(voices)
        n = int(len(voices)/2)
        self.voice_group1 = (voices[0:n])
        self.voice_group2 = (voices[n:])

    def quiz_list_to_audio(self, quiz_list, output_directory):
        os.stat(output_directory)  # to make sure that the directory exists and otherwise raise an exception
        for index, quiz in enumerate(quiz_list):
            self._quiz_to_audio(index, quiz, output_directory)

    def _quiz_to_audio(self, index, quiz, output_directory):
        try:
            q_text, a_text = split_quiz(quiz)
        except ValueError as e:
            print('Failed to convert: ({}) "{}"'.format(index+1, quiz))
        # Raw audio filename convention:
        #   [:number:]-[Q|A]-[:voice:].mp3
        #   - number: 3-digit number with left 0 padding
        q_voice, a_voice = self._decide_voices(index)
        number = '{:03d}'.format(index+1)
        q_filename = os.path.join(output_directory, '-'.join([number, 'Q', q_voice]) + '.mp3')
        if len(glob(q_filename.replace(q_voice, '*'))) == 0:
            self._text_to_audio(q_text, q_voice, q_filename)
        # else:
        #     print('Skip existing file for "{}-Q"'.format(number))
        a_filename = os.path.join(output_directory, '-'.join([number, 'A', a_voice]) + '.mp3')
        if len(glob(a_filename.replace(a_voice, '*'))) == 0:
            self._text_to_audio(a_text, a_voice, a_filename)
        # else:
        #     print('Skip existing file for "{}-A"'.format(number))
    
    def _decide_voices(self, index):
        random.shuffle(self.voice_group1)
        random.shuffle(self.voice_group2)
        if index % 2 == 0:
            return self.voice_group1[0], self.voice_group2[0]
        return self.voice_group2[0], self.voice_group1[0]

    def _text_to_audio(self, text, voice, output_filename):
        if os.path.exists(output_filename):
            print('Skip existing file "{}"'.format(output_filename))
            return
        print('Making "{}"'.format(output_filename))

        resp = self.polly.synthesize_speech(
                            Engine=self.engine,
                            LanguageCode=self.lang,
                            OutputFormat='mp3',
                            Text=text,
                            VoiceId=voice)
        with closing(resp['AudioStream']) as stream:
            with open(output_filename, 'wb') as file:
                file.write(stream.read())
