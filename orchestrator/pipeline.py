"""
Wires the Agentic RAG Pipeline using LangGraph, routing queries through specialized agents and checking citations.
"""

import time
import logging
from typing import Any, Dict, List
from config import settings
from orchestrator.state import PipelineState
from orchestrator.evaluator import QualityEvaluator
from agents.planner import PlannerAgent
from agents.reasoning import ReasoningAgent
from agents.answer_generator import AnswerGeneratorAgent
from agents.citation_checker import CitationCheckerAgent
from agents.specialized_agents import GitHubAgent, PaperAgent, CodeAgent, ReportAgent, QAAgent
from retrieval.vector_search import VectorSearchAgent
from retrieval.graph_search import GraphSearchAgent
from retrieval.web_search import WebSearchAgent
from retrieval.context_merger import ContextMerger, MergedContext
from knowledge_base.chunker import Chunk

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    logger.warning("LangGraph not found. Using custom fallback state runner.")
    HAS_LANGGRAPH = False


class Pipeline:
    def __init__(
        self,
        planner: PlannerAgent,
        vector_agent: VectorSearchAgent,
        graph_agent: GraphSearchAgent,
        web_agent: WebSearchAgent,
        merger: ContextMerger,
        reasoning_agent: ReasoningAgent,
        answer_agent: AnswerGeneratorAgent,
        citation_checker: CitationCheckerAgent,
        evaluator: QualityEvaluator
    ):
        self.planner = planner
        self.vector_agent = vector_agent
        self.graph_agent = graph_agent
        self.web_agent = web_agent
        self.merger = merger
        self.reasoning_agent = reasoning_agent
        self.answer_agent = answer_agent
        self.citation_checker = citation_checker
        self.evaluator = evaluator

        # Instantiate specialized agents
        self.github_agent = GitHubAgent()
        self.paper_agent = PaperAgent()
        self.code_agent = CodeAgent()
        self.report_agent = ReportAgent()
        self.qa_agent = QAAgent()

        # Build Graph
        if HAS_LANGGRAPH:
            self._compile_langgraph()

    def _compile_langgraph(self):
        """Compiles the LangGraph workflow structure."""
        workflow = StateGraph(PipelineState)

        # Add Nodes
        workflow.add_node("planner", self._node_planner)
        workflow.add_node("rewriter", self._node_rewriter)
        workflow.add_node("retriever", self._node_retriever)
        workflow.add_node("reasoner", self._node_reasoner)
        
        # Agent nodes
        workflow.add_node("github_agent", self._node_github_agent)
        workflow.add_node("paper_agent", self._node_paper_agent)
        workflow.add_node("code_agent", self._node_code_agent)
        workflow.add_node("report_agent", self._node_report_agent)
        workflow.add_node("qa_agent", self._node_qa_agent)
        
        # Checking & Evaluation
        workflow.add_node("citation_checker", self._node_citation_checker)
        workflow.add_node("evaluator", self._node_evaluator)

        # Set entry
        workflow.set_entry_point("planner")

        # Basic edges
        workflow.add_edge("planner", "rewriter")
        workflow.add_edge("rewriter", "retriever")
        workflow.add_edge("retriever", "reasoner")

        # Routing logic from reasoner
        def route_decision(state: PipelineState) -> str:
            if state["loop_count"] >= settings.max_retrieval_loops or state["missing_info"] is None:
                # Proceed to agent
                agent = state.get("selected_agent", "qa")
                if agent not in ["github", "paper", "code", "report", "qa"]:
                    agent = "qa"
                return f"{agent}_agent"
            return "rewriter"

        workflow.add_conditional_edges(
            "reasoner",
            route_decision,
            {
                "github_agent": "github_agent",
                "paper_agent": "paper_agent",
                "code_agent": "code_agent",
                "report_agent": "report_agent",
                "qa_agent": "qa_agent",
                "rewriter": "rewriter"
            }
        )

        # Map agent results to verification
        for agent in ["github", "paper", "code", "report", "qa"]:
            workflow.add_edge(f"{agent}_agent", "citation_checker")

        workflow.add_edge("citation_checker", "evaluator")
        workflow.add_edge("evaluator", END)

        self.compiled_graph = workflow.compile()

    # --- Node Implementations ---

    def _node_planner(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[Planner Node] Planning retrieval and agent routing...")
        plan = self.planner.plan(state["query"], workspace_facts=state["workspace_facts"])
        return {
            "plan": {
                "use_vector": plan.use_vector,
                "use_graph": plan.use_graph,
                "use_web": plan.use_web,
                "vector_query": plan.vector_query,
                "graph_query": plan.graph_query,
                "web_query": plan.web_query
            },
            "selected_agent": plan.selected_agent,
            "loop_count": 0
        }

    def _node_rewriter(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[Rewriter Node] Rewriting search query based on iteration feedback...")
        # Rewrite query if reasoning found missing information
        missing = state.get("missing_info")
        plan = state["plan"].copy()
        if missing:
            plan["vector_query"] = missing
            plan["web_query"] = missing
        return {"plan": plan}

    def _node_retriever(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[Retriever Node] Fetching documents...")
        plan = state["plan"]
        
        # Execute retrievers in parallel or series
        vector_results = []
        if plan["use_vector"]:
            vector_results = self.vector_agent.search(plan["vector_query"], workspace_id=state["workspace_id"])
            
        graph_results = []
        if plan["use_graph"]:
            graph_results = self.graph_agent.search(plan["graph_query"])
            
        web_results = []
        if plan["use_web"]:
            web_results = self.web_agent.search(plan["web_query"])

        # Merge contexts
        new_merged = self.merger.merge(state["query"], vector_results, graph_results, web_results)
        
        # Deduplicate with already retrieved chunks in previous loop iterations
        accumulated = state.get("retrieved_chunks") or []
        seen = {item["text"][:50] for item in accumulated}
        
        for item in new_merged.items:
            h = item["text"][:50]
            if h not in seen:
                seen.add(h)
                accumulated.append(item)
                
        return {
            "retrieved_chunks": accumulated,
            "loop_count": state["loop_count"] + 1
        }

    def _node_reasoner(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[Reasoner Node] Checking context sufficiency...")
        merged_context = MergedContext(items=state["retrieved_chunks"])
        res = self.reasoning_agent.evaluate(state["query"], merged_context)
        return {
            "missing_info": res.missing_info if not res.sufficient else None
        }

    # Specialized agent executors
    def _node_github_agent(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[GitHub Agent Node] Analysing codebase files...")
        merged = MergedContext(items=state["retrieved_chunks"])
        context_str = merged.to_prompt_context()
        ans = self.github_agent.call(f"Query: {state['query']}\n\nCodebase Context:\n{context_str}")
        return {"draft_answer": ans}

    def _node_paper_agent(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[Paper Agent Node] Analyzing methodologies...")
        merged = MergedContext(items=state["retrieved_chunks"])
        context_str = merged.to_prompt_context()
        ans = self.paper_agent.call(f"Query: {state['query']}\n\nPaper Context:\n{context_str}")
        return {"draft_answer": ans}

    def _node_code_agent(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[Code Agent Node] Generating source code blocks...")
        merged = MergedContext(items=state["retrieved_chunks"])
        context_str = merged.to_prompt_context()
        ans = self.code_agent.call(f"Query: {state['query']}\n\nTechnical Code Context:\n{context_str}")
        return {"draft_answer": ans}

    def _node_report_agent(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[Report Agent Node] Compiling roadmaps/reviews...")
        merged = MergedContext(items=state["retrieved_chunks"])
        context_str = merged.to_prompt_context()
        ans = self.report_agent.call(f"Query: {state['query']}\n\nSynthesis Context:\n{context_str}")
        return {"draft_answer": ans}

    def _node_qa_agent(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[QA Agent Node] Synthesizing final answer draft...")
        merged = MergedContext(items=state["retrieved_chunks"])
        ans = self.answer_agent.generate(state["query"], merged, workspace_facts=state["workspace_facts"])
        return {"draft_answer": ans}

    def _node_citation_checker(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[Citation Checker Node] Validating inline [n] citations...")
        merged = MergedContext(items=state["retrieved_chunks"])
        res = self.citation_checker.check(state["draft_answer"], merged)
        return {
            "citation_check": {
                "verified_answer": res.verified_answer,
                "flagged_claims": res.flagged_claims
            },
            "final_answer": res.verified_answer
        }

    def _node_evaluator(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("[Evaluator Node] Rating generation quality metrics...")
        merged = MergedContext(items=state["retrieved_chunks"])
        metrics = self.evaluator.evaluate(state["query"], merged.to_prompt_context(), state["final_answer"])
        return {"eval_metrics": metrics}

    # --- Custom Fallback State Machine Runner ---

    def _run_fallback(self, state: PipelineState) -> PipelineState:
        """Executes the pipeline sequentially in basic python if LangGraph is missing."""
        # 1. Planner
        planner_out = self._node_planner(state)
        state.update(planner_out)
        
        # 2. Retrieval Loop
        while state["loop_count"] < settings.max_retrieval_loops:
            # Rewrite query if needed
            rewriter_out = self._node_rewriter(state)
            state.update(rewriter_out)
            
            # Retrieve documents
            retriever_out = self._node_retriever(state)
            state.update(retriever_out)
            
            # Reason sufficiency
            reasoner_out = self._node_reasoner(state)
            state.update(reasoner_out)
            
            # If reasoning indicates context is sufficient, break early
            if state["missing_info"] is None:
                break
        
        # 3. Call Specialized Agent
        agent = state["selected_agent"]
        if agent == "github":
            agent_out = self._node_github_agent(state)
        elif agent == "paper":
            agent_out = self._node_paper_agent(state)
        elif agent == "code":
            agent_out = self._node_code_agent(state)
        elif agent == "report":
            agent_out = self._node_report_agent(state)
        else:
            agent_out = self._node_qa_agent(state)
        state.update(agent_out)

        # 4. Citation Verification
        citation_out = self._node_citation_checker(state)
        state.update(citation_out)

        # 5. Quality evaluation
        eval_out = self._node_evaluator(state)
        state.update(eval_out)

        return state

    def run(
        self,
        query: str,
        workspace_id: str,
        project_id: str | None = None,
        history: List[Dict[str, Any]] = None,
        workspace_facts: List[str] = None
    ) -> PipelineState:
        """
        Executes the agent workflow to answer a research query.
        """
        initial_state: PipelineState = {
            "query": query,
            "workspace_id": workspace_id,
            "project_id": project_id,
            "conversation_history": history or [],
            "workspace_facts": workspace_facts or [],
            "plan": {},
            "selected_agent": "qa",
            "retrieved_chunks": [],
            "missing_info": None,
            "loop_count": 0,
            "draft_answer": "",
            "citation_check": {"verified_answer": "", "flagged_claims": []},
            "final_answer": "",
            "eval_metrics": {"faithfulness": 1.0, "answer_relevancy": 1.0, "context_recall": 1.0}
        }

        start_time = time.time()
        
        if HAS_LANGGRAPH and hasattr(self, "compiled_graph"):
            logger.info("Executing workflow using LangGraph compile graph.")
            final_state = self.compiled_graph.invoke(initial_state)
        else:
            logger.info("Executing workflow using fallback state machine runner.")
            final_state = self._run_fallback(initial_state)
            
        latency = round(time.time() - start_time, 2)
        final_state["eval_metrics"]["latency"] = latency
        
        return final_state
