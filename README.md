# Context Graph — Business Intelligence Explorer

An interactive knowledge graph system with a natural-language query interface powered by Groq LLaMA 3.

## Quick Start

### 1. Add your Groq API key
Edit `.env` in the project root:
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```
Get a free key at https://console.groq.com

### 2. (Optional) Add your dataset
Place your Excel/CSV file into `data/`. The system auto-detects it.
Without a file it seeds rich demo data automatically.

### 3. Start the backend (Terminal 1)
```powershell
.\start-backend.ps1
```
Or manually:
```powershell
cd backend
python preprocess.py   # seeds DB
uvicorn main:app --reload --port 8000
```

### 4. Start the frontend (Terminal 2)
```powershell
.\start-frontend.ps1
```
Or manually:
```powershell
cd frontend
npm run dev
```

### 5. Open the app
http://localhost:5173

---

## Project Structure
```
.
├── backend/
│   ├── main.py          # FastAPI server
│   ├── preprocess.py    # Dataset → SQLite
│   ├── graph_builder.py # NetworkX graph
│   ├── groq_client.py   # LLM + guardrails
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── GraphCanvas.jsx
│       ├── ChatPanel.jsx
│       ├── CustomNode.jsx
│       ├── NodeInspector.jsx
│       └── index.css
├── data/                # Put dataset here
├── .env                 # GROQ_API_KEY
└── README.md
```

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server health + graph stats |
| GET | `/api/graph` | Full graph JSON |
| GET | `/api/graph/expand/{id}` | Expand a node's neighbours |
| GET | `/api/graph/node/{id}` | Single node metadata |
| POST | `/api/chat` | Natural-language query |

## Tech Stack
- **Backend**: Python · FastAPI · SQLite · NetworkX · Groq SDK
- **Frontend**: React · Vite · ReactFlow · Axios
- **LLM**: LLaMA 3 70B via Groq (free tier)
