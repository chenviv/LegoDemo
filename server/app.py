from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for Unity WebGL

# Store current rotation state
current_rotation = {
    'x': 0.0,
    'y': 0.0,
    'z': 0.0
}

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')

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

        return jsonify({
            'success': True,
            'rotation': current_rotation
        })
    except ValueError:
        return jsonify({'error': 'Invalid rotation values'}), 400

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
