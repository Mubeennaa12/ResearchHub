# Agentic Research Platform

High-level scaffold matching the architecture:

User Query -> Planner Agent -> [Vector Search | Graph Search | Web Search] ->
Context Merger -> Reasoning Agent -> (loop | Answer Generator -> Citation
Checker -> Final Answer)

## Layout

```
research_platform/
├── main.py                  # Entry point / CLI or server bootstrap
├── config.py                 # API keys, model names, thresholds
├── ingestion/                 # Turns raw sources into normalized documents
│   ├── base.py                # Ingestor interface
│   ├── pdf_ingestor.py
│   ├── github_ingestor.py
│   ├── youtube_ingestor.py
│   ├── web_ingestor.py
│   └── paper_ingestor.py      # arXiv / research paper specific handling
├── knowledge_base/            # Storage layer
│   ├── chunker.py              # Splits normalized docs into chunks
│   ├── vector_store.py         # Embedding index (e.g. Chroma/Pinecone/FAISS)
│   └── graph_store.py          # Entity/relationship graph (e.g. Neo4j)
├── retrieval/                 # The three parallel search branches + merge
│   ├── vector_search.py
│   ├── graph_search.py
│   ├── web_search.py
│   └── context_merger.py
├── agents/                    # The four agents in the diagram
│   ├── base_agent.py
│   ├── planner.py
│   ├── reasoning.py
│   ├── answer_generator.py
│   └── citation_checker.py
├── orchestrator/
│   └── pipeline.py             # Wires everything together, owns the retrieval loop
├── api/
│   └── routes.py                # FastAPI endpoints
└── tests/
    └── test_pipeline.py
```

## How to fill this in

Every file below has function/class signatures, docstrings, and `TODO`
comments instead of full implementations. Suggested build order:

1. `ingestion/` + `knowledge_base/` — get documents in and chunked/stored.
2. `retrieval/vector_search.py` and `context_merger.py` — get a single
   retrieval path working end to end before adding graph/web.
3. `agents/reasoning.py` + `agents/answer_generator.py` — basic Q&A loop.
4. `agents/planner.py` — add branching logic once you know what queries look like.
5. `agents/citation_checker.py` — bolt on verification last.
6. `orchestrator/pipeline.py` + `api/routes.py` — expose it.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
python main.py
```
