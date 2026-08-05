"""
Defines the State structure for the LangGraph orchestrator pipeline.
"""

from typing import TypedDict, Annotated, Sequence, Any
import operator


class PipelineState(TypedDict):
    # Inputs
    query: str
    workspace_id: str
    project_id: str | None
    
    # Context & Memories
    conversation_history: list[dict[str, Any]]
    workspace_facts: list[str]
    
    # Planner & Routing Decisions
    plan: dict[str, Any]  # {"use_vector": bool, "use_graph": bool, "use_web": bool, "vector_query": str, "graph_query": str, "web_query": str}
    selected_agent: str   # "github" | "paper" | "code" | "report" | "qa"
    
    # State tracking
    retrieved_chunks: list[dict[str, Any]]
    missing_info: str | None
    loop_count: int
    
    # Generation steps outputs
    draft_answer: str
    citation_check: dict[str, Any]  # {"verified_answer": str, "flagged_claims": list[str]}
    final_answer: str
    
    # RAG Evaluation
    eval_metrics: dict[str, Any]  # {"faithfulness": float, "relevance": float, "recall": float, "latency": float}
