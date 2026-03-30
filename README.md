# Context Graph — Business Intelligence Explorer

An interactive knowledge graph and business intelligence system with a natural-language query interface powered by Groq and LLaMA 3. 

## 📖 What it does

Context Graph allows users to upload structured business data (like CSV or Excel files) and automatically transforms it into a rich, interactive network graph. It enables users to:
- **Visually Explore Data**: Navigate complex relationships between business entities (e.g., customers, products, orders, regions) through an intuitive node-and-edge visualization.
- **Natural Language Queries**: Instead of writing complex SQL queries, users can ask questions in plain English (e.g., "Show me top customers in Europe" or "What are the most popular products?"). The system translates these questions into structured insights using Groq's low-latency LLaMA 3 API.
- **Dynamic Context**: Clicking on specific nodes reveals detailed metadata and highlights related connections in real-time, allowing users to drill down into specifics.

## 🛠️ How it does it

The application is built with a modern, decoupled architecture:
1. **Frontend (React & ReactFlow)**: Provides the user interface, rendering a dynamic, interactive canvas for the knowledge graph. It handles user interactions, node expansion, and the chat interface seamlessly.
2. **Backend (Python & FastAPI)**: Serves as the robust API layer. It orchestrates communication between the frontend, the database, and the LLM securely and efficiently.
3. **Data Pipeline (SQLite & NetworkX)**: Uploaded datasets are parsed, structured, and stored in a fast local SQLite database. NetworkX is used in the backend to model graphs, calculate relations, and serve graph payload components to the frontend.
4. **AI Engine (Groq & LLaMA 3)**: Serves as the intelligent semantic layer. The backend communicates with Groq to validate, parse, and intelligently translate natural language into actionable intents and SQL queries.

## 📋 Prerequisites

Before running the project locally, ensure you have the following installed on your system:
- **Python 3.8+**: Required for building and running the FastAPI backend.
- **Node.js (v16+) & npm**: Required for running the Vite-based React frontend.
- **Groq API Key**: A free API key from the [Groq Console](https://console.groq.com) is needed to power the natural language capabilities.

## 🚀 Quick Start

### 1. Set up Environment Variables
Create or edit the `.env` file in the root of the project to add your Groq API key:
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

### 2. (Optional) Provide Your Dataset
Place your Excel or CSV data file into the `data/` directory. The backend pipeline automatically detects and processes it. If no file is provided, the system will automatically seed rich demonstration data so you can try it out immediately.

### 3. Start the Backend (Terminal 1)
You can start the backend using the provided PowerShell script:
```powershell
.\start-backend.ps1
```
> **Manual Approach**: 
> ```powershell
> cd backend
> pip install -r requirements.txt  # If not installed already
> python preprocess.py             # Processes data and seeds SQLite DB
> uvicorn main:app --reload --port 8000
> ```

### 4. Start the Frontend (Terminal 2)
In a new terminal window, launch the frontend UI:
```powershell
.\start-frontend.ps1
```
> **Manual Approach**: 
> ```powershell
> cd frontend
> npm install
> npm run dev
> ```

### 5. Access the Interface
Open your web browser and navigate to: **[http://localhost:5173](http://localhost:5173)**

---

## 📂 Project Structure

```text
.
├── backend/
│   ├── main.py          # FastAPI server and endpoints
│   ├── preprocess.py    # Dataset extraction to SQLite
│   ├── graph_builder.py # NetworkX graph generation
│   ├── groq_client.py   # LLM integration and guardrails
│   └── requirements.txt # Python dependencies
├── frontend/
│   └── src/
│       ├── App.jsx            # Main React component
│       ├── GraphCanvas.jsx    # ReactFlow implementation
│       ├── ChatPanel.jsx      # Natural language query interface
│       ├── CustomNode.jsx     # Node rendering component
│       ├── NodeInspector.jsx  # Context panel for metrics
│       └── index.css          # Styling
├── data/                # Put dataset (.csv/.xlsx) here
├── .env                 # Environment variables (GROQ_API_KEY)
└── README.md            # Project documentation
```

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server health status and graph statistics |
| GET | `/api/graph` | Fetch full initial graph structure (nodes & edges) |
| GET | `/api/graph/expand/{id}` | Expand a specific node to see its immediate neighbours |
| GET | `/api/graph/node/{id}` | View detailed metadata for a single node |
| POST | `/api/chat` | Submit a natural-language query to guide graph visualization |

## 🏗️ Tech Stack

- **Backend Architecture**: Python · FastAPI · SQLite
- **Graph Engine Processing**: NetworkX
- **Frontend Interface**: React · Vite · ReactFlow · Axios
- **AI Intelligence Layer**: LLaMA 3 (70B) via Groq API
