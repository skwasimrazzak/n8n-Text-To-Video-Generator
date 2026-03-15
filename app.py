import os
import uuid
import traceback

from flask import Flask, request, jsonify

from gtts import gTTS

from PIL import Image, ImageDraw, ImageFont

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

app = Flask(__name__)

OUTPUT_DIR = r"D:\Learning\n8n-workflows\explainer-video\output"
RESOLUTION = (1280, 720)
FONT_SIZE = 36
BACKGROUND_COLOR = (30, 30, 60)
TEXT_COLOR = (255, 255, 255)
DEFAULT_SLIDE_DURATION = 4

def validate_input(text):
    if not text or not text.strip():
        raise ValueError("Input text is empty.")

# def split_into_scenes(text):
#     scenes = [s.strip() for s in text.strip().split('\n\n') if s.strip()]
#     if not scenes:
#         raise ValueError("No scenes could be parsed from the input text.")
#     return scenes

def split_into_scenes(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    scenes = [s.strip() for s in text.strip().split('\n\n') if s.strip()]
    if not scenes:
        raise ValueError("No scenes could be parsed from the input text.")
    return scenes

def text_to_speech(text, audio_path):
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(audio_path)
    except Exception as e:
        raise RuntimeError(f"TTS failed: {str(e)}")

def create_slide_image(scene_text, index, temp_dir):
    img = Image.new('RGB', RESOLUTION, color=BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", FONT_SIZE)
    except:
        font = ImageFont.load_default()

    words = scene_text.split()
    lines = []
    current_line = ""
    max_width = RESOLUTION[0] - 100

    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    line_height = FONT_SIZE + 10
    total_height = len(lines) * line_height
    y = (RESOLUTION[1] - total_height) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (RESOLUTION[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill=TEXT_COLOR, font=font)
        y += line_height

    img_path = os.path.join(temp_dir, f"slide_{index}.png")
    img.save(img_path)
    return img_path

def generate_video(scenes, audio_path, output_path, slide_duration):
    try:
        temp_dir = os.path.dirname(audio_path)
        audio = AudioFileClip(audio_path)

        clips = []
        for i, scene in enumerate(scenes):
            img_path = create_slide_image(scene, i, temp_dir)
            clip = ImageClip(img_path).set_duration(slide_duration)
            clips.append(clip)

        video = concatenate_videoclips(clips, method="compose")

        video_duration = video.duration
        if audio.duration > video_duration:
            audio = audio.subclip(0, video_duration)

        final = video.set_audio(audio)
        final.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac'
        )

        audio.close()
        final.close()

    except Exception as e:
        raise RuntimeError(f"Video render failed: {str(e)}")

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({"status": "error", "message": "No text field in request."}), 400

        text = data.get('text', '')
        slide_duration = int(data.get('slide_duration', DEFAULT_SLIDE_DURATION))

        validate_input(text)
        scenes = split_into_scenes(text)

        unique_id = str(uuid.uuid4())[:8]
        temp_dir = os.path.join(OUTPUT_DIR, f"temp_{unique_id}")
        os.makedirs(temp_dir, exist_ok=True)

        audio_path = os.path.join(temp_dir, "narration.mp3")
        output_path = os.path.join(OUTPUT_DIR, f"explainer_{unique_id}.mp4")

        text_to_speech(text, audio_path)
        generate_video(scenes, audio_path, output_path, slide_duration)

        return jsonify({
            "status": "success",
            "output_file": output_path,
            "scenes_count": len(scenes)
        })

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Unexpected error: {traceback.format_exc()}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)