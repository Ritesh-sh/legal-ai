Here’s a properly formatted `README.md` you can use for your project. It includes setup instructions, installation commands, how to run each component, and ends with a section providing the model source from Google Drive.

---

```markdown
# Legal AI Platform

This project is a full-stack AI-powered legal assistant platform consisting of:

- 🧠 **legal-ai-service** — Backend AI services (embedding, summarization, indexing)
- 🌐 **legal-frontend** — React-based web frontend for user interaction
- 🔧 **legal-backend** — Node.js/Express backend (API & Auth)
- 🧪 Other utilities in `a/` and `m/` directories

---

## 📦 Project Structure

```

├── legal-ai-service      # Python-based AI service
├── legal-backend         # Node.js Express backend
├── legal-frontend        # React frontend
├── a/, m/                # Utility modules / scripts

````

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Ritesh-sh/legal-ai.git
cd legal-ai-platform
````

---

## 🧠 legal-ai-service (Python Backend)

### 🔧 Installation

```bash
cd legal-ai-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 🚀 Run Service

```bash
python main.py
```

---

## 🖥️ legal-backend (Node.js Backend)

### 🔧 Installation

```bash
cd legal-backend
npm install
```

### ⚙️ Environment Setup

Create a `.env` file in `legal-backend/`:

```env
PORT=5000
JWT_SECRET=your_secret_key
```

### 🚀 Run Server

```bash
npm start
```

---

## 🌐 legal-frontend (React App)

### 🔧 Installation

```bash
cd legal-frontend
npm install
```

### 🚀 Run Frontend

```bash
npm start
```

---

## 💾 Model Files

To use the pretrained models, download them from the links below and place them in the correct directories:

* 🔗 **Model Source (Google Drive)**: [Download Models](https://drive.google.com/drive/folders/1N8g-YxJkMSTilm0OZvRzlzwQTYpWW4OH?usp=sharing)
* Place the `legal_embedding_model` and `legal_summarizer` folders inside:

```
legal-ai-service/models/
```

---

## 📬 Contact

For issues or collaboration, please contact \[[your-email@example.com](mailto:your-email@example.com)].

---

## 📝 License

MIT License © 2025 Your Name

```

---

Would you like me to include badges (build status, license, etc.) or a sample `.env` file too?
```
