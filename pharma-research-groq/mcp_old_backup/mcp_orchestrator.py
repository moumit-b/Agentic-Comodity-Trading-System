"""
MCP Orchestrator - Main orchestration layer for MCP servers.
Integrates monitoring, routing, and caching for intelligent MCP management.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from .mcp_monitor import MCPMonitor
from .mcp_router import MCPRouter
from .mcp_cache import MCPCache
from models.performance import QueryType
from mcp_tools import MCPToolWrapper


class MCPOrchestrator:
    """
    Main MCP orchestration layer.
    Provides intelligent routing, caching, performance tracking, and failover.
    This is the MCP layer of the dual orchestration architecture.
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 3600,
        max_retries: int = 2,
    ):
        """
        Initialize the MCP orchestrator.

        Args:
            cache_enabled: Whether to enable caching
            cache_ttl_seconds: Default cache TTL in seconds
            max_retries: Maximum number of retry attempts on failure
        """
        self.monitor = MCPMonitor()
        self.router = MCPRouter(self.monitor)
        self.cache = MCPCache(default_ttl_seconds=cache_ttl_seconds) if cache_enabled else None

        self.max_retries = max_retries
        self.mcp_wrappers: Dict[str, MCPToolWrapper] = {}

    def register_mcp_wrapper(
        self,
        mcp_name: str,
        wrapper: MCPToolWrapper,
        capabilities: List[str] = None,
    ):
        """
        Register an MCP wrapper for use by the orchestrator.

        Args:
            mcp_name: Name of the MCP server
            wrapper: MCPToolWrapper instance
            capabilities: List of capability tags (e.g., ["chemical", "compound"])
        """
        self.mcp_wrappers[mcp_name] = wrapper
        self.router.register_mcp(
            mcp_name,
            capabilities or [],
            metadata={"wrapper": wrapper}
        )

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        query_context: Optional[str] = None,
        preferred_mcp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call a tool with intelligent routing, caching, and failover.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            query_context: Optional query context for routing decisions
            preferred_mcp: Optional preferred MCP (from agent learning)

        Returns:
            Dict with 'result', 'mcp_used', 'cached', 'execution_time'
        """
        # Determine which MCP to route to
        if query_context:
            primary_mcp = self.router.route_query(
                query_context,
                preferred_mcp=preferred_mcp
            )
        elif preferred_mcp and preferred_mcp in self.mcp_wrappers:
            primary_mcp = preferred_mcp
        else:
            # Default to first available
            primary_mcp = list(self.mcp_wrappers.keys())[0] if self.mcp_wrappers else None

        if not primary_mcp:
            raise ValueError("No MCP servers available")

        # Check cache first
        if self.cache:
            cached_result = self.cache.get(primary_mcp, tool_name, arguments)
            if cached_result is not None:
                return {
                    "result": cached_result,
                    "mcp_used": primary_mcp,
                    "cached": True,
                    "execution_time": 0.0,
                }

        # Execute with retries and failover
        query_type = self.monitor._classify_query_type(query_context or "")
        fallback_mcps = self.router.get_fallback_mcps(primary_mcp, query_type)

        mcps_to_try = [primary_mcp] + fallback_mcps
        last_error = None

        for attempt_mcp in mcps_to_try[:self.max_retries + 1]:
            if attempt_mcp not in self.mcp_wrappers:
                continue

            start_time = time.time()

            try:
                # Call the MCP tool
                result = await self.mcp_wrappers[attempt_mcp].call_tool(
                    tool_name,
                    arguments
                )

                execution_time = time.time() - start_time

                # Record successful call
                self.monitor.record_call(
                    mcp_name=attempt_mcp,
                    query=query_context or tool_name,
                    success=True,
                    response_time=execution_time,
                    cache_hit=False,
                )

                # Cache the result
                if self.cache:
                    self.cache.set(attempt_mcp, tool_name, arguments, result)

                return {
                    "result": result,
                    "mcp_used": attempt_mcp,
                    "cached": False,
                    "execution_time": execution_time,
                }

            except Exception as e:
                execution_time = time.time() - start_time
                last_error = str(e)

                # Record failed call
                self.monitor.record_call(
                    mcp_name=attempt_mcp,
                    query=query_context or tool_name,
                    success=False,
                    response_time=execution_time,
                    error_message=last_error,
                    cache_hit=False,
                )

                # Continue to next fallback
                continue

        # All attempts failed
        raise Exception(f"All MCP attempts failed. Last error: {last_error}")

    def get_performance_feedback(self) -> Dict[str, Any]:
        """
        Get performance feedback for agents.
        This enables MCP -> Agent learning (bidirectional learning).
        """
        insights = self.monitor.get_performance_insights()

        # Add cache statistics
        if self.cache:
            insights["cache_stats"] = self.cache.get_stats()

        # Add routing insights
        insights["routing"] = self.router.get_routing_insights()

        return insights

    def get_mcp_recommendation(
        self,
        query_type: QueryType,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get recommendation for which MCP to use for a query type.
        Agents can call this to learn from MCP layer performance.

        Args:
            query_type: Type of query
            agent_name: Optional agent name requesting recommendation

        Returns:
            Dict with 'recommended_mcp', 'confidence', 'rationale'
        """
        best_mcp = self.monitor.get_best_mcp_for_query_type(query_type)

        if not best_mcp:
            return {
                "recommended_mcp": None,
                "confidence": 0.0,
                "rationale": "No performance data available yet",
            }

        perf = self.monitor.mcp_performance[best_mcp]
        success_rate = perf.get_success_rate_for_type(query_type)
        avg_time = perf.get_avg_time_for_type(query_type)

        rationale = (
            f"{best_mcp} has {success_rate*100:.1f}% success rate "
            f"with avg response time {avg_time:.2f}s for {query_type.value} queries"
        )

        return {
            "recommended_mcp": best_mcp,
            "confidence": success_rate,
            "rationale": rationale,
            "avg_time": avg_time,
        }

    def get_stats_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive stats for dashboard display.

        Returns:
            Dict with all statistics and metrics
        """
        stats = {
            "mcps": {},
            "overall": {
                "total_calls": 0,
                "total_successes": 0,
                "total_failures": 0,
                "cache_stats": self.cache.get_stats() if self.cache else None,
            },
            "insights": self.monitor.get_performance_insights(),
        }

        # Per-MCP stats
        for mcp_name in self.mcp_wrappers.keys():
            mcp_stats = self.monitor.get_mcp_stats(mcp_name)
            if mcp_stats:
                stats["mcps"][mcp_name] = mcp_stats
                stats["overall"]["total_calls"] += mcp_stats["total_calls"]
                stats["overall"]["total_successes"] += int(
                    mcp_stats["total_calls"] * mcp_stats["success_rate"]
                )

        stats["overall"]["total_failures"] = (
            stats["overall"]["total_calls"] - stats["overall"]["total_successes"]
        )

        if stats["overall"]["total_calls"] > 0:
            stats["overall"]["success_rate"] = (
                stats["overall"]["total_successes"] / stats["overall"]["total_calls"]
            )
        else:
            stats["overall"]["success_rate"] = 0.0

        return stats

    def cleanup(self):
        """Cleanup resources (call on shutdown)."""
        if self.cache:
            self.cache.cleanup_expired()
