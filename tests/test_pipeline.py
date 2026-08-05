"""
Unit and integration tests for the AI Research Workspace.
Run with `pytest tests/`
"""

import pytest
from ingestion.base import NormalizedDocument
from ingestion.github_ingestor import GitHubIngestor
from knowledge_base.chunker import chunk_document
from retrieval.context_merger import ContextMerger


def test_github_python_ast_parsing():
    """Verify that Python AST extraction identifies functions, classes, and imports."""
    ingestor = GitHubIngestor()
    code_snippet = (
        "import os\n"
        "from math import sqrt\n\n"
        "class ResearchEngine:\n"
        "    def __init__(self, name):\n"
        "        self.name = name\n\n"
        "    def run_query(self):\n"
        "        return 'result'\n\n"
        "def helper_func():\n"
        "    return os.name\n"
    )
    
    ast_data = ingestor._parse_python_ast(code_snippet)
    
    assert "ResearchEngine" in ast_data["classes"]
    assert "run_query" in ast_data["functions"]
    assert "helper_func" in ast_data["functions"]
    assert "os" in ast_data["imports"]
    assert "math" in ast_data["imports"]


def test_github_js_ts_regex_parsing():
    """Verify that JS/TS regex extraction identifies classes, functions, and imports."""
    ingestor = GitHubIngestor()
    code_snippet = (
        "import { useState } from 'react';\n"
        "import axios from 'axios';\n\n"
        "class SearchDashboard extends Component {\n"
        "    render() {\n"
        "        return 'UI';\n"
        "    }\n"
        "}\n\n"
        "function calculateMetrics(a, b) {\n"
        "    return a + b;\n"
        "}\n\n"
        "const formatData = (data) => {\n"
        "    return data.trim();\n"
        "}\n"
    )
    
    ast_data = ingestor._parse_js_ts(code_snippet)
    
    assert "SearchDashboard" in ast_data["classes"]
    assert "calculateMetrics" in ast_data["functions"]
    assert "formatData" in ast_data["functions"]
    assert "react" in ast_data["imports"]
    assert "axios" in ast_data["imports"]


def test_semantic_chunking_boundaries():
    """Verify that chunking divides text and maintains metadata mapping."""
    doc = NormalizedDocument(
        source_id="mock_doc_id",
        source_type="pdf",
        title="Test PDF Document",
        text="Page one content. " * 50 + "\n\nPage two content. " * 50,
        sections=[
            {"type": "page", "id": 1, "page": 1, "text": "Page one content. " * 50},
            {"type": "page", "id": 2, "page": 2, "text": "Page two content. " * 50}
        ]
    )
    
    chunks = chunk_document(doc, chunk_size=100, overlap=10)
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.document_id == "mock_doc_id"
        assert chunk.source_type == "pdf"
        assert "page" in chunk.metadata
        assert chunk.metadata["page"] in [1, 2]
        assert len(chunk.text) > 0


def test_context_merger_lexical_ranking():
    """Verify that ContextMerger successfully deduplicates and ranks results by query overlap."""
    merger = ContextMerger()
    query = "SegFormer trained on ADE20K"
    
    # Mock search chunks
    # Chunks are class objects
    from knowledge_base.chunker import Chunk
    vector_results = [
        Chunk(
            chunk_id="chunk1",
            document_id="doc1",
            text="This document discusses SegFormer, a semantic segmentation model trained on the ADE20K dataset.",
            source_type="pdf",
            metadata={"title": "SegFormer Paper"}
        ),
        Chunk(
            chunk_id="chunk2",
            document_id="doc2",
            text="General information about neural networks and image classification on ImageNet.",
            source_type="pdf",
            metadata={"title": "NN Basics"}
        )
    ]
    
    # Mock web search hit
    web_results = [
        {
            "title": "SegFormer Info",
            "url": "http://segformer.com",
            "snippet": "SegFormer is a vision transformer framework trained on ADE20K."
        }
    ]
    
    merged = merger.merge(
        query=query,
        vector_results=vector_results,
        graph_results=[],
        web_results=web_results
    )
    
    assert len(merged.items) == 3  # Keeps all distinct sources
    # The SegFormer paper should rank first because of query term density
    assert "SegFormer" in merged.items[0]["text"]
    assert "ADE20K" in merged.items[0]["text"]
    assert merged.items[0]["score"] > merged.items[2]["score"]
