from flask import Flask, request, send_file, redirect, url_for, jsonify
import cv2
import os
import tempfile
import requests
from requests.exceptions import ChunkedEncodingError

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
    # Check if file is uploaded
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']

    # Check if file is allowed
    if file and allowed_file(file.filename):
        # Save uploaded file
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        # Enhance video resolution
        output_filename, error = enhance_resolution(filename, app.config['PROCESSED_FOLDER'])

        if error:
            return error, 500

        return jsonify({'filename': os.path.basename(output_filename)})

    return 'Invalid file format', 400

@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join(app.config['PROCESSED_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
