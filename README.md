# Obsidian-Study-Agent

AI-powered Retrieval-Augmented Generation (RAG) agent that accesses and updates your Obsidian study notes, integrates internet search, and provides a FastAPI web interface for seamless interaction.

## Features

* **Personalized knowledge access:** Queries your Obsidian vault with advanced vector search.
* **Internet integration:** Fetches up-to-date info online to enrich responses.
* **Auto note-taking:** Writes and updates markdown notes autonomously.
* **FastAPI web app:** Easy-to-use chatbot interface for interaction.

## Tools

* **FAISS** to create a vector database.
* **gemini-1.5-flash** as the large language model.
* **SerpAPI** for internet search.
* **LangChain** to create the agent.
* **FastAPI** for web interface.
* **MongoDB** to store sessions.

## Installation

```bash
git clone https://github.com/yourusername/AgentRAG-Obsidian.git
cd Obsidian-Study-Agent
uv sync
```

## Usage

1. Configure your Obsidian vault path and API keys in the `configs/` folder.
2. Build the agent:

```bash
uv run python studying_assistant/building/build_agent.py
```

3. Start the FastAPI server:

```bash
uv run main.py
```

4. Open your browser and go to `http://localhost:8000` to chat with your AI assistant.


## Contributing

Feel free to open issues or submit pull requests!

## License

[MIT License](LICENSE)