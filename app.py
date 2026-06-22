import os
import uuid
import base64
import json
import io
import traceback
from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image
from generator import GeneratorPipeline
from editor import EditingPipeline

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(__file__), 'output')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

gen_pipeline = GeneratorPipeline()
edit_pipeline = EditingPipeline()

sessions = {}


def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {
            'current_image': None,
            'pipeline': EditingPipeline()
        }
    return sessions[session_id]


def pil_to_base64(img, fmt='PNG'):
    buf = io.BytesIO()
    if img.mode == 'RGBA':
        img.save(buf, format='PNG')
    else:
        img = img.convert('RGB')
        if fmt.upper() == 'JPEG':
            img.save(buf, format='JPEG', quality=95)
        else:
            img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def base64_to_pil(data):
    if ',' in data:
        data = data.split(',')[1]
    buf = io.BytesIO(base64.b64decode(data))
    return Image.open(buf)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        params = request.json
        img = gen_pipeline.generate(params)
        b64 = pil_to_base64(img, 'PNG')

        session_id = str(uuid.uuid4())
        session = get_session(session_id)
        session['current_image'] = img.copy()
        session['pipeline'].load_image(img.copy())

        return jsonify({
            'success': True,
            'image': b64,
            'session_id': session_id,
            'width': img.width,
            'height': img.height
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/upload', methods=['POST'])
def upload():
    try:
        if 'image' in request.files:
            file = request.files['image']
            img = Image.open(file.stream)
        elif 'image' in request.form:
            data = request.form['image']
            img = base64_to_pil(data)
        else:
            return jsonify({'success': False, 'error': 'No image provided'})

        session_id = str(uuid.uuid4())
        session = get_session(session_id)
        session['current_image'] = img.copy()
        session['pipeline'].load_image(img.copy())

        return jsonify({
            'success': True,
            'image': pil_to_base64(img, 'PNG'),
            'session_id': session_id,
            'width': img.width,
            'height': img.height
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/edit', methods=['POST'])
def edit():
    try:
        data = request.json
        session_id = data.get('session_id')
        operations = data.get('operations', [])

        if not session_id:
            return jsonify({'success': False, 'error': 'No session'})

        session = get_session(session_id)
        if session['current_image'] is None:
            return jsonify({'success': False, 'error': 'No image loaded'})

        pipeline = session['pipeline']

        for op in operations:
            op_type = op.get('type')
            params = op.get('params', {})
            pipeline.apply(op_type, params)

        img = pipeline.get_current_image()
        session['current_image'] = img

        return jsonify({
            'success': True,
            'image': pil_to_base64(img, 'PNG'),
            'width': img.width,
            'height': img.height,
            'can_undo': pipeline.can_undo(),
            'can_redo': pipeline.can_redo()
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/undo', methods=['POST'])
def undo():
    try:
        data = request.json
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'No session'})

        session = get_session(session_id)
        pipeline = session['pipeline']
        img = pipeline.undo()
        session['current_image'] = img

        return jsonify({
            'success': True,
            'image': pil_to_base64(img, 'PNG') if img else None,
            'can_undo': pipeline.can_undo(),
            'can_redo': pipeline.can_redo()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/redo', methods=['POST'])
def redo():
    try:
        data = request.json
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'No session'})

        session = get_session(session_id)
        pipeline = session['pipeline']
        img = pipeline.redo()
        session['current_image'] = img

        return jsonify({
            'success': True,
            'image': pil_to_base64(img, 'PNG') if img else None,
            'can_undo': pipeline.can_undo(),
            'can_redo': pipeline.can_redo()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/reset', methods=['POST'])
def reset():
    try:
        data = request.json
        session_id = data.get('session_id')
        if session_id and session_id in sessions:
            session = sessions[session_id]
            if session['current_image']:
                session['pipeline'].reset()
                session['current_image'] = None
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/download', methods=['POST'])
def download():
    try:
        data = request.json
        session_id = data.get('session_id')
        fmt = data.get('format', 'PNG')

        if session_id and session_id in sessions:
            session = sessions[session_id]
            img = session['current_image']
            if img:
                buf = io.BytesIO()
                if fmt.upper() == 'JPEG' or fmt.upper() == 'JPG':
                    img = img.convert('RGB')
                    img.save(buf, format='JPEG', quality=95)
                else:
                    if img.mode == 'RGBA':
                        img.save(buf, format='PNG')
                    else:
                        img.save(buf, format='PNG')
                buf.seek(0)
                return send_file(
                    buf,
                    mimetype=f'image/{fmt.lower()}',
                    as_attachment=True,
                    download_name=f'image_genius.{fmt.lower()}'
                )

        return jsonify({'success': False, 'error': 'No image'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/info', methods=['POST'])
def info():
    try:
        data = request.json
        session_id = data.get('session_id')
        if session_id and session_id in sessions:
            session = sessions[session_id]
            img = session['current_image']
            if img:
                return jsonify({
                    'success': True,
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format or 'PNG',
                    'can_undo': session['pipeline'].can_undo(),
                    'can_redo': session['pipeline'].can_redo()
                })
        return jsonify({'success': False, 'error': 'No image'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/canvas_resize', methods=['POST'])
def canvas_resize():
    try:
        data = request.json
        session_id = data.get('session_id')
        width = int(data.get('width', 1920))
        height = int(data.get('height', 1080))
        bg_color = data.get('bg_color', '#000000')

        if isinstance(bg_color, str):
            bg_color = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5))

        session = get_session(session_id)
        pipeline = session['pipeline']
        if pipeline.get_current_image() is None:
            img = Image.new('RGB', (width, height), bg_color)
            pipeline.load_image(img)
            session['current_image'] = img
        else:
            img = pipeline.resize_canvas(width, height, bg_color)
            session['current_image'] = img

        return jsonify({
            'success': True,
            'image': pil_to_base64(img, 'PNG') if img else None,
            'width': img.width if img else width,
            'height': img.height if img else height
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print("*" * 60)
    print("  IMAGE GENIUS - Advanced Image Generator & Editor")
    print("*" * 60)
    print(f"  Server: http://127.0.0.1:5000")
    print("  Press Ctrl+C to stop")
    print("*" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
