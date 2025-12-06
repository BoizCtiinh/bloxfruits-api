from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from threading import Lock

app = Flask(__name__)

# Lưu trữ data trong memory
data_storage = []
storage_lock = Lock()

# Thời gian lưu trữ (10 phút)
EXPIRY_TIME = timedelta(minutes=10)

# Danh sách các event hợp lệ
VALID_EVENTS = [
    "Rip Indra",
    "Soul Reaper", 
    "Dough King",
    "Mirage",
    "Elite Hunter",
    "Full Moon",
    "Near Moon",
    "Raid Castle"
]

def clean_expired_data():
    """Xóa data đã quá 10 phút"""
    current_time = datetime.now()
    with storage_lock:
        data_storage[:] = [
            item for item in data_storage 
            if current_time - item['timestamp'] < EXPIRY_TIME
        ]

@app.route('/', methods=['GET'])
def index():
    """Landing page"""
    return jsonify({
        'name': 'Blox Fruits Server Tracker API',
        'version': '1.0',
        'status': 'running',
        'endpoints': {
            'POST /api/data': 'Submit server event data',
            'GET /api/data/recent': 'Get recent events',
            'GET /api/events': 'List valid events',
            'GET /api/stats': 'Get statistics',
            'GET /api/health': 'Health check'
        }
    }), 200

@app.route('/api/data', methods=['POST'])
def post_data():
    """Endpoint để POST data lên server"""
    try:
        data = request.get_json()
        
        # Kiểm tra các trường bắt buộc
        required_fields = ['Players', 'jobid', 'name', 'place_id']
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields'
            }), 400
        
        # Validate event name
        event_name = data['name']
        if event_name not in VALID_EVENTS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid event. Valid events: {", ".join(VALID_EVENTS)}'
            }), 400
        
        # Kiểm tra trùng lặp
        with storage_lock:
            duplicate = any(
                item['jobid'] == data['jobid'] and 
                item['name'] == event_name
                for item in data_storage
            )
        
        if duplicate:
            return jsonify({
                'status': 'info',
                'message': 'Event already exists'
            }), 200
        
        # Lưu data
        data_entry = {
            'Players': data['Players'],
            'jobid': data['jobid'],
            'name': event_name,
            'place_id': data['place_id'],
            'timestamp': datetime.now()
        }
        
        with storage_lock:
            data_storage.append(data_entry)
        
        clean_expired_data()
        
        return jsonify({
            'status': 'success',
            'message': f'Event "{event_name}" saved'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/data/recent', methods=['GET'])
def get_recent_data():
    """Endpoint để GET data"""
    try:
        clean_expired_data()
        
        name = request.args.get('name')
        limit = request.args.get('limit', default=100, type=int)
        
        if limit > 500:
            limit = 500
        
        with storage_lock:
            if name:
                filtered_data = [
                    item for item in data_storage 
                    if item['name'] == name
                ]
            else:
                filtered_data = data_storage.copy()
            
            filtered_data.sort(key=lambda x: x['timestamp'], reverse=True)
            result_data = filtered_data[:limit]
            
            response_data = [
                {
                    'Players': item['Players'],
                    'jobid': item['jobid'],
                    'name': item['name'],
                    'place_id': item['place_id'],
                    'created_at': item['timestamp'].isoformat(),
                    'expires_in': int((item['timestamp'] + EXPIRY_TIME - datetime.now()).total_seconds())
                }
                for item in result_data
            ]
        
        return jsonify({
            'status': 'success',
            'event': name if name else 'all',
            'count': len(response_data),
            'data': response_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/events', methods=['GET'])
def get_valid_events():
    """Danh sách events hợp lệ"""
    return jsonify({
        'status': 'success',
        'events': VALID_EVENTS,
        'endpoints': {
            event: f'/api/data/recent?name={event.replace(" ", "%20")}&limit=100'
            for event in VALID_EVENTS
        }
    }), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Thống kê"""
    try:
        clean_expired_data()
        
        with storage_lock:
            event_counts = {}
            for item in data_storage:
                event_name = item['name']
                if event_name not in event_counts:
                    event_counts[event_name] = 0
                event_counts[event_name] += 1
            
            total_servers = len(data_storage)
        
        return jsonify({
            'status': 'success',
            'total_servers': total_servers,
            'event_counts': event_counts,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    clean_expired_data()
    
    with storage_lock:
        active_servers = len(data_storage)
    
    return jsonify({
        'status': 'healthy',
        'active_servers': active_servers,
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)