from flask import Flask, request, send_file, redirect, url_for
import cv2
import os
import tempfile
import requests
from requests.exceptions import ChunkedEncodingError

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def enhance_resolution(input_file):
    # Load video
    cap = cv2.VideoCapture(input_file)

    # Get input video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Set output video resolution to 2K (2560x1440)
    new_width, new_height = 2560, 1440

    # Create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    output_file = tempfile.NamedTemporaryFile(suffix='.avi', delete=False)
    out = cv2.VideoWriter(output_file.name, fourcc, fps, (new_width, new_height))

    while(cap.isOpened()):
        ret, frame = cap.read()
        if ret == True:
            # Resize frame to 2K resolution
            resized_frame = cv2.resize(frame, (new_width, new_height))
            out.write(resized_frame)
        else:
            break

    # Release video capture and writer objects
    cap.release()
    out.release()

    return output_file.name

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

        # Send file to backend for processing with timeout
        files = {'file': open(filename, 'rb')}
        try:
            response = requests.post('http://localhost:5000/process', files=files, timeout=120)
            if response.status_code == 200:
                return redirect(url_for('download', filename=response.json()['filename']))
            else:
                return 'Error processing media', 500
        except ChunkedEncodingError as e:
            return f'Connection Error: {e}', 500

@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join(app.config['PROCESSED_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
