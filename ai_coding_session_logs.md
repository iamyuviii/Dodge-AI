# AI Coding Session & Setup Logs

This document outlines the workflows, key prompts, tools, and debugging strategies used to build the **Context Graph — Business Intelligence Explorer**. 

## 1. Tools Used
- **Antigravity (Google Deepmind Assistant) & Cursor AI**: Used as the primary intelligent pair-programming environment. 
- **Workflows**: Used conversational prompting to bootstrap the `backend` FastAPI server and `frontend` React+Vite architecture, subsequently refining individual components like ReactFlow graph layouts and Groq LLaMA 3 integration.

---

## 2. Key Prompts and Initialization
Due to the sheer amount of code, the application was split into two primary domain prompts.

### Initial System Prompt (Backend & Database)
> "Build the backend for an interactive SAP O2C (Order-to-Cash) business intelligence system. 
> 1. Use FastAPI for the core server.
> 2. Include a `preprocess.py` script to generate a SQLite database (`business.db`) from relational data like orders, deliveries, invoices, and payments.
> 3. Use NetworkX to build a directed knowledge graph from this database, linking orders to their respective deliveries and invoices.
> 4. Endpoints should include `/api/graph` (full graph JSON) and `/api/chat` (natural language interface)."

### Initial System Prompt (Frontend & Visualization)
> "Create a React frontend using Vite. 
> 1. Use ReactFlow for mapping the JSON graph from the backend into a visual interactive graph.
> 2. Create a side-by-side layout: a massive graph canvas on the left, and a chat interface on the right.
> 3. Nodes must be styled distinctly based on their type (Orders, Payments, etc) with a floating `NodeInspector` panel to show metadata when a node is clicked."

### Integration Prompt (LLM & Chat)
> "Integrate the Groq API (LLaMA 3 70B) in `/api/chat`. The LLM needs context about the SAP O2C data so that users can ask deep business queries. Write a system prompt for the Groq client that provides it with the database schema and instructs it to act as a data-backed business insights tool."

### Conversational / Human-Like Iteration Prompts
> "Hey, the chat panel looks a bit squished on smaller screens. Can we make it a drawer that slides in from the right instead of taking up half the screen?"
> "The LLM keeps returning markdown formatting like \`\`\`sql inside the data stream, which breaks my Python execution. How do I parse that out safely with regex?"
> "Can we add styling to the ReactFlow nodes so that Orders are blue, Payments are green, and Invoices are red? Make them pop out a bit more with a drop shadow or hover effect."
> "I noticed that sometimes the AI tries to fetch the entire database if someone asks a broad question. We need it to limit the returned rows to 50 so it doesn't crash the server. Can you fix the Groq prompt rules?"

---

## 3. Iteration and Debugging Workflows

### Iteration 1: Graph Scalability & Layout Issues
- **Problem**: The initial graph load attempted to render thousands of nodes at once, causing the browser to freeze. Furthermore, a dependency for `dagre` layout was missing (`layout.js`), failing the initial render.
- **AI Debugging Workflow**: 
  - *Prompt*: "The frontend is crashing because `layout.js` is missing and rendering too many nodes is freezing the canvas. How can we optimize this?"
  - *Solution*: The AI helped implement a `get_initial_subgraph()` function in `main.py` to serve a performant 30-node initial view. We also decoupled the graph calculation from the view layer and introduced an `/api/graph/expand/{node_id}` endpoint so users can double-click nodes to dynamically load neighbors.

### Iteration 2: Redundant PDF/Data Processing Latency
- **Problem**: Early iterations featured significant latency when asking follow-up questions because the LLM route redundantly fetched underlying context files.
- **AI Debugging Workflow**:
  - *Prompt*: "We are experiencing severe latency in the `/api/chat` route. The terminal shows it parsing the full context on every request. Please optimize this."
  - *Solution*: Instructed the AI to implement a modular memory/cache mechanism so that preprocessing is done exactly once on startup, significantly boosting chat responsiveness.

### Iteration 3: Production Deployment
- **Problem**: Need to deploy the bipartite structure (FastAPI + React) seamlessly.
- **AI Debugging Workflow**:
  - *Prompt*: "Deploy this project to Render. Configure the frontend to point to the production backend URL."
  - *Solution*: We completely parameterized `main.jsx` with `axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL` and created a free-tier Render backend/frontend deployment.

### Iteration 4: LLM Guardrails & Prompt Formatting
- **Problem**: The Groq API occasionally generated conversational text before the SQL or attempted to fetch unstructured data, which caused the pipeline to fail or resulted in missing row caps.
- **AI Debugging Workflow**:
  - *Prompt*: "Fix the groq prompts and rules, because in some cases it is giving wrong answers. Like, we have restricted the limit to 50 but it ignores it. I have added some changes, look into them and check any other issues that can cause this."
  - *Solution*: Modified the `SQL_GEN_PROMPT` to strictly enforce `LIMIT 50` on non-aggregation queries. We also implemented robust regex extractions to strip markdown code blocks systematically before executing the query, and bounded the Python summarizer context window so the final AI answer works flawlessly.

---

## Summary
By leveraging AI tools, the development timeline was radically accelerated. The AI served not only as a boilerplate generator but as an architectural sounding board—helping modularize the backend graph cache, solving complex graph traversal algorithms, and implementing high-speed React Flow node-expansion features interactively.
