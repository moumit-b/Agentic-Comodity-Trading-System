"""MCP Router - Intelligent routing with learning capabilities."""

from typing import List, Optional, Dict, Any
from models.performance import QueryType
from .mcp_monitor import MCPMonitor


class MCPRouter:
    """
    Intelligent router for MCP servers.
    Routes queries to optimal MCP based on learned performance patterns.
    Implements bidirectional learning (Novel Feature 1).
    """

    def __init__(self, monitor: MCPMonitor):
        """
        Initialize the MCP router.

        Args:
            monitor: MCP monitor for performance feedback
        """
        self.monitor = monitor
        self.available_mcps: Dict[str, Dict[str, Any]] = {}

        # Manual routing rules (can be overridden by learning)
        self.static_routes: Dict[str, List[str]] = {
            "chemical": ["PubChem", "BioMCP"],
            "clinical": ["ClinicalTrials", "BioMCP"],
            "literature": ["Literature", "BioMCP"],
            "gene": ["BioMCP", "WebKnowledge"],
            "protein": ["BioMCP", "WebKnowledge"],
        }

    def register_mcp(self, mcp_name: str, capabilities: List[str], metadata: Dict[str, Any] = None):
        """Register an MCP server with its capabilities."""
        self.available_mcps[mcp_name] = {
            "capabilities": capabilities,
            "metadata": metadata or {},
        }
        self.monitor.register_mcp(mcp_name)

    def route_query(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        preferred_mcp: Optional[str] = None,
    ) -> str:
        """
        Route a query to the best MCP server.

        Args:
            query: The query string
            query_type: Optional pre-classified query type
            preferred_mcp: Optional preference from agent (agent->MCP learning)

        Returns:
            Name of the MCP to route to
        """
        # If preferred MCP specified and available, use it
        if preferred_mcp and preferred_mcp in self.available_mcps:
            return preferred_mcp

        # Classify query type if not provided
        if query_type is None:
            query_type = self.monitor._classify_query_type(query)

        # Try to get best MCP from learned performance
        best_mcp = self.monitor.get_best_mcp_for_query_type(query_type)

        # If we have learned performance data, use it
        if best_mcp and best_mcp in self.available_mcps:
            # Check if we should use fallback due to poor performance
            if not self.monitor.should_use_fallback(best_mcp):
                return best_mcp

        # Fall back to static routing rules
        route_key = self._query_type_to_route_key(query_type)
        if route_key in self.static_routes:
            for mcp in self.static_routes[route_key]:
                if mcp in self.available_mcps:
                    return mcp

        # Last resort: return first available MCP
        if self.available_mcps:
            return list(self.available_mcps.keys())[0]

        raise ValueError("No MCP servers available for routing")

    def _query_type_to_route_key(self, query_type: QueryType) -> str:
        """Convert query type to static route key."""
        mapping = {
            QueryType.CHEMICAL_SEARCH: "chemical",
            QueryType.INHIBITOR_SEARCH: "chemical",
            QueryType.CLINICAL_TRIAL: "clinical",
            QueryType.LITERATURE_SEARCH: "literature",
            QueryType.GENE_LOOKUP: "gene",
            QueryType.PROTEIN_INFO: "protein",
            QueryType.GENERAL: "chemical",  # Default to chemical
        }
        return mapping.get(query_type, "chemical")

    def get_fallback_mcps(self, primary_mcp: str, query_type: QueryType) -> List[str]:
        """
        Get list of fallback MCPs if primary fails.

        Args:
            primary_mcp: The primary MCP that might fail
            query_type: Type of query

        Returns:
            List of fallback MCP names in priority order
        """
        route_key = self._query_type_to_route_key(query_type)
        fallbacks = []

        if route_key in self.static_routes:
            for mcp in self.static_routes[route_key]:
                if mcp != primary_mcp and mcp in self.available_mcps:
                    fallbacks.append(mcp)

        # Add any other available MCPs as last resort
        for mcp in self.available_mcps:
            if mcp not in fallbacks and mcp != primary_mcp:
                fallbacks.append(mcp)

        return fallbacks

    def get_routing_insights(self) -> Dict[str, Any]:
        """
        Get insights about routing decisions.
        This data helps agents learn optimal MCP usage.
        """
        return {
            "available_mcps": list(self.available_mcps.keys()),
            "static_routes": self.static_routes,
            "learned_preferences": self.monitor.get_performance_insights()["query_type_recommendations"],
        }
