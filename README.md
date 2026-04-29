# 🐄 BreedScan — Cattle Breed AI Predictor

A full-stack web app that predicts cattle breeds from images using your fine-tuned MobileNetV2 model.

---

## 📁 Project Structure

```
cattle_app/
├── app.py                  ← Flask backend (API + model inference)
├── model.keras             ← ⚠️ Place your model file here!
├── requirements.txt
├── users.json              ← Auto-created: user accounts
├── history.json            ← Auto-created: prediction history
├── templates/
│   └── index.html          ← Full frontend (single page app)
└── static/
    ├── uploads/            ← Uploaded images for prediction
    └── retrain/            ← Copies of images saved for retraining
```

---

## 🚀 Setup & Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Place the model file

Copy your `best_finetuned__1_.keras` to this folder and rename it:
```bash
cp /path/to/best_finetuned__1_.keras ./model.keras
```

### 3. Run the app

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 🔑 Features

| Feature | Guest | Registered User |
|---------|-------|-----------------|
| Upload & predict breed | ✅ | ✅ |
| View breed info | ✅ | ✅ |
| Compare breeds | ✅ | ✅ |
| Save prediction history | ❌ | ✅ |
| View past predictions | ❌ | ✅ |

---

## 🐮 Supported Breeds

1. **Ayrshire** — Scotland origin, 5,000–7,000 L/year
2. **Brown Swiss** — Swiss Alps origin, 6,000–9,000 L/year
3. **Gir** — Gujarat, India origin, 1,200–3,500 L/year
4. **Hariana** — Haryana, India origin, 900–2,500 L/year
5. **Holstein Friesian** — Netherlands origin, 7,000–12,000 L/year

---

## 🔁 Retraining

Every image uploaded by any user (guest or registered) is automatically saved to `static/retrain/`. You can use these images to further train your model:

```python
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Load existing model
model = tf.keras.models.load_model('model.keras')

# Set up data generator on retrain folder
# (manually label images into subfolders first)
datagen = ImageDataGenerator(preprocessing_function=tf.keras.applications.mobilenet_v2.preprocess_input)
...
```

---

## 🔒 Security Notes

- Passwords are SHA-256 hashed before storage
- Session-based authentication with Flask sessions
- For production, use a proper database (PostgreSQL) and HTTPS
