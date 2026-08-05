"""
FastAPI application routes and endpoint handlers.
"""

import os
import time
import shutil
import tempfile
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from api.database import init_db, get_db
from api.models import (
    Workspace, WorkspaceFact, Collection, Folder, Document,
    Project, ChatSession, ChatMessage, Task, PersonalNote
)

# Ingestors & Storage Imports
from ingestion.pdf_ingestor import PDFIngestor
from ingestion.github_ingestor import GitHubIngestor
from ingestion.youtube_ingestor import YouTubeIngestor
from ingestion.web_ingestor import WebIngestor
from ingestion.paper_ingestor import PaperIngestor
from knowledge_base.chunker import chunk_document
from knowledge_base.vector_store import VectorStore
from knowledge_base.graph_store import GraphStore

# Retrieval & Agents Imports
from retrieval.vector_search import VectorSearchAgent
from retrieval.graph_search import GraphSearchAgent
from retrieval.web_search import WebSearchAgent
from retrieval.context_merger import ContextMerger
from agents.planner import PlannerAgent
from agents.reasoning import ReasoningAgent
from agents.answer_generator import AnswerGeneratorAgent
from agents.citation_checker import CitationCheckerAgent
from orchestrator.evaluator import QualityEvaluator
from orchestrator.pipeline import Pipeline

app = FastAPI(title="AI Research Workspace (Agentic RAG)")

# Enable CORS for Next.js frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_db()


# Initialize global helper instances lazily
_pipeline_instance = None
_vector_store_instance = None
_graph_store_instance = None


def get_vector_store() -> VectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance


def get_graph_store() -> GraphStore:
    global _graph_store_instance
    if _graph_store_instance is None:
        _graph_store_instance = GraphStore(
            uri=settings.graph_db_uri,
            user=settings.graph_db_user,
            password=settings.graph_db_password
        )
    return _graph_store_instance


def get_pipeline() -> Pipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        v_store = get_vector_store()
        g_store = get_graph_store()
        
        v_agent = VectorSearchAgent(v_store, top_k=settings.top_k_vector)
        g_agent = GraphSearchAgent(g_store, top_k=settings.top_k_graph)
        w_agent = WebSearchAgent(top_k=settings.top_k_web)
        
        merger = ContextMerger()
        planner = PlannerAgent()
        reasoning = ReasoningAgent()
        answer = AnswerGeneratorAgent()
        citation = CitationCheckerAgent()
        evaluator = QualityEvaluator()
        
        _pipeline_instance = Pipeline(
            planner=planner,
            vector_agent=v_agent,
            graph_agent=g_agent,
            web_agent=w_agent,
            merger=merger,
            reasoning_agent=reasoning,
            answer_agent=answer,
            citation_checker=citation,
            evaluator=evaluator
        )
    return _pipeline_instance


# --- Schemas ---

class WorkspaceCreate(BaseModel):
    name: str


class CollectionCreate(BaseModel):
    name: str


class FolderCreate(BaseModel):
    name: str


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class FactCreate(BaseModel):
    fact_text: str


class TaskCreate(BaseModel):
    title: str
    status: Optional[str] = "todo"


class NoteCreate(BaseModel):
    title: str
    content: str
    document_id: Optional[str] = None


# --- WORKSPACE ROUTERS ---

@app.post("/workspaces", response_model=Dict[str, Any])
def create_workspace(req: WorkspaceCreate, db: Session = Depends(get_db)):
    ws = Workspace(name=req.name)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    
    # Create default collections for clean layout
    default_collections = ["Papers", "GitHub", "Datasets", "Blogs", "Notes", "Videos"]
    for col_name in default_collections:
        col = Collection(workspace_id=ws.id, name=col_name)
        db.add(col)
    db.commit()
    
    return {"id": ws.id, "name": ws.name}


@app.get("/workspaces", response_model=List[Dict[str, Any]])
def list_workspaces(db: Session = Depends(get_db)):
    workspaces = db.query(Workspace).all()
    return [{"id": w.id, "name": w.name, "created_at": w.created_at} for w in workspaces]


@app.delete("/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str, db: Session = Depends(get_db)):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Clean up associated vector chunks
    v_store = get_vector_store()
    for doc in ws.documents:
        v_store.delete_by_source(doc.id)

    db.delete(ws)
    db.commit()
    return {"message": "Workspace deleted successfully"}


# --- COLLECTIONS & FOLDERS ---

@app.get("/workspaces/{workspace_id}/collections")
def get_workspace_collections(workspace_id: str, db: Session = Depends(get_db)):
    collections = db.query(Collection).filter(Collection.workspace_id == workspace_id).all()
    result = []
    for col in collections:
        result.append({
            "id": col.id,
            "name": col.name,
            "folders": [{"id": f.id, "name": f.name} for f in col.folders]
        })
    return result


@app.post("/workspaces/{workspace_id}/collections")
def create_collection(workspace_id: str, req: CollectionCreate, db: Session = Depends(get_db)):
    col = Collection(workspace_id=workspace_id, name=req.name)
    db.add(col)
    db.commit()
    db.refresh(col)
    return {"id": col.id, "name": col.name}


@app.post("/collections/{collection_id}/folders")
def create_folder(collection_id: str, req: FolderCreate, db: Session = Depends(get_db)):
    fol = Folder(collection_id=collection_id, name=req.name)
    db.add(fol)
    db.commit()
    db.refresh(fol)
    return {"id": fol.id, "name": fol.name}


# --- INGESTION ENDPOINT ---

@app.post("/workspaces/{workspace_id}/ingest")
async def ingest_source(
    workspace_id: str,
    source_url: Optional[str] = Form(None),
    collection_id: Optional[str] = Form(None),
    folder_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Ingests files (PDF) or URLs (GitHub, YouTube, arXiv, general websites).
    """
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    temp_path = None
    source_target = ""
    source_type = ""

    # 1. Determine input target (File vs URL)
    if file:
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        source_target = temp_path
    elif source_url:
        source_target = source_url
    else:
        raise HTTPException(status_code=400, detail="Must provide either file upload or source_url")

    # 2. Select appropriate Ingestor
    ingestors = [
        PaperIngestor(),
        GitHubIngestor(),
        YouTubeIngestor(),
        PDFIngestor(),
        WebIngestor()
    ]
    
    selected_ingestor = None
    for ing in ingestors:
        try:
            if ing.can_handle(source_target):
                selected_ingestor = ing
                break
        except Exception:
            continue

    if not selected_ingestor:
        if temp_path:
            shutil.rmtree(os.path.dirname(temp_path), ignore_errors=True)
        raise HTTPException(status_code=400, detail="Unsupported source format or URL")

    # 3. Execute parsing
    try:
        norm_doc = selected_ingestor.ingest(source_target)
    except Exception as e:
        if temp_path:
            shutil.rmtree(os.path.dirname(temp_path), ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    # Clean up temp file
    if temp_path:
        shutil.rmtree(os.path.dirname(temp_path), ignore_errors=True)

    # 4. Save to Database
    db_doc = Document(
        workspace_id=workspace_id,
        folder_id=folder_id if folder_id else None,
        title=norm_doc.title,
        file_path_or_url=source_url if source_url else file.filename,
        source_type=norm_doc.source_type,
        metadata_json=norm_doc.metadata
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # 5. Semantic Chunking & Vector Store Upserting
    chunks = chunk_document(norm_doc, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)
    
    # Overwrite chunk document IDs with stable database primary key
    for c in chunks:
        c.document_id = db_doc.id
        c.metadata["document_id"] = db_doc.id

    v_store = get_vector_store()
    v_store.upsert(chunks, workspace_id=workspace_id)

    # 6. Graph Store Insertion (One-Shot Token Conserving Entity Extraction)
    # Extracts nodes/relations from the document summary/first 2000 chars to conserve API limits
    g_store = get_graph_store()
    snippet = norm_doc.text[:2000]
    
    # Run simple entity extraction pipeline asynchronously/lazily
    graph_data = g_store.entity_extraction_pipeline(snippet)
    
    # Load into neo4j
    for ent in graph_data.get("entities", []):
        g_store.add_entity(ent["type"], ent["id"], ent.get("properties", {}))
    for rel in graph_data.get("relationships", []):
        g_store.add_relationship(rel["from_id"], rel["to_id"], rel["type"])

    return {
        "document_id": db_doc.id,
        "title": db_doc.title,
        "source_type": db_doc.source_type,
        "chunks_count": len(chunks)
    }


@app.get("/workspaces/{workspace_id}/documents")
def list_documents(workspace_id: str, db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.workspace_id == workspace_id).all()
    return [{
        "id": d.id,
        "title": d.title,
        "source_type": d.source_type,
        "file_path_or_url": d.file_path_or_url,
        "created_at": d.created_at,
        "folder_id": d.folder_id
    } for d in docs]


@app.delete("/documents/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    v_store = get_vector_store()
    v_store.delete_by_source(document_id)
    
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}


# --- PERSISTENT WORKSPACE FACTS (AI MEMORY) ---

@app.get("/workspaces/{workspace_id}/facts")
def get_workspace_facts(workspace_id: str, db: Session = Depends(get_db)):
    facts = db.query(WorkspaceFact).filter(WorkspaceFact.workspace_id == workspace_id).all()
    return [{"id": f.id, "fact_text": f.fact_text, "created_at": f.created_at} for f in facts]


@app.post("/workspaces/{workspace_id}/facts")
def add_workspace_fact(workspace_id: str, req: FactCreate, db: Session = Depends(get_db)):
    fact = WorkspaceFact(workspace_id=workspace_id, fact_text=req.fact_text)
    db.add(fact)
    db.commit()
    db.refresh(fact)
    return {"id": fact.id, "fact_text": fact.fact_text}


@app.delete("/facts/{fact_id}")
def delete_workspace_fact(fact_id: str, db: Session = Depends(get_db)):
    fact = db.query(WorkspaceFact).filter(WorkspaceFact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    db.delete(fact)
    db.commit()
    return {"message": "Fact deleted"}


# --- PROJECTS HUB ENDPOINTS ---

@app.post("/workspaces/{workspace_id}/projects")
def create_project(workspace_id: str, req: ProjectCreate, db: Session = Depends(get_db)):
    proj = Project(workspace_id=workspace_id, name=req.name, description=req.description)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return {"id": proj.id, "name": proj.name}


@app.get("/workspaces/{workspace_id}/projects")
def list_projects(workspace_id: str, db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.workspace_id == workspace_id).all()
    return [{"id": p.id, "name": p.name, "description": p.description, "created_at": p.created_at} for p in projects]


# Project Bookmarks
@app.post("/projects/{project_id}/bookmark/{document_id}")
def bookmark_document(project_id: str, document_id: str, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == project_id).first()
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not proj or not doc:
        raise HTTPException(status_code=404, detail="Project or Document not found")
    
    if doc not in proj.documents:
        proj.documents.append(doc)
        db.commit()
    return {"message": "Document bookmarked in project"}


@app.get("/projects/{project_id}/bookmarks")
def list_project_bookmarks(project_id: str, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return [{"id": d.id, "title": d.title, "source_type": d.source_type} for d in proj.documents]


# Project Tasks
@app.post("/projects/{project_id}/tasks")
def create_task(project_id: str, req: TaskCreate, db: Session = Depends(get_db)):
    t = Task(project_id=project_id, title=req.title, status=req.status)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "title": t.title, "status": t.status}


@app.get("/projects/{project_id}/tasks")
def list_tasks(project_id: str, db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    return [{"id": t.id, "title": t.title, "status": t.status} for t in tasks]


@app.put("/tasks/{task_id}")
def update_task_status(task_id: str, status: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = status
    db.commit()
    return {"id": task.id, "status": task.status}


# Project Personal Notes
@app.post("/workspaces/{workspace_id}/notes")
def create_personal_note(workspace_id: str, req: NoteCreate, db: Session = Depends(get_db)):
    note = PersonalNote(
        workspace_id=workspace_id,
        project_id=req.project_id if hasattr(req, "project_id") else None,
        document_id=req.document_id,
        title=req.title,
        content=req.content
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "title": note.title}


@app.get("/workspaces/{workspace_id}/notes")
def list_personal_notes(workspace_id: str, db: Session = Depends(get_db)):
    notes = db.query(PersonalNote).filter(PersonalNote.workspace_id == workspace_id).all()
    return [{"id": n.id, "title": n.title, "content": n.content, "updated_at": n.updated_at} for n in notes]


# --- AGENTIC RAG CHAT QUERY ROUTER ---

@app.post("/projects/{project_id}/query")
def run_agentic_query(project_id: str, req: QueryRequest, db: Session = Depends(get_db)):
    """
    Executes the full LangGraph Agentic query loop for the project.
    """
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # 1. Initialize or get active chat session
    session_id = req.session_id
    if not session_id:
        # Create a new session
        session = ChatSession(project_id=project_id, title=req.query[:40])
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
    else:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="ChatSession not found")

    # 2. Compile Conversation History
    history = []
    for msg in session.messages:
        history.append({"role": msg.role, "content": msg.content})

    # Save user query
    user_msg = ChatMessage(session_id=session_id, role="user", content=req.query)
    db.add(user_msg)
    db.commit()

    # 3. Load Workspace Memory (facts/preferences)
    workspace_facts = [f.fact_text for f in proj.workspace.facts]

    # 4. Invoke LangGraph pipeline
    rag_pipeline = get_pipeline()
    try:
        pipeline_output = rag_pipeline.run(
            query=req.query,
            workspace_id=proj.workspace_id,
            project_id=project_id,
            history=history,
            workspace_facts=workspace_facts
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {e}")

    # 5. Save assistant reply
    citations = [
        {
            "source": item.get("source"),
            "source_type": item.get("source_type"),
            "text_snippet": item.get("text", "")[:100],
            "metadata": item.get("metadata", {})
        }
        for item in pipeline_output["retrieved_chunks"]
    ]
    
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=pipeline_output["final_answer"],
        citations=citations,
        eval_metrics=pipeline_output["eval_metrics"]
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "session_id": session_id,
        "answer": pipeline_output["final_answer"],
        "citations": citations,
        "eval_metrics": pipeline_output["eval_metrics"],
        "selected_agent": pipeline_output["selected_agent"]
    }


# --- DASHBOARD STATS ---

@app.get("/workspaces/{workspace_id}/dashboard")
def get_dashboard_stats(workspace_id: str, db: Session = Depends(get_db)):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Calculate metrics
    docs = ws.documents
    doc_count = len(docs)
    video_count = sum(1 for d in docs if d.source_type == "youtube")
    repo_count = sum(1 for d in docs if d.source_type == "github")
    pdf_count = sum(1 for d in docs if d.source_type == "pdf")
    web_count = sum(1 for d in docs if d.source_type == "web")

    # Load average evaluations from project query messages
    faith_scores = []
    relevance_scores = []
    latencies = []
    
    for proj in ws.projects:
        for sess in proj.chat_sessions:
            for msg in sess.messages:
                if msg.role == "assistant" and msg.eval_metrics:
                    m = msg.eval_metrics
                    if "faithfulness" in m:
                        faith_scores.append(m["faithfulness"])
                    if "answer_relevancy" in m:
                        relevance_scores.append(m["answer_relevancy"])
                    if "latency" in m:
                        latencies.append(m["latency"])

    avg_faith = round(sum(faith_scores) / len(faith_scores), 2) if faith_scores else 1.0
    avg_rel = round(sum(relevance_scores) / len(relevance_scores), 2) if relevance_scores else 1.0
    avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    return {
        "stats": {
            "documents": doc_count,
            "videos": video_count,
            "repositories": repo_count,
            "papers": sum(1 for d in docs if d.source_type == "paper"),
            "pdf_count": pdf_count,
            "web_count": web_count,
            "projects": len(ws.projects),
            "notes": len(ws.notes)
        },
        "performance": {
            "avg_faithfulness": avg_faith,
            "avg_relevancy": avg_rel,
            "avg_latency": avg_lat
        }
    }
