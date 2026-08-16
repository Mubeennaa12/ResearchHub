"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  FolderOpen,
  Plus,
  Trash2,
  Bookmark,
  CheckSquare,
  MessageSquare,
  FileText,
  Video,
  Globe,
  Upload,
  Link2,
  BookOpen,
  PieChart,
  Brain,
  Activity,
  Layers,
  Send,
  Loader2,
  ChevronRight,
  User,
  Cpu,
  BarChart3,
  Calendar,
  AlertTriangle,
  Menu,
  X,
  FileCode,
  Notebook
} from "lucide-react";

const GithubIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
    <path d="M9 18c-4.51 2-5-2-7-2" />
  </svg>
);


// API Endpoint configuration
const API_BASE = "http://localhost:8000";

export default function WorkspacePage() {
  const [isMounted, setIsMounted] = useState(false);
  // Navigation & Workspace State
  const [activeTab, setActiveTab] = useState<"dashboard" | "explorer" | "project" | "memory">("dashboard");
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<any>(null);
  const [showWorkspaceModal, setShowWorkspaceModal] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Collections & Folders
  const [collections, setCollections] = useState<any[]>([]);
  const [activeCollection, setActiveCollection] = useState<any>(null);
  const [showFolderModal, setShowFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");

  // Projects
  const [projects, setProjects] = useState<any[]>([]);
  const [activeProject, setActiveProject] = useState<any>(null);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");

  // Ingestion
  const [ingestTab, setIngestTab] = useState<"file" | "url">("file");
  const [sourceUrl, setSourceUrl] = useState("");
  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [selectedFolderId, setSelectedFolderId] = useState("");

  // Documents
  const [documents, setDocuments] = useState<any[]>([]);
  const [activeDocument, setActiveDocument] = useState<any>(null);

  // Notes (linked to document or project)
  const [notes, setNotes] = useState<any[]>([]);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [isEditingNote, setIsEditingNote] = useState(false);

  // Project Memory / Facts
  const [facts, setFacts] = useState<any[]>([]);
  const [newFact, setNewFact] = useState("");

  // Tasks
  const [tasks, setTasks] = useState<any[]>([]);
  const [newTaskTitle, setNewTaskTitle] = useState("");

  // Chats
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [queryInput, setQueryInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<any>(null);

  // Dashboard Stats
  const [stats, setStats] = useState<any>({
    documents: 0,
    videos: 0,
    repositories: 0,
    papers: 0,
    pdf_count: 0,
    web_count: 0,
    projects: 0,
    notes: 0
  });
  const [performance, setPerformance] = useState<any>({
    avg_faithfulness: 1.0,
    avg_relevancy: 1.0,
    avg_latency: 0.0
  });

  // Server state helper
  const [isOffline, setIsOffline] = useState(false);

  // --- MOCK DATABASE FALLBACK STATE ---
  const [mockDb, setMockDb] = useState<any>({
    workspaces: [{ id: "mock-ws-1", name: "AI Research", created_at: new Date().toISOString() }],
    facts: [
      { id: "mock-fact-1", fact_text: "User prefers FastAPI and Next.js stacks." },
      { id: "mock-fact-2", fact_text: "Always double check mathematical equations from context." }
    ],
    collections: [
      { id: "mock-col-1", name: "Papers", folders: [{ id: "mock-f-1", name: "Vision Transformers" }] },
      { id: "mock-col-2", name: "GitHub", folders: [] },
      { id: "mock-col-3", name: "Videos", folders: [] }
    ],
    documents: [
      {
        id: "mock-doc-1",
        title: "Attention Is All You Need.pdf",
        source_type: "pdf",
        file_path_or_url: "attention.pdf",
        created_at: new Date().toISOString(),
        folder_id: "mock-f-1"
      },
      {
        id: "mock-doc-2",
        title: "google-gemini/antigravity",
        source_type: "github",
        file_path_or_url: "github.com/google-gemini/antigravity",
        created_at: new Date().toISOString(),
        folder_id: null
      }
    ],
    projects: [{ id: "mock-p-1", name: "Scene Prediction", description: "Researching visual scene classification models" }],
    bookmarks: [],
    tasks: [{ id: "mock-t-1", title: "Read SegFormer paper", status: "todo" }],
    notes: [{ id: "mock-n-1", title: "transformer notes", content: "ViTs work best with pre-training on huge datasets.", updated_at: new Date().toISOString() }],
    messages: [
      {
        id: "mock-m-1",
        role: "user",
        content: "What is attention mechanism?"
      },
      {
        id: "mock-m-2",
        role: "assistant",
        content: "The attention mechanism allows models to focus on key parts of the input sequence dynamically. [1] It replaces traditional recurrence layers with self-attention steps.",
        citations: [{ source: "Attention Is All You Need.pdf", source_type: "pdf", text_snippet: "An attention function can be described as mapping a query and a set of key-value pairs to an output." }],
        eval_metrics: { faithfulness: 0.98, answer_relevancy: 0.95, latency: 0.45 }
      }
    ]
  });

  // --- FETCH DATA WRAPPERS (DYNAMIC BACKEND OR MOCK) ---

  const fetchWorkspaces = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/workspaces`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setWorkspaces(data);
      setIsOffline(false);
      if (data.length > 0 && !activeWorkspace) {
        setActiveWorkspace(data[0]);
      }
    } catch (e) {
      setIsOffline(true);
      setWorkspaces(mockDb.workspaces);
      if (mockDb.workspaces.length > 0 && !activeWorkspace) {
        setActiveWorkspace(mockDb.workspaces[0]);
      }
    }
  }, [activeWorkspace, mockDb.workspaces]);

  const fetchWorkspaceDetails = useCallback(async () => {
    if (!activeWorkspace) return;
    const wsId = activeWorkspace.id;

    if (isOffline) {
      setCollections(mockDb.collections);
      setDocuments(mockDb.documents);
      setProjects(mockDb.projects);
      setFacts(mockDb.facts);
      setNotes(mockDb.notes);
      
      if (mockDb.projects.length > 0 && !activeProject) {
        setActiveProject(mockDb.projects[0]);
      }
      
      // Update local dashboard stats
      setStats({
        documents: mockDb.documents.length,
        videos: mockDb.documents.filter((d: any) => d.source_type === "youtube").length,
        repositories: mockDb.documents.filter((d: any) => d.source_type === "github").length,
        papers: mockDb.documents.filter((d: any) => d.source_type === "paper").length,
        pdf_count: mockDb.documents.filter((d: any) => d.source_type === "pdf").length,
        web_count: mockDb.documents.filter((d: any) => d.source_type === "web").length,
        projects: mockDb.projects.length,
        notes: mockDb.notes.length
      });
      return;
    }

    try {
      // Collections
      const colRes = await fetch(`${API_BASE}/workspaces/${wsId}/collections`);
      if (colRes.ok) setCollections(await colRes.json());

      // Documents
      const docRes = await fetch(`${API_BASE}/workspaces/${wsId}/documents`);
      if (docRes.ok) setDocuments(await docRes.json());

      // Projects
      const projRes = await fetch(`${API_BASE}/workspaces/${wsId}/projects`);
      if (projRes.ok) {
        const projs = await projRes.json();
        setProjects(projs);
        if (projs.length > 0 && !activeProject) {
          setActiveProject(projs[0]);
        }
      }

      // Memory Facts
      const factRes = await fetch(`${API_BASE}/workspaces/${wsId}/facts`);
      if (factRes.ok) setFacts(await factRes.json());

      // Notes
      const noteRes = await fetch(`${API_BASE}/workspaces/${wsId}/notes`);
      if (noteRes.ok) setNotes(await noteRes.json());

      // Dashboard Stats
      const statRes = await fetch(`${API_BASE}/workspaces/${wsId}/dashboard`);
      if (statRes.ok) {
        const s = await statRes.json();
        setStats(s.stats);
        setPerformance(s.performance);
      }
    } catch (e) {
      console.error("Error loading workspace data details from backend.");
    }
  }, [activeWorkspace, isOffline, activeProject, mockDb]);

  const fetchProjectDetails = useCallback(async () => {
    if (!activeProject) return;
    const projId = activeProject.id;

    if (isOffline) {
      setTasks(mockDb.tasks);
      setMessages(mockDb.messages);
      return;
    }

    try {
      // Tasks
      const taskRes = await fetch(`${API_BASE}/projects/${projId}/tasks`);
      if (taskRes.ok) setTasks(await taskRes.json());
      
      // Chats (simulate loading project active session history)
      // Since it's a demo, we can call a query stats endpoint or load from message table.
    } catch (e) {
      console.error("Error loading project details.");
    }
  }, [activeProject, isOffline, mockDb]);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  useEffect(() => {
    fetchWorkspaceDetails();
  }, [activeWorkspace, fetchWorkspaceDetails]);

  useEffect(() => {
    fetchProjectDetails();
  }, [activeProject, fetchProjectDetails]);

  // --- ACTIONS ---

  const handleCreateWorkspace = async () => {
    if (!newWorkspaceName.trim()) return;

    if (isOffline) {
      const newWs = {
        id: `mock-ws-${Date.now()}`,
        name: newWorkspaceName,
        created_at: new Date().toISOString()
      };
      setMockDb((prev: any) => ({
        ...prev,
        workspaces: [...prev.workspaces, newWs]
      }));
      setNewWorkspaceName("");
      setShowWorkspaceModal(false);
      setActiveWorkspace(newWs);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/workspaces`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newWorkspaceName })
      });
      if (res.ok) {
        const data = await res.json();
        setNewWorkspaceName("");
        setShowWorkspaceModal(false);
        fetchWorkspaces();
        setActiveWorkspace(data);
      }
    } catch (e) {
      alert("Failed to connect to backend");
    }
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim() || !activeCollection) return;

    if (isOffline) {
      const newF = { id: `mock-f-${Date.now()}`, name: newFolderName };
      const updatedCols = mockDb.collections.map((c: any) => {
        if (c.id === activeCollection.id) {
          return { ...c, folders: [...c.folders, newF] };
        }
        return c;
      });
      setMockDb((prev: any) => ({ ...prev, collections: updatedCols }));
      setNewFolderName("");
      setShowFolderModal(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/collections/${activeCollection.id}/folders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newFolderName })
      });
      if (res.ok) {
        setNewFolderName("");
        setShowFolderModal(false);
        fetchWorkspaceDetails();
      }
    } catch (e) {
      alert("Failed to connect to backend");
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim() || !activeWorkspace) return;

    if (isOffline) {
      const newProj = {
        id: `mock-p-${Date.now()}`,
        name: newProjectName,
        description: newProjectDesc
      };
      setMockDb((prev: any) => ({
        ...prev,
        projects: [...prev.projects, newProj]
      }));
      setNewProjectName("");
      setNewProjectDesc("");
      setShowProjectModal(false);
      setActiveProject(newProj);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/workspaces/${activeWorkspace.id}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newProjectName, description: newProjectDesc })
      });
      if (res.ok) {
        const data = await res.json();
        setNewProjectName("");
        setNewProjectDesc("");
        setShowProjectModal(false);
        fetchWorkspaceDetails();
        setActiveProject(data);
      }
    } catch (e) {
      alert("Failed to create project");
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace) return;
    setIngestLoading(true);

    if (isOffline) {
      setTimeout(() => {
        const mockDoc = {
          id: `mock-doc-${Date.now()}`,
          title: ingestTab === "url" ? sourceUrl.split("/").pop() || "Web Resource" : ingestFile?.name || "Uploaded Document",
          source_type: ingestTab === "url" ? (sourceUrl.includes("github") ? "github" : sourceUrl.includes("youtube") ? "youtube" : "web") : "pdf",
          file_path_or_url: ingestTab === "url" ? sourceUrl : ingestFile?.name || "Local PDF",
          created_at: new Date().toISOString(),
          folder_id: selectedFolderId || null
        };
        setMockDb((prev: any) => ({
          ...prev,
          documents: [...prev.documents, mockDoc]
        }));
        setIngestLoading(false);
        setSourceUrl("");
        setIngestFile(null);
        fetchWorkspaceDetails();
      }, 1500);
      return;
    }

    try {
      const formData = new FormData();
      if (ingestTab === "url" && sourceUrl) {
        formData.append("source_url", sourceUrl);
      } else if (ingestTab === "file" && ingestFile) {
        formData.append("file", ingestFile);
      } else {
        throw new Error("Must fill ingestion form fields");
      }

      if (selectedFolderId) {
        formData.append("folder_id", selectedFolderId);
      }

      const res = await fetch(`${API_BASE}/workspaces/${activeWorkspace.id}/ingest`, {
        method: "POST",
        body: formData
      });

      if (res.ok) {
        setSourceUrl("");
        setIngestFile(null);
        fetchWorkspaceDetails();
      } else {
        const err = await res.json();
        alert(`Ingestion failed: ${err.detail}`);
      }
    } catch (e: any) {
      alert(e.message || "Failed to submit ingestion");
    } finally {
      setIngestLoading(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (isOffline) {
      setMockDb((prev: any) => ({
        ...prev,
        documents: prev.documents.filter((d: any) => d.id !== docId)
      }));
      fetchWorkspaceDetails();
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`, { method: "DELETE" });
      if (res.ok) fetchWorkspaceDetails();
    } catch (e) {
      alert("Failed to delete document");
    }
  };

  // Notes
  const handleSaveNote = async () => {
    if (!noteTitle.trim() || !activeWorkspace) return;

    if (isOffline) {
      const updatedNotes = mockDb.notes.map((n: any) => {
        if (n.id === activeDocument?.id || n.id === "mock-n-1") {
          return { ...n, title: noteTitle, content: noteContent, updated_at: new Date().toISOString() };
        }
        return n;
      });
      setMockDb((prev: any) => ({ ...prev, notes: updatedNotes }));
      setIsEditingNote(false);
      fetchWorkspaceDetails();
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/workspaces/${activeWorkspace.id}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: noteTitle,
          content: noteContent,
          document_id: activeDocument?.id || null
        })
      });
      if (res.ok) {
        setNoteTitle("");
        setNoteContent("");
        setIsEditingNote(false);
        fetchWorkspaceDetails();
      }
    } catch (e) {
      alert("Failed to save note");
    }
  };

  // Facts (Memory)
  const handleAddFact = async () => {
    if (!newFact.trim() || !activeWorkspace) return;

    if (isOffline) {
      const newF = { id: `mock-f-${Date.now()}`, fact_text: newFact, created_at: new Date().toISOString() };
      setMockDb((prev: any) => ({ ...prev, facts: [...prev.facts, newF] }));
      setNewFact("");
      fetchWorkspaceDetails();
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/workspaces/${activeWorkspace.id}/facts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fact_text: newFact })
      });
      if (res.ok) {
        setNewFact("");
        fetchWorkspaceDetails();
      }
    } catch (e) {
      alert("Failed to add memory fact");
    }
  };

  const handleDeleteFact = async (factId: string) => {
    if (isOffline) {
      setMockDb((prev: any) => ({ ...prev, facts: prev.facts.filter((f: any) => f.id !== factId) }));
      fetchWorkspaceDetails();
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/facts/${factId}`, { method: "DELETE" });
      if (res.ok) fetchWorkspaceDetails();
    } catch (e) {
      alert("Failed to delete fact");
    }
  };

  // Tasks
  const handleAddTask = async () => {
    if (!newTaskTitle.trim() || !activeProject) return;

    if (isOffline) {
      const newT = { id: `mock-t-${Date.now()}`, title: newTaskTitle, status: "todo" };
      setMockDb((prev: any) => ({ ...prev, tasks: [...prev.tasks, newT] }));
      setNewTaskTitle("");
      fetchProjectDetails();
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/projects/${activeProject.id}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTaskTitle })
      });
      if (res.ok) {
        setNewTaskTitle("");
        fetchProjectDetails();
      }
    } catch (e) {
      alert("Failed to add task");
    }
  };

  const handleToggleTask = async (task: any) => {
    const nextStatus = task.status === "done" ? "todo" : "done";

    if (isOffline) {
      const updatedTasks = mockDb.tasks.map((t: any) => {
        if (t.id === task.id) return { ...t, status: nextStatus };
        return t;
      });
      setMockDb((prev: any) => ({ ...prev, tasks: updatedTasks }));
      fetchProjectDetails();
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/tasks/${task.id}?status=${nextStatus}`, { method: "PUT" });
      if (res.ok) fetchProjectDetails();
    } catch (e) {
      alert("Failed to toggle task");
    }
  };

  // Chat Query Call
  const handleSendQuery = async () => {
    if (!queryInput.trim()) return;
    if (!activeProject) {
      alert("Please select or create a project first!");
      return;
    }
    const currentQuery = queryInput;
    setQueryInput("");
    setChatLoading(true);

    const userMessage = { id: `user-msg-${Date.now()}`, role: "user", content: currentQuery };
    setMessages((prev) => [...prev, userMessage]);

    if (isOffline) {
      setTimeout(() => {
        const reply = {
          id: `asst-msg-${Date.now()}`,
          role: "assistant",
          content: "I parsed the local resources. Based on your documents, the attention mechanism functions as a mapping of queries, keys, and values [1]. It helps extract contextual vectors for tokens. We run the query rewriter loop twice.",
          citations: [
            { source: "Attention Is All You Need.pdf", source_type: "pdf", text_snippet: "An attention function can be described as mapping a query and a set of key-value pairs to an output." }
          ],
          eval_metrics: { faithfulness: 0.99, answer_relevancy: 0.98, latency: 0.38 }
        };
        setMessages((prev) => [...prev, reply]);
        setChatLoading(false);
      }, 2000);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/projects/${activeProject.id}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: currentQuery,
          session_id: activeSessionId
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (!activeSessionId) setActiveSessionId(data.session_id);
        
        const assistantReply = {
          id: `asst-msg-${Date.now()}`,
          role: "assistant",
          content: data.answer,
          citations: data.citations,
          eval_metrics: data.eval_metrics
        };
        setMessages((prev) => [...prev, assistantReply]);
      }
    } catch (e) {
      alert("Search failed or timed out");
    } finally {
      setChatLoading(false);
    }
  };

  // Utility to map source types to icons
  const getSourceIcon = (type: string) => {
    switch (type) {
      case "pdf":
        return <FileText className="w-4 h-4 text-rose-400" />;
      case "youtube":
        return <Video className="w-4 h-4 text-red-400" />;
      case "github":
        return <GithubIcon className="w-4 h-4 text-purple-400" />;
      case "paper":
        return <BookOpen className="w-4 h-4 text-emerald-400" />;
      default:
        return <Globe className="w-4 h-4 text-blue-400" />;
    }
  };

  if (!isMounted) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-violet-500 mr-2" />
        <span>Loading AI Research Workspace...</span>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-100 font-sans">
      
      {/* Sidebar Panel */}
      <aside className={`flex flex-col border-r border-slate-800 bg-slate-900/40 backdrop-blur-xl transition-all duration-300 ${isSidebarOpen ? "w-64" : "w-16"} shrink-0 overflow-hidden`}>
        
        {/* Header Title */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-2 overflow-hidden">
            <Brain className="w-6 h-6 text-violet-500 shrink-0 animate-pulse" />
            {isSidebarOpen && <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-violet-400 to-indigo-300 bg-clip-text text-transparent">Antigravity</span>}
          </div>
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-1 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-100 hidden md:block">
            {isSidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>

        {/* Workspace Selection Selector */}
        {isSidebarOpen && (
          <div className="p-4 border-b border-slate-800 shrink-0">
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Active Workspace</label>
            <div className="flex gap-2">
              <select 
                value={activeWorkspace?.id || ""} 
                onChange={(e) => {
                  const ws = workspaces.find((w: any) => w.id === e.target.value);
                  if (ws) setActiveWorkspace(ws);
                }}
                className="w-full px-3 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg text-sm text-slate-200 outline-none focus:ring-1 focus:ring-violet-500 cursor-pointer"
              >
                {workspaces.map((w: any) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
              <button 
                onClick={() => setShowWorkspaceModal(true)} 
                className="p-2 bg-slate-800 border border-slate-700 hover:bg-violet-600 hover:border-violet-500 rounded-lg text-slate-300 hover:text-white transition-all shadow-sm"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Navigation Tabs List */}
        <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
              activeTab === "dashboard" ? "bg-violet-600/20 border border-violet-500/30 text-violet-400 font-semibold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <PieChart className="w-5 h-5" />
            {isSidebarOpen && <span>Dashboard</span>}
          </button>
          <button
            onClick={() => setActiveTab("explorer")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
              activeTab === "explorer" ? "bg-violet-600/20 border border-violet-500/30 text-violet-400 font-semibold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <FolderOpen className="w-5 h-5" />
            {isSidebarOpen && <span>Knowledge Base</span>}
          </button>
          <button
            onClick={() => setActiveTab("project")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
              activeTab === "project" ? "bg-violet-600/20 border border-violet-500/30 text-violet-400 font-semibold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <Layers className="w-5 h-5" />
            {isSidebarOpen && <span>Projects Hub</span>}
          </button>
          <button
            onClick={() => setActiveTab("memory")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
              activeTab === "memory" ? "bg-violet-600/20 border border-violet-500/30 text-violet-400 font-semibold" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <Brain className="w-5 h-5" />
            {isSidebarOpen && <span>AI Facts Memory</span>}
          </button>
        </nav>

        {/* Sidebar Footer status */}
        {isSidebarOpen && (
          <div className="p-4 border-t border-slate-800 bg-slate-950/20 shrink-0">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Cpu className="w-3.5 h-3.5" />
              <span>Model Provider:</span>
              <span className="text-violet-400 font-semibold uppercase">Gemini Flash</span>
            </div>
            {isOffline && (
              <div className="flex items-center gap-1.5 text-xs text-amber-500 mt-2">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>Backend offline. Running locally.</span>
              </div>
            )}
          </div>
        )}
      </aside>

      {/* Main Workspace Frame */}
      <main className="flex-1 flex flex-col overflow-hidden bg-slate-950">
        
        {/* Top Navigation Bar */}
        <header className="h-16 border-b border-slate-800 flex items-center justify-between px-6 shrink-0 bg-slate-900/10">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-slate-100">{activeWorkspace?.name || "Workspace"}</h2>
          </div>
          
          <div className="flex items-center gap-3">
            <span className="px-2 py-0.5 text-xs bg-emerald-500/15 border border-emerald-500/20 text-emerald-400 rounded-md font-medium">Free Tier</span>
            <div className="w-8 h-8 rounded-full bg-violet-600 border border-violet-500 flex items-center justify-center font-bold text-sm shadow-md shadow-violet-500/15">
              U
            </div>
          </div>
        </header>

        {/* Content Body Area */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-950">
          
          {/* TAB 1: DASHBOARD VIEW */}
          {activeTab === "dashboard" && (
            <div className="space-y-6 max-w-6xl mx-auto">
              
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-slate-100 to-slate-300 bg-clip-text text-transparent">Knowledge Hub Overview</h1>
                  <p className="text-sm text-slate-400">Track database records, storage files, and RAG retrieval latency.</p>
                </div>
              </div>

              {/* Statistical Cards Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-slate-900/40 border border-slate-800/80 p-5 rounded-2xl flex items-center justify-between shadow-sm">
                  <div>
                    <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Total Documents</span>
                    <h3 className="text-3xl font-bold text-slate-100 mt-1">{stats.documents}</h3>
                  </div>
                  <div className="p-3 bg-violet-500/10 border border-violet-500/10 text-violet-400 rounded-2xl">
                    <FileText className="w-6 h-6" />
                  </div>
                </div>

                <div className="bg-slate-900/40 border border-slate-800/80 p-5 rounded-2xl flex items-center justify-between shadow-sm">
                  <div>
                    <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">YouTube Ingests</span>
                    <h3 className="text-3xl font-bold text-slate-100 mt-1">{stats.videos}</h3>
                  </div>
                  <div className="p-3 bg-red-500/10 border border-red-500/10 text-red-400 rounded-2xl">
                    <Video className="w-6 h-6" />
                  </div>
                </div>

                <div className="bg-slate-900/40 border border-slate-800/80 p-5 rounded-2xl flex items-center justify-between shadow-sm">
                  <div>
                    <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">GitHub Repos</span>
                    <h3 className="text-3xl font-bold text-slate-100 mt-1">{stats.repositories}</h3>
                  </div>
                  <div className="p-3 bg-purple-500/10 border border-purple-500/10 text-purple-400 rounded-2xl">
                    <GithubIcon className="w-6 h-6" />
                  </div>
                </div>

                <div className="bg-slate-900/40 border border-slate-800/80 p-5 rounded-2xl flex items-center justify-between shadow-sm">
                  <div>
                    <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Research Papers</span>
                    <h3 className="text-3xl font-bold text-slate-100 mt-1">{stats.papers}</h3>
                  </div>
                  <div className="p-3 bg-emerald-500/10 border border-emerald-500/10 text-emerald-400 rounded-2xl">
                    <BookOpen className="w-6 h-6" />
                  </div>
                </div>
              </div>

              {/* RAG EVALUATION PANEL */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                <div className="lg:col-span-2 bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2 text-violet-400">
                      <BarChart3 className="w-5 h-5" />
                      <h3 className="font-bold text-slate-200">System Evaluation Metrics</h3>
                    </div>
                    <p className="text-xs text-slate-500 mb-6">Score analysis compiled based on RAGAS rules over actual agent replies.</p>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-slate-950/40 border border-slate-800 p-4 rounded-xl text-center">
                      <span className="text-xs text-slate-400 block mb-1">Faithfulness</span>
                      <span className="text-2xl font-extrabold text-violet-400">{(performance.avg_faithfulness * 100).toFixed(0)}%</span>
                      <p className="text-[10px] text-slate-500 mt-2">Zero-Hallucination score</p>
                    </div>
                    <div className="bg-slate-950/40 border border-slate-800 p-4 rounded-xl text-center">
                      <span className="text-xs text-slate-400 block mb-1">Answer Relevancy</span>
                      <span className="text-2xl font-extrabold text-indigo-400">{(performance.avg_relevancy * 100).toFixed(0)}%</span>
                      <p className="text-[10px] text-slate-500 mt-2">Query target matching</p>
                    </div>
                    <div className="bg-slate-950/40 border border-slate-800 p-4 rounded-xl text-center">
                      <span className="text-xs text-slate-400 block mb-1">Avg Latency</span>
                      <span className="text-2xl font-extrabold text-emerald-400">{performance.avg_latency.toFixed(2)}s</span>
                      <p className="text-[10px] text-slate-500 mt-2">Search loop latency</p>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2 text-violet-400">
                      <Activity className="w-5 h-5" />
                      <h3 className="font-bold text-slate-200">Workspace Statistics</h3>
                    </div>
                  </div>
                  <div className="space-y-3 flex-1 flex flex-col justify-center">
                    <div className="flex justify-between items-center text-sm border-b border-slate-800 pb-2">
                      <span className="text-slate-400">Associated Projects</span>
                      <span className="text-slate-200 font-semibold">{stats.projects}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm border-b border-slate-800 pb-2">
                      <span className="text-slate-400">Personal Notes</span>
                      <span className="text-slate-200 font-semibold">{stats.notes}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm border-b border-slate-800 pb-2">
                      <span className="text-slate-400">PDF Files</span>
                      <span className="text-slate-200 font-semibold">{stats.pdf_count}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-400">Web Links</span>
                      <span className="text-slate-200 font-semibold">{stats.web_count}</span>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* TAB 2: KNOWLEDGE BASE EXPLORER */}
          {activeTab === "explorer" && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-6xl mx-auto h-[calc(100vh-12rem)]">
              
              {/* Hierarchical Browser */}
              <div className="lg:col-span-4 bg-slate-900/30 border border-slate-800 rounded-2xl p-4 flex flex-col overflow-hidden h-full">
                <div className="flex items-center justify-between mb-4 shrink-0">
                  <h3 className="font-bold text-slate-200 text-sm uppercase tracking-wider">Collections Browser</h3>
                  <button 
                    onClick={() => {
                      if (collections.length === 0) {
                        alert("Select a workspace first");
                        return;
                      }
                      setActiveCollection(collections[0]);
                      setShowFolderModal(true);
                    }} 
                    className="p-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>
                
                <div className="flex-1 overflow-y-auto space-y-4">
                  {collections.map((col: any) => (
                    <div key={col.id} className="space-y-1.5">
                      <div 
                        onClick={() => setActiveCollection(col)}
                        className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm font-semibold cursor-pointer transition-colors ${
                          activeCollection?.id === col.id ? "bg-slate-800 text-violet-400" : "text-slate-300 hover:text-slate-100 hover:bg-slate-850"
                        }`}
                      >
                        <Layers className="w-4 h-4" />
                        <span>{col.name}</span>
                      </div>
                      
                      {/* Folders nested */}
                      <div className="pl-6 space-y-1 border-l border-slate-800 ml-3">
                        {col.folders && col.folders.map((f: any) => (
                          <div 
                            key={f.id} 
                            onClick={() => setSelectedFolderId(f.id)}
                            className={`flex items-center gap-2 px-2 py-1 rounded-md text-xs cursor-pointer transition-colors ${
                              selectedFolderId === f.id ? "bg-violet-600/10 text-violet-400 border border-violet-500/20" : "text-slate-400 hover:text-slate-200"
                            }`}
                          >
                            <FolderOpen className="w-3.5 h-3.5" />
                            <span>{f.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Documents Detail Panel */}
              <div className="lg:col-span-5 bg-slate-900/30 border border-slate-800 rounded-2xl p-5 flex flex-col overflow-hidden h-full">
                <h3 className="font-bold text-slate-200 text-sm uppercase tracking-wider mb-4 shrink-0">Documents</h3>
                
                <div className="flex-1 overflow-y-auto space-y-2">
                  {documents.length === 0 ? (
                    <div className="text-center py-12 text-slate-500 text-sm">
                      No documents ingested yet. Upload some files or paste URLs!
                    </div>
                  ) : (
                    documents.map((d: any) => (
                      <div 
                        key={d.id} 
                        onClick={() => {
                          setActiveDocument(d);
                          setNoteTitle(d.title);
                          // find note if any
                          const existingNote = notes.find((n: any) => n.document_id === d.id);
                          setNoteContent(existingNote ? existingNote.content : "");
                          setIsEditingNote(true);
                        }}
                        className={`flex items-center justify-between p-3 border rounded-xl cursor-pointer transition-all ${
                          activeDocument?.id === d.id ? "bg-slate-800/80 border-violet-500/40" : "bg-slate-900/40 border-slate-800 hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-center gap-3 overflow-hidden">
                          {getSourceIcon(d.source_type)}
                          <div className="overflow-hidden">
                            <h4 className="text-sm font-medium text-slate-200 truncate">{d.title}</h4>
                            <span className="text-[10px] text-slate-500">{d.source_type.toUpperCase()} • Ingested {new Date(d.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteDocument(d.id);
                          }}
                          className="p-1.5 rounded-md hover:bg-slate-700 text-slate-500 hover:text-rose-400"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Right Panel: Ingestion Zone & Personal Note Slider */}
              <div className="lg:col-span-3 flex flex-col h-full overflow-hidden">
                {!isEditingNote ? (
                  <div className="bg-slate-900/30 border border-slate-800 rounded-2xl p-5 flex flex-col h-full overflow-y-auto">
                    <h3 className="font-bold text-slate-200 text-sm uppercase tracking-wider mb-4">Ingestion Center</h3>
                    
                    {/* Tab Ingestion */}
                    <div className="flex border-b border-slate-800 mb-4 bg-slate-950/40 p-1 rounded-lg">
                      <button 
                        onClick={() => setIngestTab("file")}
                        className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${ingestTab === "file" ? "bg-violet-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"}`}
                      >
                        File Upload
                      </button>
                      <button 
                        onClick={() => setIngestTab("url")}
                        className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${ingestTab === "url" ? "bg-violet-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"}`}
                      >
                        Web / URL
                      </button>
                    </div>

                    <form onSubmit={handleIngest} className="space-y-4">
                      {ingestTab === "file" ? (
                        <div className="border border-dashed border-slate-700 hover:border-violet-500/40 rounded-xl p-6 text-center cursor-pointer bg-slate-950/20 transition-colors">
                          <input 
                            type="file" 
                            accept=".pdf"
                            onChange={(e) => setIngestFile(e.target.files?.[0] || null)}
                            className="hidden" 
                            id="file-upload" 
                          />
                          <label htmlFor="file-upload" className="cursor-pointer space-y-2 block">
                            <Upload className="w-8 h-8 text-slate-500 mx-auto" />
                            <span className="text-xs text-slate-300 block">{ingestFile ? ingestFile.name : "Select PDF Document"}</span>
                            <span className="text-[10px] text-slate-500 block">Maximum file size 10MB</span>
                          </label>
                        </div>
                      ) : (
                        <div className="space-y-1">
                          <label className="text-[10px] font-semibold text-slate-400 block uppercase">Ingestion Link</label>
                          <div className="flex gap-2">
                            <div className="relative flex-1">
                              <Link2 className="absolute left-2.5 top-2.5 w-4 h-4 text-slate-500" />
                              <input 
                                type="text" 
                                value={sourceUrl}
                                onChange={(e) => setSourceUrl(e.target.value)}
                                placeholder="arXiv, github, youtube, docs links"
                                className="w-full pl-9 pr-3 py-2 bg-slate-800/80 border border-slate-700 rounded-lg text-xs outline-none text-slate-200 placeholder-slate-500"
                              />
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Select folder destination */}
                      <div className="space-y-1">
                        <label className="text-[10px] font-semibold text-slate-400 block uppercase">Destination Folder (Optional)</label>
                        <select
                          value={selectedFolderId}
                          onChange={(e) => setSelectedFolderId(e.target.value)}
                          className="w-full px-3 py-2 bg-slate-850 border border-slate-700 rounded-lg text-xs text-slate-200"
                        >
                          <option value="">No folder (Collection root)</option>
                          {collections.flatMap((c: any) => c.folders || []).map((f: any) => (
                            <option key={f.id} value={f.id}>{f.name}</option>
                          ))}
                        </select>
                      </div>

                      <button 
                        type="submit"
                        disabled={ingestLoading}
                        className="w-full py-2 bg-violet-600 hover:bg-violet-500 disabled:bg-slate-800 rounded-lg text-xs font-semibold text-white transition-all flex items-center justify-center gap-2"
                      >
                        {ingestLoading ? (
                          <>
                            <Loader2 className="w-4.5 h-4.5 animate-spin" />
                            <span>Parsing & Chunking...</span>
                          </>
                        ) : (
                          <span>Submit to Ingestion</span>
                        )}
                      </button>
                    </form>
                  </div>
                ) : (
                  // Markdown Note editor panel
                  <div className="bg-slate-900/30 border border-slate-800 rounded-2xl p-5 flex flex-col h-full overflow-hidden">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4 shrink-0">
                      <h3 className="font-bold text-slate-200 text-sm uppercase tracking-wider">Personal Notes</h3>
                      <button 
                        onClick={() => setIsEditingNote(false)}
                        className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="flex-1 flex flex-col space-y-3 overflow-hidden">
                      <input 
                        type="text" 
                        value={noteTitle}
                        onChange={(e) => setNoteTitle(e.target.value)}
                        placeholder="Note title"
                        className="w-full bg-slate-850 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-violet-500 shrink-0"
                      />
                      <textarea
                        value={noteContent}
                        onChange={(e) => setNoteContent(e.target.value)}
                        placeholder="Write note content in Markdown format..."
                        className="w-full flex-1 bg-slate-850 border border-slate-700 rounded-lg p-3 text-xs text-slate-300 outline-none resize-none focus:ring-1 focus:ring-violet-500 overflow-y-auto"
                      />
                      <button 
                        onClick={handleSaveNote}
                        className="w-full py-2 bg-violet-600 hover:bg-violet-500 rounded-lg text-xs font-semibold text-white shrink-0"
                      >
                        Save Personal Note
                      </button>
                    </div>
                  </div>
                )}
              </div>

            </div>
          )}

          {/* TAB 3: PROJECTS HUB */}
          {activeTab === "project" && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-6xl mx-auto h-[calc(100vh-12rem)]">
              
              {/* Project Selection sidebar */}
              <div className="lg:col-span-3 bg-slate-900/30 border border-slate-800 rounded-2xl p-4 flex flex-col overflow-hidden h-full">
                <div className="flex items-center justify-between mb-4 shrink-0">
                  <h3 className="font-bold text-slate-200 text-sm uppercase tracking-wider">Projects</h3>
                  <button onClick={() => setShowProjectModal(true)} className="p-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300">
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>
                
                <div className="flex-1 overflow-y-auto space-y-2">
                  {projects.map((p: any) => (
                    <div 
                      key={p.id}
                      onClick={() => setActiveProject(p)}
                      className={`p-3 border rounded-xl cursor-pointer transition-all ${
                        activeProject?.id === p.id ? "bg-slate-800/80 border-violet-500/40" : "bg-slate-900/40 border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      <h4 className="text-sm font-semibold text-slate-200">{p.name}</h4>
                      <p className="text-[10px] text-slate-500 mt-1 line-clamp-2">{p.description || "No description"}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Chat interaction center */}
              <div className="lg:col-span-5 bg-slate-900/30 border border-slate-800 rounded-2xl flex flex-col overflow-hidden h-full">
                <div className="p-4 border-b border-slate-800 shrink-0 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-violet-400" />
                    <span className="font-semibold text-sm text-slate-200">Agentic Research Chat</span>
                  </div>
                </div>

                {/* Message display thread */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messages.map((msg, index) => (
                    <div key={msg.id || index} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
                      <div className={`max-w-[85%] rounded-2xl p-3 border text-xs leading-relaxed ${
                        msg.role === "user" ? "bg-violet-600 border-violet-500/40 text-white rounded-tr-none" : "bg-slate-900/60 border-slate-800 text-slate-300 rounded-tl-none"
                      }`}>
                        {msg.content}
                        
                        {/* Inline Citations tag lists */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-3 pt-2 border-t border-slate-850">
                            {msg.citations.map((cite: any, citeIdx: number) => (
                              <button 
                                key={citeIdx}
                                onClick={() => setActiveCitation(cite)}
                                className="flex items-center gap-1 px-1.5 py-0.5 bg-slate-800 border border-slate-700 hover:border-violet-500/40 rounded text-[9px] text-slate-400 hover:text-slate-200 transition-colors"
                              >
                                <Bookmark className="w-2.5 h-2.5 text-violet-400" />
                                <span>[{citeIdx + 1}] {cite.source}</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      {/* Metric Tag info */}
                      {msg.role === "assistant" && msg.eval_metrics && (
                        <div className="flex gap-2 text-[8px] text-slate-500 mt-1 pl-2">
                          <span>Faithfulness: {(msg.eval_metrics.faithfulness * 100).toFixed(0)}%</span>
                          <span>•</span>
                          <span>Latency: {msg.eval_metrics.latency.toFixed(2)}s</span>
                        </div>
                      )}
                    </div>
                  ))}

                  {messages.length === 0 && !chatLoading && (
                    <div className="flex flex-col items-center justify-center h-full text-center p-6 my-auto">
                      <Brain className="w-10 h-10 text-violet-500/40 mb-3 animate-pulse" />
                      <h4 className="text-xs font-semibold text-slate-300">Research Project Assistant</h4>
                      <p className="text-[10px] text-slate-500 mt-1 max-w-[200px]">
                        Ask queries about papers, GitHub repos, or documents loaded in this workspace.
                      </p>
                    </div>
                  )}
                  
                  {chatLoading && (
                    <div className="flex items-center gap-2 text-xs text-slate-500 pl-2">
                      <Loader2 className="w-4 h-4 animate-spin text-violet-400" />
                      <span>Planner orchestrating specialized agents...</span>
                    </div>
                  )}
                </div>

                {/* Input query field */}
                <div className="p-3 border-t border-slate-800 shrink-0 bg-slate-950/20">
                  <div className="relative">
                    <input 
                      type="text" 
                      value={queryInput}
                      onChange={(e) => setQueryInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleSendQuery()}
                      placeholder="Ask your knowledge base (e.g. Compare ViT and CNN)..."
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-4 pr-10 py-2.5 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-violet-500"
                    />
                    <button 
                      onClick={handleSendQuery}
                      className="absolute right-2 top-2 z-10 cursor-pointer p-1.5 bg-violet-600 hover:bg-violet-500 rounded-lg text-white transition-colors"
                    >
                      <Send className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Context checklist details & Citation visualizer */}
              <div className="lg:col-span-4 bg-slate-900/30 border border-slate-800 rounded-2xl p-4 flex flex-col overflow-hidden h-full">
                
                {/* Bookmarks, Tasks, Citations tabs */}
                <div className="flex border-b border-slate-800 pb-3 mb-4 shrink-0 justify-between items-center">
                  <h3 className="font-bold text-slate-200 text-sm uppercase tracking-wider">Project Context</h3>
                </div>

                <div className="flex-1 overflow-y-auto space-y-6">
                  
                  {/* Selected Citation viewer */}
                  {activeCitation && (
                    <div className="bg-violet-950/15 border border-violet-500/25 rounded-xl p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-violet-400 font-bold uppercase tracking-wide">Citation Source Detail</span>
                        <button onClick={() => setActiveCitation(null)} className="p-0.5 hover:bg-slate-800 rounded text-slate-500">
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                      <h5 className="text-xs font-semibold text-slate-200">{activeCitation.source}</h5>
                      <blockquote className="text-[10px] text-slate-400 italic bg-slate-950/40 p-2.5 rounded-lg border-l-2 border-violet-500">
                        "{activeCitation.text_snippet}"
                      </blockquote>
                    </div>
                  )}

                  {/* Tasks TODO List */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-850 pb-1">
                      <span className="text-xs text-slate-400 font-semibold uppercase">Project Checklist</span>
                      <span className="text-[10px] text-slate-500">Tasks</span>
                    </div>

                    <div className="space-y-1.5 max-h-48 overflow-y-auto">
                      {tasks.map((task: any) => (
                        <div 
                          key={task.id} 
                          onClick={() => handleToggleTask(task)}
                          className="flex items-center gap-2.5 p-2 bg-slate-950/20 border border-slate-850 hover:border-slate-800 rounded-lg cursor-pointer transition-colors"
                        >
                          <input 
                            type="checkbox" 
                            checked={task.status === "done"}
                            onChange={() => {}} // toggled on container click
                            className="w-3.5 h-3.5 text-violet-600 bg-slate-800 border-slate-700 rounded focus:ring-violet-500 focus:ring-offset-0 focus:ring-0" 
                          />
                          <span className={`text-xs ${task.status === "done" ? "line-through text-slate-500" : "text-slate-300"}`}>{task.title}</span>
                        </div>
                      ))}
                    </div>

                    <div className="flex gap-2">
                      <input 
                        type="text" 
                        value={newTaskTitle}
                        onChange={(e) => setNewTaskTitle(e.target.value)}
                        placeholder="Add task item..."
                        className="flex-1 bg-slate-850 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 outline-none"
                      />
                      <button onClick={handleAddTask} className="p-2 bg-violet-600 hover:bg-violet-500 rounded-lg text-white">
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Bookmarks */}
                  <div className="space-y-2">
                    <span className="text-xs text-slate-400 font-semibold uppercase block border-b border-slate-850 pb-1">Bookmarked Sources</span>
                    <div className="space-y-1 text-xs">
                      {documents.slice(0, 3).map((d: any) => (
                        <div key={d.id} className="flex items-center gap-2 p-1.5 hover:bg-slate-900 rounded-md text-slate-300">
                          <Bookmark className="w-3.5 h-3.5 text-violet-400 shrink-0" />
                          <span className="truncate">{d.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              </div>

            </div>
          )}

          {/* TAB 4: PERSISTENT FACTS MEMORY */}
          {activeTab === "memory" && (
            <div className="max-w-3xl mx-auto space-y-6">
              <div>
                <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-slate-100 to-slate-300 bg-clip-text text-transparent">AI Long-term Facts Memory</h1>
                <p className="text-sm text-slate-400">Add persistent preferences or habits to guide future query responses (e.g. Always use FastAPI code, write math in LaTeX).</p>
              </div>

              {/* Facts list */}
              <div className="bg-slate-900/30 border border-slate-800 rounded-2xl p-5 space-y-4">
                <div className="space-y-2">
                  {facts.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-xs">
                      No facts recorded. Add a new fact below!
                    </div>
                  ) : (
                    facts.map((fact: any) => (
                      <div key={fact.id} className="flex items-center justify-between p-3.5 bg-slate-950/40 border border-slate-850 hover:border-slate-800 rounded-xl transition-all">
                        <div className="flex items-center gap-3">
                          <div className="w-2 h-2 rounded-full bg-violet-400 shrink-0" />
                          <span className="text-xs text-slate-300">{fact.fact_text}</span>
                        </div>
                        <button 
                          onClick={() => handleDeleteFact(fact.id)}
                          className="p-1 rounded-md text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                <div className="flex gap-3 border-t border-slate-800/80 pt-4">
                  <input 
                    type="text" 
                    value={newFact}
                    onChange={(e) => setNewFact(e.target.value)}
                    placeholder="Enter context fact (e.g., Target code must use TypeScript type interfaces)..."
                    className="flex-1 bg-slate-850 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-300 outline-none focus:ring-1 focus:ring-violet-500"
                  />
                  <button 
                    onClick={handleAddFact}
                    className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-xl text-xs font-semibold text-white transition-colors"
                  >
                    Add Fact
                  </button>
                </div>
              </div>

            </div>
          )}

        </div>
      </main>

      {/* --- MODALS --- */}

      {/* 1. Workspace Modal */}
      {showWorkspaceModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-100">Create Workspace</h3>
            <input 
              type="text" 
              value={newWorkspaceName}
              onChange={(e) => setNewWorkspaceName(e.target.value)}
              placeholder="e.g., College Notes, Public Safety Project"
              className="w-full bg-slate-850 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-violet-500"
            />
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowWorkspaceModal(false)} className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors">
                Cancel
              </button>
              <button onClick={handleCreateWorkspace} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-xl text-xs font-semibold text-white transition-colors">
                Create Workspace
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Folder Modal */}
      {showFolderModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-100">Create Folder</h3>
            <input 
              type="text" 
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="Folder name (e.g., Vision Transformers)"
              className="w-full bg-slate-850 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-violet-500"
            />
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowFolderModal(false)} className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors">
                Cancel
              </button>
              <button onClick={handleCreateFolder} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-xl text-xs font-semibold text-white transition-colors">
                Create Folder
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Project Modal */}
      {showProjectModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-100">Create Project</h3>
            <div className="space-y-3">
              <input 
                type="text" 
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="Project name (e.g., Scene Prediction)"
                className="w-full bg-slate-850 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-violet-500"
              />
              <textarea
                value={newProjectDesc}
                onChange={(e) => setNewProjectDesc(e.target.value)}
                placeholder="Brief description..."
                className="w-full h-24 bg-slate-850 border border-slate-700 rounded-xl p-3.5 text-xs text-slate-200 outline-none resize-none focus:ring-1 focus:ring-violet-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowProjectModal(false)} className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors">
                Cancel
              </button>
              <button onClick={handleCreateProject} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-xl text-xs font-semibold text-white transition-colors">
                Create Project
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
