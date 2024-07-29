from flask import Flask, request, send_file, jsonify
import os
import yt_dlp
import cv2
from requests.exceptions import RequestException

app = Flask(__name__)

UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
PROCESSED_FOLDER = os.environ.get('PROCESSED_FOLDER', 'processed')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def enhance_resolution(input_file, output_folder):
    # Load video
    cap = cv2.VideoCapture(input_file)

    if not cap.isOpened():
        return None, "Error opening video file."

    # Get input video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Set output video resolution to 2K (2560x1440)
    new_width, new_height = 2560, 1440

    # Create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    output_file_path = os.path.join(output_folder, f"{os.path.basename(input_file)}_enhanced.avi")
    out = cv2.VideoWriter(output_file_path, fourcc, fps, (new_width, new_height))

    while(cap.isOpened()):
        ret, frame = cap.read()
        if ret:
            # Resize frame to 2K resolution
            resized_frame = cv2.resize(frame, (new_width, new_height))
            out.write(resized_frame)
        else:
            break

    # Release video capture and writer objects
    cap.release()
    out.release()

    return output_file_path, None

@app.before_first_request
def ensure_directories():
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(app.config['PROCESSED_FOLDER']):
        os.makedirs(app.config['PROCESSED_FOLDER'])

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify(error="No file uploaded"), 400

    file = request.files['file']

    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        output_filename, error = enhance_resolution(filename, app.config['PROCESSED_FOLDER'])

        if error:
            return jsonify(error=error), 500

        return jsonify({'filename': os.path.basename(output_filename)})

    return jsonify(error="Invalid file format"), 400

@app.route('/download-file/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify(error="File not found"), 404

@app.route('/fetch-video-info', methods=['POST'])
def fetch_video_info():
    video_url = request.form.get('url')
    if not video_url:
        return jsonify(error="No URL provided"), 400

    try:
        ydl_opts = {'format': 'best'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            download_url = info_dict.get('url', None)
            title = info_dict.get('title', 'downloaded_video')
            return jsonify({'download_url': download_url, 'title': title})
    except Exception as e:
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(debug=True)
