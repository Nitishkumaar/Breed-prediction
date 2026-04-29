from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os, json, uuid, hashlib, shutil, sqlite3
from datetime import datetime
from PIL import Image

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'cattle-breed-secret-key-2024'
CORS(app, supports_credentials=True)

UPLOAD_FOLDER  = 'static/uploads'
RETRAIN_FOLDER = 'static/retrain'
MODEL_PATH     = 'model.keras'
DB_PATH        = 'database.db'

os.makedirs(UPLOAD_FOLDER,  exist_ok=True)
os.makedirs(RETRAIN_FOLDER, exist_ok=True)

CLASSES = ['Ayrshire', 'Brown_Swiss', 'Gir', 'Hariana', 'Holstein_Friesian']

BREED_INFO = {
    'Ayrshire': {
        'origin': 'Ayrshire County, Scotland',
        'milk_yield': '5,000-7,000 litres/year',
        'climate': 'Cool temperate; thrives in 10-20C',
        'food': 'Pasture grass, silage, hay, mineral supplements',
        'color': '#D4A017',
        'description': 'A hardy dairy breed known for efficient milk production and strong adaptability.',
        'fat_content': '3.9%', 'protein': '3.3%', 'lifespan': '12-15 years', 'weight': '450-550 kg'
    },
    'Brown_Swiss': {
        'origin': 'Alps of Switzerland',
        'milk_yield': '6,000-9,000 litres/year',
        'climate': 'Mountainous & temperate; 5-22C',
        'food': 'Alpine grasses, hay, grain concentrates',
        'color': '#8B6914',
        'description': 'One of the oldest dairy breeds, prized for high-protein milk ideal for cheese.',
        'fat_content': '4.0%', 'protein': '3.5%', 'lifespan': '15-20 years', 'weight': '550-700 kg'
    },
    'Gir': {
        'origin': 'Gir Forest, Gujarat, India',
        'milk_yield': '1,200-3,500 litres/year',
        'climate': 'Tropical & arid; 25-45C',
        'food': 'Dry fodder, agricultural byproducts, shrubs',
        'color': '#C65D00',
        'description': 'A premier Indian zebu breed known for disease resistance and heat tolerance.',
        'fat_content': '4.5%', 'protein': '3.8%', 'lifespan': '12-14 years', 'weight': '350-450 kg'
    },
    'Hariana': {
        'origin': 'Haryana & western UP, India',
        'milk_yield': '900-2,500 litres/year',
        'climate': 'Semi-arid; 20-42C',
        'food': 'Wheat straw, mustard cake, green fodder',
        'color': '#5B8A3C',
        'description': 'A dual-purpose Indian breed used for both milk and draught work.',
        'fat_content': '4.2%', 'protein': '3.6%', 'lifespan': '12-15 years', 'weight': '300-400 kg'
    },
    'Holstein_Friesian': {
        'origin': 'North Holland & Friesland, Netherlands',
        'milk_yield': '7,000-12,000 litres/year',
        'climate': 'Temperate; optimal 10-18C',
        'food': 'High-energy silage, corn, protein supplements',
        'color': '#2C5F8A',
        'description': "The world's highest milk-producing breed, recognizable by its black & white markings.",
        'fat_content': '3.7%', 'protein': '3.2%', 'lifespan': '10-15 years', 'weight': '580-700 kg'
    }
}

# ─── DATABASE SETUP ──────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                username  TEXT UNIQUE NOT NULL,
                password  TEXT NOT NULL,
                email     TEXT DEFAULT '',
                created   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
                breed         TEXT NOT NULL,
                confidence    REAL NOT NULL,
                probabilities TEXT NOT NULL,
                image_url     TEXT NOT NULL,
                filename      TEXT NOT NULL,
                timestamp     TEXT NOT NULL
            );
        ''')
    print("SQLite database ready ->", DB_PATH)

init_db()

# ─── MODEL ───────────────────────────────────────────────────────────────────

model = None

def load_model():
    global model
    if os.path.exists(MODEL_PATH):
        try:
            import tensorflow as tf
            model = tf.keras.models.load_model(MODEL_PATH)
            print("Model loaded successfully")
        except Exception as e:
            print(f"Could not load model: {e}")

load_model()

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def predict_breed(img_path):
    if model is None:
        import random
        idx = random.randint(0, 4)
        probs = [round(random.uniform(0.01, 0.1), 3) for _ in range(5)]
        probs[idx] = round(1.0 - sum(probs) + probs[idx], 3)
        return CLASSES[idx], {CLASSES[i]: round(probs[i] * 100, 1) for i in range(5)}
    import numpy as np, tensorflow as tf
    img = Image.open(img_path).convert('RGB').resize((224, 224))
    arr = tf.keras.applications.mobilenet_v2.preprocess_input(
              np.expand_dims(np.array(img, dtype=np.float32), 0))
    preds = model.predict(arr, verbose=0)[0]
    idx = int(np.argmax(preds))
    return CLASSES[idx], {CLASSES[i]: round(float(preds[i]) * 100, 1) for i in range(5)}

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def register():
    data     = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email    = data.get('email', '').strip()
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    try:
        with get_db() as conn:
            conn.execute(
                'INSERT INTO users (username, password, email, created) VALUES (?,?,?,?)',
                (username, hash_password(password), email, datetime.now().isoformat())
            )
            row = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
            session['user']    = username
            session['user_id'] = row['id']
        return jsonify({'message': 'Registered', 'username': username})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data     = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM users WHERE username=? AND password=?',
            (username, hash_password(password))
        ).fetchone()
    if not row:
        return jsonify({'error': 'Invalid credentials'}), 401
    session['user']    = username
    session['user_id'] = row['id']
    return jsonify({'message': 'Logged in', 'username': username})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/me')
def me():
    user = session.get('user')
    return jsonify({'username': user, 'logged_in': bool(user)})

# ─── PREDICTION ──────────────────────────────────────────────────────────────

@app.route('/api/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file      = request.files['image']
    filename  = f"{uuid.uuid4().hex}_{file.filename}"
    filepath  = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    shutil.copy(filepath, os.path.join(RETRAIN_FOLDER, filename))

    breed, probabilities = predict_breed(filepath)
    info      = BREED_INFO[breed]
    timestamp = datetime.now().isoformat()
    image_url = f'/static/uploads/{filename}'

    user_id = session.get('user_id')
    if user_id:
        with get_db() as conn:
            conn.execute(
                '''INSERT INTO predictions
                   (user_id, breed, confidence, probabilities, image_url, filename, timestamp)
                   VALUES (?,?,?,?,?,?,?)''',
                (user_id, breed, probabilities[breed],
                 json.dumps(probabilities), image_url, filename, timestamp)
            )

    return jsonify({
        'breed':         breed,
        'confidence':    probabilities[breed],
        'probabilities': probabilities,
        'info':          info,
        'image_url':     image_url,
        'timestamp':     timestamp
    })

# ─── HISTORY ─────────────────────────────────────────────────────────────────

@app.route('/api/history')
def get_history():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT 50',
            (user_id,)
        ).fetchall()
    return jsonify([{
        'id':            r['id'],
        'breed':         r['breed'],
        'confidence':    r['confidence'],
        'probabilities': json.loads(r['probabilities']),
        'image_url':     r['image_url'],
        'timestamp':     r['timestamp']
    } for r in rows])

@app.route('/api/history/<int:pred_id>', methods=['DELETE'])
def delete_history(pred_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    with get_db() as conn:
        conn.execute('DELETE FROM predictions WHERE id=? AND user_id=?', (pred_id, user_id))
    return jsonify({'message': 'Deleted'})

# ─── BREED INFO & COMPARE ────────────────────────────────────────────────────

@app.route('/api/breeds')
def get_breeds():
    return jsonify(BREED_INFO)

@app.route('/api/compare', methods=['POST'])
def compare():
    breeds = request.json.get('breeds', [])
    return jsonify({b: BREED_INFO[b] for b in breeds if b in BREED_INFO})

# ─── MODEL STATUS ────────────────────────────────────────────────────────────

@app.route('/api/model-status')
def model_status():
    return jsonify({
        'loaded':          model is not None,
        'classes':         CLASSES,
        'retrain_samples': len(os.listdir(RETRAIN_FOLDER))
    })

# ─── SERVE FRONTEND ──────────────────────────────────────────────────────────

@app.route('/')
@app.route('/<path:path>')
def index(path=''):
    return send_from_directory('templates', 'index.html')

if __name__ == '__main__':
    print("Cattle Breed Predictor starting...")
    print(f"  Model  : {'Loaded' if model else 'Demo mode (place model.keras here)'}")
    print(f"  DB     : {DB_PATH}")
    app.run(debug=True, port=5000)
