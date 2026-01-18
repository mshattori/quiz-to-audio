import os
import random
import shutil
import json
from tempfile import mkdtemp
from typing import Tuple

from pydub import AudioSegment

from speech_audio_tools.tts import init_tts_engine
from .quiz_parser import load_quiz


class DummyTTSEngine:
    """Offline/dummy engine for tests; generates silence."""

    def text_to_audio(self, text, lang, voice, speed=None):
        # 60 ms per character, minimum 300 ms
        duration = max(300, int(len(text) * 60))
        return AudioSegment.silent(duration=duration)

    def get_speakers(self, lang):
        return ["dummy"]


def init_engine_with_dummy(engine: str):
    if engine == "dummy":
        return DummyTTSEngine()
    return init_tts_engine(engine)


class SpeakerGroup:
    @classmethod
    def make_speaker_groups(cls, lang_Q, lang_A, engine_Q, engine_A):
        speakers_Q = init_engine_with_dummy(engine_Q).get_speakers(lang_Q)
        speakers_A = init_engine_with_dummy(engine_A).get_speakers(lang_A)
        if set(speakers_Q) != set(speakers_A) or len(speakers_Q) < 2:
            group_Q = SpeakerGroup(lang_Q, speakers_Q)
            group_A = SpeakerGroup(lang_A, speakers_A)
        else:
            n = int(len(speakers_Q) / 2)
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


class QuizAudioDict:
    _DICT_FILENAME = ".quiz_audio_dict.json"

    def __init__(self, original_directory):
        self.orig_directory = original_directory
        self.orig_dict = {}
        self.initial = True
        dict_filename = os.path.join(original_directory, self._DICT_FILENAME)
        if os.path.exists(dict_filename):
            self.initial = False
            with open(dict_filename, encoding="utf-8") as f:
                loaded_dict = json.load(f)
            for filename, text in loaded_dict.items():
                if not os.path.exists(os.path.join(original_directory, filename)):
                    continue
                self.orig_dict[text] = filename
        self.new_dict = {}
        self.new_list = []

    def exists(self, text, filename):
        if self.initial:
            orig_filepath = os.path.join(self.orig_directory, filename)
            if os.path.exists(orig_filepath):
                return True
        return text in self.orig_dict or text in self.new_dict

    def update_filename(self, text, filename):
        if self.initial:
            orig_filepath = os.path.join(self.orig_directory, filename)
            if os.path.exists(orig_filepath):
                self.orig_dict[text] = filename
        self.new_list.append((filename, text))
        self.new_dict.setdefault(text, filename)

    def copy_files(self, new_directory):
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
        with open(dict_filename, "w", encoding="utf-8") as f:
            json.dump(dict_records, f, ensure_ascii=False, indent=2)


class QuizTTS:
    def __init__(self, lang_Q, lang_A, engine_Q="neural", engine_A="neural", speed_Q=1.0, speed_A=1.0):
        self.engine_Q = init_engine_with_dummy(engine_Q)
        self.engine_A = init_engine_with_dummy(engine_A)
        group_Q, group_A = SpeakerGroup.make_speaker_groups(lang_Q, lang_A, engine_Q, engine_A)
        self.voice_group_Q = group_Q
        self.voice_group_A = group_A
        self.speed_Q = speed_Q
        self.speed_A = speed_A

    def quiz_list_to_audio(self, quiz_file, audio_directory, invert_QA, split_by_comma):
        self.invert_QA = invert_QA
        self.split_by_comma = split_by_comma
        os.stat(audio_directory)
        self.original_directory = audio_directory
        self.quiz_audio_dict = QuizAudioDict(audio_directory)
        new_directory = mkdtemp()
        quiz_list = load_quiz(quiz_file)
        for index, (q_text, a_text) in enumerate(quiz_list):
            self._quiz_to_audio(index, q_text, a_text, new_directory)
        self.quiz_audio_dict.copy_files(new_directory)
        shutil.rmtree(audio_directory)
        os.rename(new_directory, audio_directory)

    def _quiz_to_audio(self, index, q_text, a_text, output_directory):
        if self.invert_QA:
            q_text, a_text = a_text, q_text
        q_voice, a_voice = self._decide_speakers(index)
        number = "{:03d}".format(index + 1)
        q_filename = os.path.join(
            output_directory, "-".join([number, "Q", q_voice.title(), str(self.speed_Q)]) + ".mp3"
        )
        self._make_audio(q_text, "Q", q_filename, q_voice)
        a_filename = os.path.join(
            output_directory, "-".join([number, "A", a_voice.title(), str(self.speed_A)]) + ".mp3"
        )
        self._make_audio(a_text, "A", a_filename, a_voice)

    def _make_audio(self, text, side, filepath, voice):
        filename = os.path.basename(filepath)
        if not self.quiz_audio_dict.exists(text, filename):
            self.text_to_audio(text, side, filepath, voice)
        self.quiz_audio_dict.update_filename(text, filename)

    def _decide_speakers(self, index):
        speaker_Q = self.voice_group_Q.get_speaker()
        speaker_A = self.voice_group_A.get_speaker()
        if (self.voice_group_Q.lang == self.voice_group_A.lang) and (index % 2 == 1):
            speaker_Q, speaker_A = speaker_A, speaker_Q
        return speaker_Q, speaker_A

    def text_to_audio(self, text, side, output_filename, voice):
        if os.path.exists(output_filename):
            print('Skip existing file "{}"'.format(output_filename))
            return
        audio = self._convert_text_to_audio_segment_with_split_pause(text, side, voice)
        audio.export(output_filename, format="mp3")

    def _convert_text_to_audio_segment_with_split_pause(self, text, side, voice):
        def split_by_synonym_blocks(text):
            blocks = []
            import re

            while True:
                m = re.search(r"\[\=([^]]+)\]", text)
                if not m:
                    blocks.append(text)
                    break
                blocks.append(text[0 : m.start()])
                blocks.append("equals " + m.group(1))
                text = text[m.end() :]
            return [b.strip() for b in blocks if b.strip()]

        def split_by_commas(text):
            import re

            blocks = re.split(r"[,;、]\s*", text)
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
                    sub_segment_list.pop()
                audio_segment_list.extend(sub_segment_list)
            else:
                audio = self._convert_text_to_audio_segment(block, side, voice)
                audio_segment_list.append(audio)
            audio_segment_list.append(synonym_pause)
        if audio_segment_list:
            audio_segment_list.pop()
        combined_audio = audio_segment_list[0]
        for segment in audio_segment_list[1:]:
            combined_audio += segment
        return combined_audio

    def _convert_text_to_audio_segment(self, text, side, voice):
        if side == "Q":
            engine = self.engine_Q
            lang = self.voice_group_Q.lang
            speed = self.speed_Q
        elif side == "A":
            engine = self.engine_A
            lang = self.voice_group_A.lang
            speed = self.speed_A
        else:
            raise ValueError(f"Invalid side: {side}")
        return engine.text_to_audio(text, lang, voice, speed)


__all__ = ["QuizTTS"]
