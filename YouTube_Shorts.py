import glob
import gspread
import datetime
import textwrap
import numpy as np
import pandas as pd
import logging
import os
import cv2
from moviepy.editor import *
from moviepy.config import change_settings
from moviepy.editor import AudioFileClip
from moviepy.editor import ImageClip
from moviepy.audio.AudioClip import AudioArrayClip
from pydub import AudioSegment
from google.cloud import texttospeech
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials
from flask import flash
from PIL import Image

logger = logging.getLogger('YouTube_Shorts')

change_settings({"IMAGEMAGICK_BINARY": "/usr/local/bin/convert"})

def add_silence_to_audio(audio_file_path, silence_duration_before = 600, silence_duration_after = 700):
    audio = AudioSegment.from_file(audio_file_path, format="mp3")
    silence_before = AudioSegment.silent(duration=silence_duration_before)
    silence_after = AudioSegment.silent(duration=silence_duration_after)
    final_audio = silence_before + audio + silence_after
    final_audio.export(audio_file_path, format="mp3")

def get_data_as_dataframe(sheet):
    data = sheet.get_all_values()
    df = pd.DataFrame(data)
    df.columns = df.iloc[0]
    df = df.iloc[1:]
    return df

def count_creatable_video():
    scope = ["https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('/Users/keisukewatanabe/Documents/GitHub/YouTube/.keys/YouTube_text_to_speech_speedy-anthem-340212-e4195f19e826.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1e_3MvXLtcQz0QtT4vOjW-__uN6ReKDU9CVKvW76KjAE").worksheet("GCol")
    df = get_data_as_dataframe(sheet)
    count = 0
    for _, row in df.iterrows():
        if row['Status'] != 'Created' and row['Status'] != 'Skipped':
            count += 1
    return count

def convert_gray_to_rgb(img_path):
    with Image.open(img_path) as img:
        if img.mode == 'L':  
            rgb_img = img.convert('RGB')
            rgb_img.save(img_path)

def create_video(num_videos):
    logger.debug("Starting create_video function in YouTube_Shorts")
    try:
        scope = ["https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name('/Users/keisukewatanabe/Documents/GitHub/YouTube/.keys/YouTube_text_to_speech_speedy-anthem-340212-e4195f19e826.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1e_3MvXLtcQz0QtT4vOjW-__uN6ReKDU9CVKvW76KjAE").worksheet("GCol")
        df = get_data_as_dataframe(sheet)
        bgm = AudioFileClip('/Users/keisukewatanabe/Documents/GitHub/YouTube/Assets/music/Kevin_MacLeod_-_Canon_in_D_Major.mp3')
        creatable_videos = count_creatable_video()

        if num_videos > creatable_videos:
            message = f"The maximum number of videos creatable is {creatable_videos}."
            print(message)
            num_videos = creatable_videos

        index = 2
        created_count = 0

        for index, row in df.iterrows():
            index += 2
            status = row['Status']
            print(f"Row: {index}, Status: {status}")
            if status != 'Created':

                author_name = row['Author']
                author = "3 Quotes from " + author_name
                quote1 = row['Quote1']
                quote2 = row['Quote2']
                quote3 = row['Quote3']

                quotes = [quote1, quote2, quote3]
                quotes = sorted(quotes, key=len)

                quote1 = quotes[0]
                quote2 = quotes[1]
                quote3 = quotes[2]

                if not quote1 or not quote3:
                    print(f"Row: {index}, Quote1 or Quote3 is empty. Skipping this row.")
                    continue

                if len(quote1) > 220 or len(quote2) > 220 or len(quote3) > 220:
                    print(f"Row: {index}, Author: {author_name} has a quote longer than 300 characters. Skipping...")
                    df.at[index-2, 'Status'] = 'Skipped'
                    continue

                expected_filename = f"{author_name.replace(' ', '_')}.jpg"
                if expected_filename not in os.listdir('input'):
                    continue

                texts = [author, quote1, quote2, quote3]
                audio_clips = []
                clips = []
                start_time = 0

                key_path = '/Users/keisukewatanabe/Documents/GitHub/YouTube/.keys/YouTube_text_to_speech_speedy-anthem-340212-e4195f19e826.json'
                client = texttospeech.TextToSpeechClient.from_service_account_json(key_path)

                file_path = 'input/' + expected_filename
                file_list = glob.glob('input/' + expected_filename)
                if file_list:
                    temp_clip = ImageClip(file_list[0])
                    temp_clip = temp_clip.resize(width=1080)
                    img_height = temp_clip.size[1]
                    print("Img_width: " + str(img_height))

                for i, text in enumerate(texts):

                    num_chars = len(text.replace('\n', ''))
                    if num_chars <= 100:
                        fontsize = 58
                    elif 100 < num_chars <= 200:
                        fontsize = 52
                    else:
                        fontsize = 48
                    
                    if fontsize == 58:
                        wrap_length = 24
                    elif fontsize == 52:
                        wrap_length = 22
                    else:
                        wrap_length = 26

                    text = textwrap.fill(text, wrap_length)

                    temp_txt_clip = TextClip(text, fontsize=fontsize, color='white')
                    txt_height = temp_txt_clip.size[1]

                    half_txt_space = ((1920 - img_height) / 2)

                    position_x = ("center")
                    position_y = ((1920 - img_height) / 2) - (txt_height / 3)
                    print("Position Y: " +str(position_y))

                    synthesis_input = texttospeech.SynthesisInput(text=text)
                    voice = texttospeech.VoiceSelectionParams(
                        language_code="en-US",
                        name="en-US-Wavenet-B",
                        ssml_gender=texttospeech.SsmlVoiceGender.MALE
                    )

                    audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    sample_rate_hertz=44100
                    )

                    response = client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                    )

                    speech_file = f"speech_{i}.mp3"
                    with open(speech_file, "wb") as out:
                        out.write(response.audio_content)

                    add_silence_to_audio(speech_file)

                    audio = AudioFileClip(speech_file, fps=44100).set_start(start_time)
                    print(f"Generated audio clip with duration {audio.duration} and fps {audio.fps}")
                    audio_clips.append(audio)

                    os.remove(speech_file)

                    duration = audio.duration
                    if i == 2:
                        duration += 0.8

                    txt_clip = TextClip(text, fontsize = fontsize, color='white')
                    txt_clip = txt_clip.set_duration(duration).set_start(start_time)
                    txt_clip = txt_clip.set_position((position_x, position_y))
                    clips.append(txt_clip)
                    
                    start_time += duration

                total_duration = start_time

                convert_gray_to_rgb(file_path)

                for m in file_list:
                    clip = ImageClip(m).set_duration(total_duration).resize(width=1080)
                    clip = clip.set_position(("center", 1100))
                    clips.insert(0, clip)

                final_audio = concatenate_audioclips(audio_clips)

                bgm = bgm.subclip(0, total_duration)
                final_audio_bgm = CompositeAudioClip([final_audio, bgm.volumex(0.4)])

                concat_clip = CompositeVideoClip(clips, size=(1080,1920))

                concat_clip = concat_clip.set_audio(final_audio_bgm)
                
                output_directory = "output"
                current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = os.path.join(output_directory, f"{author_name}_{current_time}.mp4")
                concat_clip.write_videofile(output_filename, fps=24, codec='libx264', audio_codec='aac', audio_bitrate="320k") #,write_logfile=True)

                file_name_only = os.path.basename(output_filename)
                df.at[index-2, 'Status'] = 'Created'
                df.at[index-2, 'File Name'] = file_name_only
                created_count += 1
                if created_count >= num_videos:
                    break
            index += 1
        set_with_dataframe(sheet, df)
        return created_count
    except Exception:
        logger.exception("Error occurred in create_video function")

if __name__ == '__main__':
    app.run(debug=True)