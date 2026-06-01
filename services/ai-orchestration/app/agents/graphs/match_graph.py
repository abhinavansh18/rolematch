"""
LangGraph multi-agent match pipeline.

Node execution order:
  resume_analyzer → job_retriever → reranker → match_scorer → finalizer
                                  ↑
                          (parallel within)
"""
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.nodes.finalizer import finalizer_node
from app.agents.nodes.job_retriever import job_retriever_node
from app.agents.nodes.match_scorer import match_scorer_node
from app.agents.nodes.reranker import reranker_node
from app.agents.nodes.resume_analyzer import resume_analyzer_node


class MatchState(TypedDict):
    match_id: str
    user_id: str
    resume_id: str
    filters: dict
    # Populated by nodes
    resume_structured: dict | None
    resume_embedding: list[float] | None
    candidate_job_ids: list[str] | None
    ranked_jobs: list[dict] | None
    scored_jobs: list[dict] | None
    error: str | None


def build_match_graph() -> StateGraph:
    graph = StateGraph(MatchState)

    graph.add_node("resume_analyzer", resume_analyzer_node)
    graph.add_node("job_retriever",   job_retriever_node)
    graph.add_node("reranker",        reranker_node)
    graph.add_node("match_scorer",    match_scorer_node)
    graph.add_node("finalizer",       finalizer_node)

    graph.set_entry_point("resume_analyzer")
    graph.add_edge("resume_analyzer", "job_retriever")
    graph.add_edge("job_retriever",   "reranker")
    graph.add_edge("reranker",        "match_scorer")
    graph.add_edge("match_scorer",    "finalizer")
    graph.add_edge("finalizer",       END)

    return graph.compile()


# Singleton compiled graph (thread-safe, reuse across requests)
MatchGraph = build_match_graph()
