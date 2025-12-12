import boto3
from openai import OpenAI
import os
import re
import random
import shutil
import json
import io
from tempfile import mkdtemp, NamedTemporaryFile
from glob import glob
from contextlib import closing
from pydub import AudioSegment

POLLY_MAX_CHARS = 1000 # Max characters per chunk for Amazon Polly

def _split_text_into_chunks(text, max_chars):
    """
    Splits text into chunks, trying to respect sentence boundaries if possible,
    but primarily focusing on staying under max_chars.
    """
    chunks = []
    current_chunk = ""
    
    # Define common Japanese sentence endings
    sentence_enders = ["。", "！", "？", ".", "!", "?"]

    # Split text into potential sentences
    # This regex splits by sentence_enders but keeps the delimiter
    sentences = re.findall(r'[^。！？\.!\?]+[。！？\.!\?]*', text)

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += sentence
        else:
            if current_chunk: # Add current_chunk if not empty
                chunks.append(current_chunk)
            current_chunk = sentence # Start new chunk with current sentence
            
            # If a single sentence is longer than max_chars, split it forcibly
            while len(current_chunk) > max_chars:
                chunks.append(current_chunk[:max_chars])
                current_chunk = current_chunk[max_chars:]
    
    if current_chunk: # Add any remaining text as a chunk
        chunks.append(current_chunk)
            
    return [chunk.strip() for chunk in chunks if chunk.strip()]

random.seed(0)  # make it consistent

# Pattern to match a paren that can contain inner parens
PAREN_PATTERN = r'\([^()]*(?:\([^()]+\)[^()]*)*\)'

def load_quiz(quiz_file):
    with open(quiz_file, encoding='utf-8') as f:
        lines = f.readlines()
    quiz_lines = [l.strip() for l in lines if not _is_skip_line(l)]
    return [_split_quiz(quiz) for quiz in quiz_lines]

def _is_skip_line(l):
    return (len(l.strip()) <= 0 or
            l.lstrip()[0] == '#' or
            l.find(':=') == -1 or
            re.fullmatch(r'\s*\(.*\)\s*', l)) # skip lines that contain only parens

def _split_quiz(quiz):
    q_text, a_text = quiz.split(' := ')
    q_text = re.sub(PAREN_PATTERN, '', q_text)
    a_text = re.sub(PAREN_PATTERN, '', a_text)
    if re.search('[()]', q_text) or re.search('[()]', a_text):
        raise ValueError('Unmatched paren: "{}"'.format(quiz))

    q_text, a_text = q_text.strip(), a_text.strip()
    if len(q_text) == 0 or len(a_text) == 0:
        raise ValueError(f'Q or A is empty: "{quiz}"')
    # Replace slash '/' sign with comma plus 'or'
    q_text = re.sub(r'\s*/\s*', ', or ', q_text)
    a_text = re.sub(r'\s*/\s*', ', or ', a_text)
    return (q_text, a_text)

# References:
# Amazon Polly:
# - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/polly.html
# - https://aws.amazon.com/jp/polly/pricing/
# OpenAI:
# - https://platform.openai.com/docs/api-reference/audio/createSpeech
# - https://openai.com/api/pricing/
# Note:
# polly neural: 16 USD / 1M characters
# polly long-form: 100 USD / 1M characters
# openai TTS: 15 USD / 1M characters
class AmazonPollyEngine(object):
    EXCLUDE_VOICES = ('Ivy', 'Justin', 'Kevin', 'Matthew')

    def __init__(self, engine='neural'):
        self.polly = boto3.client('polly')
        self.engine = engine

    def text_to_audio(self, text, lang, voice, speed=None):
        if speed:
            speed = self._convert_to_percentage(speed)
            text = f'<speak><prosody rate="{speed}">{text}</prosody></speak>'
            text_type = 'ssml'
        else:
            text_type = 'text'
        resp = self.polly.synthesize_speech(
                            Engine=self.engine,
                            LanguageCode=lang,
                            OutputFormat='mp3',
                            Text=text,
                            TextType=text_type,
                            VoiceId=voice)
        with closing(resp['AudioStream']) as stream:
            audio_content = stream.read()
        return AudioSegment.from_file(io.BytesIO(audio_content), format='mp3')

    def get_speakers(self, lang):
        resp = self.polly.describe_voices(Engine=self.engine, LanguageCode=lang)
        voices = [voice['Name'] for voice in resp['Voices']]
        voices = list(filter(lambda v: v not in self.EXCLUDE_VOICES, voices))
        random.shuffle(voices)
        return voices

    @staticmethod
    def _convert_to_percentage(value):
        """
        Converts any decimal value between 0 and 1 to a percentage string.

        Args:
            value: The value to convert (str).

        Returns:
            The converted value as a percentage string (str).
        """
        try:
            float_value = float(value)
            if 0 <= float_value <= 1:
                percentage = int(float_value * 100)
                return f"{percentage}%"
            else:
                return value  # Return the original value if it's outside the range 0 to 1
        except ValueError:
            return value  # Return the original value if it cannot be converted to float

class OpenAISpeechEngine(object):
    def __init__(self, engine='tts-1'):
        self.engine = engine
        self.openai = OpenAI()

    def text_to_audio(self, text, lang, voice, speed=None):
        response = self.openai.audio.speech.create(
            model=self.engine,
            input=text,
            voice=voice,
            response_format='mp3',
            speed=speed or 1.0
        )

        audio_content = io.BytesIO(response.content)
        return AudioSegment.from_file(audio_content, format='mp3')

    def get_speakers(self, lang):
        return ['alloy', 'ash', 'coral', 'echo', 'fable', 'onyx', 'nova', 'sage', 'shimmer']

def init_tts_engine(engine):
    if engine in ('standard', 'neural', 'long-form', 'generative'):
        return AmazonPollyEngine(engine)
    elif engine.startswith('openai-') and engine.split('-', maxsplit=1)[1] in ('tts-1', 'tts-1-hd'):
        engine = engine.split('-', maxsplit=1)[1]
        return OpenAISpeechEngine(engine)
    else:
        raise ValueError(f'Invalid engine: "{engine}"')

class SpeakerGroup(object):
    @classmethod
    def make_speaker_groups(cls, lang_Q, lang_A, engine_Q, engine_A):
        speakers_Q = init_tts_engine(engine_Q).get_speakers(lang_Q)
        speakers_A = init_tts_engine(engine_A).get_speakers(lang_A)
        if set(speakers_Q) != set(speakers_A):
            group_Q = SpeakerGroup(lang_Q, speakers_Q)
            group_A = SpeakerGroup(lang_A, speakers_A)
        else:
            n = int(len(speakers_Q)/2)
            group_Q = SpeakerGroup(lang_Q, speakers_Q[0:n])
            group_A = SpeakerGroup(lang_A, speakers_Q[n:])
        return group_Q, group_A

    def __init__(self, lang, speakers):
        self._lang = lang
        self._speakers = speakers

    @property
    def lang(self):
        return self._lang

    def get_speaker(self):
        random.shuffle(self._speakers)
        return self._speakers[0]

class SimpleTTS(object):
    def __init__(self, lang, speaker=None, engine='neural'):
        self.engine = init_tts_engine(engine)
        self.lang = lang
        if speaker:
            self.speaker = speaker
        else:
            self.speaker = self.engine.get_speakers(lang)[0]

    def make_audio_file(self, text, output_filename, speed=None):
        if os.path.exists(output_filename):
            print('Skip existing file "{}"'.format(output_filename))
            return
        parent_dir = os.path.dirname(output_filename)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        # Split text into chunks to handle API limits
        text_chunks = _split_text_into_chunks(text, POLLY_MAX_CHARS)
        
        combined_audio = AudioSegment.empty()
        for i, chunk in enumerate(text_chunks):
            print(f"Synthesizing chunk {i+1}/{len(text_chunks)} for '{os.path.basename(output_filename)}'")
            try:
                audio_segment = self.engine.text_to_audio(chunk, self.lang, self.speaker, speed)
                combined_audio += audio_segment
            except Exception as e:
                print(f"Error synthesizing chunk {i+1}: {e}")
                # Decide how to handle errors for individual chunks
                # For now, just re-raise if it's a critical error, or log and continue
                raise

        if combined_audio:
            print(f'Exporting {output_filename}')
            combined_audio.export(output_filename, format='mp3')
        else:
            print(f"No audio generated for {output_filename}")

class QuizTTS(object):
    def __init__(self, lang_Q, lang_A, engine_Q='neural', engine_A='neural', speed_Q=1.0, speed_A=1.0):
        self.polly = boto3.client('polly')
        self.engine_Q = init_tts_engine(engine_Q)
        self.engine_A = init_tts_engine(engine_A)
        group_Q, group_A = SpeakerGroup.make_speaker_groups(lang_Q, lang_A, engine_Q, engine_A)
        self.voice_group_Q = group_Q
        self.voice_group_A = group_A
        self.speed_Q = speed_Q
        self.speed_A = speed_A

    def quiz_list_to_audio(self, quiz_file, audio_directory, invert_QA, split_by_comma):
        self.invert_QA = invert_QA
        self.split_by_comma = split_by_comma
        os.stat(audio_directory)  # to make sure that the directory exists and otherwise raise an exception
        self.original_directory = audio_directory
        self.quiz_audio_dict = QuizAudioDict(audio_directory)
        new_directory = mkdtemp()
        try:
            quiz_list = load_quiz(quiz_file)
        except ValueError as e:
            print(f'Failed to convert: {str(e)}')
            raise e
        for index, q_a in enumerate(quiz_list):
            q_text, a_text = q_a
            self._quiz_to_audio(index, q_text, a_text, new_directory)
        self.quiz_audio_dict.copy_files(new_directory)
        shutil.rmtree(audio_directory)
        os.rename(new_directory, audio_directory)

    def _quiz_to_audio(self, index, q_text, a_text, output_directory):
        if self.invert_QA:
            q_text, a_text = a_text, q_text
        q_lang, a_lang = self.voice_group_Q.lang, self.voice_group_A.lang
        # Raw audio filename convention:
        #   [:number:]-[Q|A]-[:voice:].mp3
        #   - number: 3-digit number with left 0 padding
        q_voice, a_voice = self._decide_speakers(index)
        number = '{:03d}'.format(index+1)
        q_filename = os.path.join(output_directory, '-'.join([number, 'Q', q_voice.title(), str(self.speed_Q)]) + '.mp3')
        self._make_audio(q_text, 'Q', q_filename, q_voice)
        a_filename = os.path.join(output_directory, '-'.join([number, 'A', a_voice.title(), str(self.speed_A)]) + '.mp3')
        self._make_audio(a_text, 'A', a_filename, a_voice)
    
    def _make_audio(self, text, side, filepath, voice):
        filename = os.path.basename(filepath)
        if not self.quiz_audio_dict.exists(text, filename):
            self.text_to_audio(text, side, filepath, voice)
        self.quiz_audio_dict.update_filename(text, filename)

    def _decide_speakers(self, index):
        speaker_Q = self.voice_group_Q.get_speaker()
        speaker_A = self.voice_group_A.get_speaker()
        if (self.voice_group_Q.lang == self.voice_group_A.lang) and (index % 2 == 1):
            # shufful Q and A each time
            speaker_Q, speaker_A = speaker_A, speaker_Q
        return speaker_Q, speaker_A

    def text_to_audio(self, text, side, output_filename, voice):
        if os.path.exists(output_filename):
            print('Skip existing file "{}"'.format(output_filename))
            return
        print('Making "{file}" for "{text}"'.format(file=os.path.basename(output_filename), text=text))
        audio = self._convert_text_to_audio_segment_with_split_pause(text, side, voice)
        audio.export(output_filename, format='mp3')

    def _convert_text_to_audio_segment_with_split_pause(self, text, side, voice):
        # split by synonym block: e.g. [=stick to]
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
            if self.split_by_comma:
                sub_segment_list = []
                for sub_block in split_by_commas(block):
                    audio = self._convert_text_to_audio_segment(sub_block, side, voice)
                    sub_segment_list.extend([audio, comma_pause])
                if sub_segment_list:
                    sub_segment_list.pop()  # Remove the last pause
                audio_segment_list.extend(sub_segment_list)
            else:
                audio = self._convert_text_to_audio_segment(block, side, voice)
                audio_segment_list.append(audio)
            audio_segment_list.append(synonym_pause)
        if audio_segment_list:
            audio_segment_list.pop()  # Remove the last pause
        # Join segments
        combined_audio = audio_segment_list[0]
        for segment in audio_segment_list[1:]:
            combined_audio += segment
        return combined_audio

    def _convert_text_to_audio_segment(self, text, side, voice):
        if side == 'Q':
            engine = self.engine_Q
            lang = self.voice_group_Q.lang
            speed = self.speed_Q
        elif side == 'A':
            engine = self.engine_A
            lang = self.voice_group_A.lang
            speed = self.speed_A
        else:
            raise ValueError('Invalid side: "{}"'.format(side))
        return engine.text_to_audio(text, lang, voice, speed)

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

    def exists(self, text, filename):
        if self.initial:
            # Return True to prevent it from creating new file if audio files had been created
            # before the dict file was implemented.
            orig_filepath = os.path.join(self.orig_directory, filename)
            if os.path.exists(orig_filepath):
                return True
        return (text in self.orig_dict or text in self.new_dict)

    def update_filename(self, text, filename):
        if self.initial:
            # At initial attempt and if the file exits, assume that the orig dict contains the record.
            # It allows it to copy the file from the orig directory in self.copy_file() later.
            orig_filepath = os.path.join(self.orig_directory, filename)
            if os.path.exists(orig_filepath):
                self.orig_dict[text] = filename
        self.new_list.append((filename, text))
        # If exists, must not overwrite. It allows it to copy existing the audio file as the new
        # filename when there are the same text in different Q&A items.
        self.new_dict.setdefault(text, filename)

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

def list_speakers(lang, engine):
    tts_engine = init_tts_engine(engine)
    speakers = tts_engine.get_speakers(lang)
    print('\n'.join(speakers))

def calculate_cost(text, engine, exchange_rate):
    char_count = len(text)
    if engine == 'neural':
        cost_usd = (char_count / 1_000_000) * 16
    elif engine == 'long-form':
        cost_usd = (char_count / 1_000_000) * 100
    elif engine.startswith('openai-'):
        cost_usd = (char_count / 1_000_000) * 15
    else:
        raise ValueError(f'Invalid engine: "{engine}"')
    cost_jpy = cost_usd * exchange_rate
    return cost_jpy

def synthesize_speech(lang, speaker, input_file, output_file, engine=None, speed=None):
    with open(input_file, 'r') as f:
        text = ''
        for line in f.readlines():
            if line.strip().startswith('#'):
                continue
            text += line
    SimpleTTS(lang, speaker, engine).make_audio_file(text, output_file, speed)

if __name__ == '__main__':
    from argparse import ArgumentParser
    from dotenv import load_dotenv
    parser = ArgumentParser(description="Polly text-to-speech command line tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    # Define the 'speakers' command
    subparser = subparsers.add_parser('speakers', help='List available speakers')
    subparser.add_argument('--lang', '-l', required=True, help='Language code')
    subparser.add_argument('--engine', required=False, default='neural', help='TTS engine')
    subparser.add_argument('--env-file', required=False, default='.env', help='Environment file')
    # Define the 'synthesize' command
    subparser = subparsers.add_parser('synthesize', help='Synthesize speech from text')
    subparser.add_argument('--lang', '-l', required=True, help='Language code')
    subparser.add_argument('--speaker', default=None, help='Speaker name')
    subparser.add_argument('--input-file', '-i', required=True, help='Input text file')
    subparser.add_argument('--output-file', '-o', required=False, default=None, help='Output audio file')
    subparser.add_argument('--engine', required=False, default='neural', help='TTS engine')
    subparser.add_argument('--speed', required=False, default=None, help='Speech speed')
    subparser.add_argument('--env-file', required=False, default='.env', help='Environment file')
    # Define the 'calculate-cost' command
    subparser = subparsers.add_parser('calc-cost', help='Calculate the cost of synthesizing speech')
    subparser.add_argument('--engine', required=False, default='neural', help='TTS engine')
    subparser.add_argument('--exchange-rate', required=False, type=float, default=1.5, help='Exchange rate from USD to JPY')
    subparser.add_argument('input_file', help='Input text file')

    args = parser.parse_args()
    if args.command == 'speakers':
        load_dotenv(args.env_file, override=True)
        list_speakers(args.lang, args.engine)
    elif args.command == 'synthesize':
        load_dotenv(args.env_file, override=True)
        if not args.output_file:
            args.output_file = os.path.splitext(args.input_file)[0] + '.mp3'
        synthesize_speech(args.lang, args.speaker, args.input_file, args.output_file, args.engine, args.speed)
    elif args.command == 'calc-cost':
        quiz_list = load_quiz(args.input_file)
        text = '\n'.join([q + '\n' + a for q, a in quiz_list])
        cost_jpy = calculate_cost(text, args.engine, args.exchange_rate)
        print(f'Size: {len(text)} characters, Cost: {cost_jpy:.2f} JPY')
    else:
        print('Invalid command:', args.command)
        parser.print_help()