from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import os
import json
import queue
import threading

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for Unity WebGL

# Store current rotation state
current_rotation = {
    'x': 0.0,
    'y': 0.0,
    'z': 0.0
}

# SSE subscribers
rotation_subscribers = []
rotation_lock = threading.Lock()

def _broadcast_rotation(rotation):
    payload = f"data: {json.dumps(rotation)}\n\n"
    with rotation_lock:
        dead = []
        for q in rotation_subscribers:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            rotation_subscribers.remove(q)

@app.route('/')
def index():
    """Serve the main HTML page"""
    response = send_from_directory('static', 'index.html')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/rotation', methods=['GET'])
def get_rotation():
    """Get current rotation angles"""
    return jsonify(current_rotation)

@app.route('/api/rotation', methods=['POST'])
def set_rotation():
    """Update rotation angles"""
    data = request.json

    # Validate input
    if not all(key in data for key in ['x', 'y', 'z']):
        return jsonify({'error': 'Missing rotation parameters'}), 400

    try:
        current_rotation['x'] = float(data['x'])
        current_rotation['y'] = float(data['y'])
        current_rotation['z'] = float(data['z'])

        _broadcast_rotation(current_rotation)

        return jsonify({
            'success': True,
            'rotation': current_rotation
        })
    except ValueError:
        return jsonify({'error': 'Invalid rotation values'}), 400

@app.route('/api/rotation/stream', methods=['GET'])
def rotation_stream():
    """Stream rotation updates via Server-Sent Events"""
    q = queue.Queue(maxsize=100)
    with rotation_lock:
        rotation_subscribers.append(q)

    def event_stream():
        try:
            # Send current rotation immediately
            yield f"data: {json.dumps(current_rotation)}\n\n"
            while True:
                msg = q.get()
                yield msg
        except GeneratorExit:
            pass
        finally:
            with rotation_lock:
                if q in rotation_subscribers:
                    rotation_subscribers.remove(q)

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/webgl/<path:path>')
def serve_webgl(path):
    """Serve WebGL files"""
    return send_from_directory('static/webgl', path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
