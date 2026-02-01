"""MCP Performance Monitor - Tracks performance for bidirectional learning."""

from typing import Dict, List, Optional
from datetime import datetime
import time
from models.performance import (
    MCPPerformance,
    PerformanceMetrics,
    QueryType,
)


class MCPMonitor:
    """
    Monitors MCP server performance and provides feedback to agents.
    This enables bidirectional learning (Novel Feature 1).
    """

    def __init__(self):
        """Initialize the MCP monitor."""
        self.mcp_performance: Dict[str, MCPPerformance] = {}
        self._query_type_classifier: Optional[callable] = None

    def register_mcp(self, mcp_name: str):
        """Register a new MCP server for monitoring."""
        if mcp_name not in self.mcp_performance:
            self.mcp_performance[mcp_name] = MCPPerformance(mcp_name=mcp_name)

    def record_call(
        self,
        mcp_name: str,
        query: str,
        success: bool,
        response_time: float,
        error_message: Optional[str] = None,
        cache_hit: bool = False,
    ):
        """Record a call to an MCP server."""
        # Ensure MCP is registered
        self.register_mcp(mcp_name)

        # Classify query type
        query_type = self._classify_query_type(query)

        # Create metrics
        metrics = PerformanceMetrics(
            success=success,
            response_time_seconds=response_time,
            timestamp=datetime.now(),
            error_message=error_message,
            cache_hit=cache_hit,
        )

        # Record in performance tracker
        self.mcp_performance[mcp_name].record_call(query_type, metrics)

    def _classify_query_type(self, query: str) -> QueryType:
        """
        Classify query type based on content.
        This is a simple implementation - could be enhanced with ML.
        """
        query_lower = query.lower()

        # Chemical/compound queries
        if any(word in query_lower for word in ["molecular", "formula", "compound", "chemical", "smiles", "inchi"]):
            return QueryType.CHEMICAL_SEARCH

        # Inhibitor searches
        if "inhibitor" in query_lower or "antagonist" in query_lower:
            return QueryType.INHIBITOR_SEARCH

        # Clinical trial queries
        if any(word in query_lower for word in ["trial", "clinical", "phase", "nct"]):
            return QueryType.CLINICAL_TRIAL

        # Literature queries
        if any(word in query_lower for word in ["paper", "publication", "pubmed", "article", "research"]):
            return QueryType.LITERATURE_SEARCH

        # Gene queries
        if any(word in query_lower for word in ["gene", "chromosome", "dna", "genetic"]):
            return QueryType.GENE_LOOKUP

        # Protein queries
        if any(word in query_lower for word in ["protein", "enzyme", "receptor", "uniprot"]):
            return QueryType.PROTEIN_INFO

        return QueryType.GENERAL

    def get_best_mcp_for_query_type(self, query_type: QueryType) -> Optional[str]:
        """
        Get the MCP with best performance for a given query type.
        This is key for bidirectional learning - MCP layer teaches agents.
        """
        best_mcp = None
        best_score = -1.0

        for mcp_name, performance in self.mcp_performance.items():
            success_rate = performance.get_success_rate_for_type(query_type)
            avg_time = performance.get_avg_time_for_type(query_type)

            # Score combines success rate and speed (prefer fast + accurate)
            # Score = success_rate * (1 / (1 + avg_time))
            if avg_time > 0:
                score = success_rate * (1 / (1 + avg_time))
            else:
                score = success_rate

            if score > best_score:
                best_score = score
                best_mcp = mcp_name

        return best_mcp

    def get_performance_insights(self) -> Dict[str, any]:
        """
        Generate insights about MCP performance.
        This data is sent to agents for learning.
        """
        insights = {
            "mcp_rankings": {},
            "query_type_recommendations": {},
            "overall_stats": {
                "total_calls": sum(p.total_calls for p in self.mcp_performance.values()),
                "cache_hit_rate": self._calculate_overall_cache_hit_rate(),
            },
        }

        # Rank MCPs by overall performance
        mcp_scores = []
        for mcp_name, performance in self.mcp_performance.items():
            score = performance.success_rate * (1 / (1 + performance.avg_response_time))
            mcp_scores.append((mcp_name, score, performance))

        mcp_scores.sort(key=lambda x: x[1], reverse=True)
        insights["mcp_rankings"] = [
            {
                "mcp": name,
                "score": score,
                "success_rate": perf.success_rate,
                "avg_time": perf.avg_response_time,
            }
            for name, score, perf in mcp_scores
        ]

        # Recommendations by query type
        for query_type in QueryType:
            best_mcp = self.get_best_mcp_for_query_type(query_type)
            if best_mcp:
                insights["query_type_recommendations"][query_type.value] = {
                    "best_mcp": best_mcp,
                    "success_rate": self.mcp_performance[best_mcp].get_success_rate_for_type(query_type),
                    "avg_time": self.mcp_performance[best_mcp].get_avg_time_for_type(query_type),
                }

        return insights

    def _calculate_overall_cache_hit_rate(self) -> float:
        """Calculate overall cache hit rate across all MCPs."""
        total_calls = sum(p.total_calls for p in self.mcp_performance.values())
        if total_calls == 0:
            return 0.0

        total_cache_hits = sum(p.cache_hits for p in self.mcp_performance.values())
        return total_cache_hits / total_calls

    def get_mcp_stats(self, mcp_name: str) -> Optional[Dict[str, any]]:
        """Get detailed statistics for a specific MCP."""
        if mcp_name not in self.mcp_performance:
            return None

        perf = self.mcp_performance[mcp_name]
        return {
            "mcp_name": mcp_name,
            "total_calls": perf.total_calls,
            "success_rate": perf.success_rate,
            "avg_response_time": perf.avg_response_time,
            "cache_hit_rate": perf.cache_hit_rate,
            "performance_by_type": {
                query_type.value: {
                    "success_rate": perf.get_success_rate_for_type(query_type),
                    "avg_time": perf.get_avg_time_for_type(query_type),
                }
                for query_type in QueryType
                if query_type in perf.performance_by_type
            },
        }

    def should_use_fallback(self, mcp_name: str) -> bool:
        """
        Determine if we should use fallback MCP due to poor performance.
        Part of intelligent routing logic.
        """
        if mcp_name not in self.mcp_performance:
            return False

        perf = self.mcp_performance[mcp_name]

        # Use fallback if success rate is too low or response time too high
        if perf.total_calls >= 5:  # Only after some calls
            if perf.success_rate < 0.3:  # Less than 30% success
                return True
            if perf.avg_response_time > 10.0:  # More than 10 seconds average
                return True

        return False
