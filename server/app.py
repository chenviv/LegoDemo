from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import json
import queue
import threading

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for Unity WebGL
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store current rotation state
current_rotation = {
    'x': 0.0,
    'y': 0.0,
    'z': 0.0
}

# Store BLE connection status
ble_connection_status = {
    'connected': False,
    'device_name': None
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

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected')
    # Send current rotation and BLE status immediately upon connection
    emit('rotation_update', current_rotation)
    emit('ble_status', ble_connection_status)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')
    # If the disconnecting client was the one with BLE connection, update status
    # Check if this was the BLE client by seeing if it had sent BLE status
    # Reset BLE status and notify all remaining clients
    global ble_connection_status
    if ble_connection_status['connected']:
        print('BLE client disconnected - resetting BLE status')
        ble_connection_status['connected'] = False
        ble_connection_status['device_name'] = None
        socketio.emit('ble_status', ble_connection_status)

@socketio.on('ble_status')
def handle_ble_status(data):
    """Handle BLE connection status update from client"""
    try:
        ble_connection_status['connected'] = bool(data.get('connected', False))
        ble_connection_status['device_name'] = data.get('device_name')

        # Broadcast BLE status to all connected clients
        emit('ble_status', ble_connection_status, broadcast=True)
        print(f"BLE Status: {'Connected' if ble_connection_status['connected'] else 'Disconnected'}")

    except Exception as e:
        emit('error', {'message': f'Invalid BLE status: {str(e)}'})

@socketio.on('rotation_update')
def handle_rotation_update(data):
    """Handle rotation update from BLE client"""
    try:
        # Validate input
        if not all(key in data for key in ['x', 'y', 'z']):
            emit('error', {'message': 'Missing rotation parameters'})
            return

        current_rotation['x'] = float(data['x'])
        current_rotation['y'] = float(data['y'])
        current_rotation['z'] = float(data['z'])

        # Broadcast to all connected clients (including Unity WebGL)
        emit('rotation_update', current_rotation, broadcast=True)

    except (ValueError, TypeError) as e:
        emit('error', {'message': f'Invalid rotation values: {str(e)}'})

@socketio.on('update_timer_interval')
def handle_timer_interval_update(data):
    """Handle timer interval update request from UI"""
    try:
        interval = int(data.get('interval', 100))

        if interval < 10 or interval > 1000:
            emit('error', {'message': 'Timer interval must be between 10 and 1000 ms'})
            return

        # Forward to BLE client
        emit('update_timer_interval', {'interval': interval}, broadcast=True)
        print(f"Timer interval update request: {interval}ms")

    except (ValueError, TypeError) as e:
        emit('error', {'message': f'Invalid timer interval: {str(e)}'})

@app.route('/webgl/<path:path>')
def serve_webgl(path):
    """Serve WebGL files"""
    return send_from_directory('static/webgl', path)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
