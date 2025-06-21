"""Cost tracking infrastructure for AI agent calls and other billable operations."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CostCategory(StrEnum):
  """Categories of costs that can be tracked."""

  AGENT = "agent"
  TTS = "tts"
  API = "api"


@dataclass
class AgentCost:
  """Record of cost for a single agent call."""

  agent_name: str
  model_name: str
  input_tokens: int
  output_tokens: int
  cost_usd: Decimal
  timestamp: datetime
  duration_seconds: float | None = None
  retry_count: int = 0
  category: CostCategory = CostCategory.AGENT
  metadata: dict[str, Any] = field(default_factory=dict)
  cached_tokens: int = 0
  """Number of tokens that were served from cache (charged at reduced rate)."""


@dataclass
class UsageMetrics:
  """Comprehensive usage metrics for the workflow."""

  total_cost_usd: Decimal = Decimal("0.00")
  total_input_tokens: int = 0
  total_output_tokens: int = 0
  total_cached_tokens: int = 0
  total_duration_seconds: float = 0.0
  agent_call_count: int = 0
  tts_call_count: int = 0
  api_call_count: int = 0
  cache_hits: int = 0
  cache_misses: int = 0
  retry_count: int = 0
  failure_count: int = 0
  costs_by_category: dict[str, Decimal] = field(default_factory=dict)
  costs_by_agent: dict[str, Decimal] = field(default_factory=dict)
  costs_by_model: dict[str, Decimal] = field(default_factory=dict)
  performance_by_agent: dict[str, dict[str, float]] = field(default_factory=dict)


def calculate_agent_cost(
  model_name: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0
) -> Decimal:
  """Calculate the cost of an agent call based on model and token usage.

  Args:
      model_name: The Gemini model used
      input_tokens: Number of input tokens used
      output_tokens: Number of output tokens used
      cached_tokens: Number of tokens served from cache (charged at 75% discount)

  Returns:
      Total cost in USD as Decimal for precise calculations
  """
  # Pricing per 1M tokens as of June 2025
  # Source: https://ai.google.dev/gemini-api/docs/pricing
  pricing = {
    # Gemini 2.5 Flash models (Updated pricing as of June 2025)
    "gemini-2.5-flash": {
      "input_per_1m": Decimal("0.30"),  # text/image/video
      "output_per_1m": Decimal("2.50"),
      "cache_per_1m": Decimal("0.075"),  # context caching
    },
    "gemini-2.5-flash-preview": {
      "input_per_1m": Decimal("0.30"),  # text/image/video
      "output_per_1m": Decimal("2.50"),
      "cache_per_1m": Decimal("0.075"),  # context caching
    },
    # Gemini 2.5 Flash-Lite models
    "gemini-2.5-flash-lite": {
      "input_per_1m": Decimal("0.10"),  # text/image/video
      "output_per_1m": Decimal("0.40"),
      "cache_per_1m": Decimal("0.025"),  # context caching
    },
    # Gemini 2.5 Pro models
    "gemini-2.5-pro": {
      "input_per_1m": Decimal("1.25"),  # ≤200k tokens
      "input_per_1m_long": Decimal("2.50"),  # >200k tokens
      "output_per_1m": Decimal("10.00"),  # ≤200k tokens
      "output_per_1m_long": Decimal("15.00"),  # >200k tokens
      "cache_per_1m": Decimal("0.31"),  # ≤200k tokens
      "cache_per_1m_long": Decimal("0.625"),  # >200k tokens
    },
    "gemini-2.5-pro-preview": {
      "input_per_1m": Decimal("1.25"),
      "input_per_1m_long": Decimal("2.50"),
      "output_per_1m": Decimal("10.00"),
      "output_per_1m_long": Decimal("15.00"),
      "cache_per_1m": Decimal("0.31"),
      "cache_per_1m_long": Decimal("0.625"),
    },
    # Gemini 2.0 Flash models (keeping existing rates - need to verify)
    "gemini-2.0-flash": {
      "input_per_1m": Decimal("0.10"),
      "output_per_1m": Decimal("0.40"),
    },
    "gemini-2.0-flash-lite": {
      "input_per_1m": Decimal("0.075"),
      "output_per_1m": Decimal("0.30"),
    },
    # TTS models (keeping existing rates - need to verify)
    "gemini-2.5-flash-preview-tts": {
      "input_per_1m": Decimal("0.50"),
      "output_per_1m": Decimal("10.00"),
    },
    "gemini-2.5-pro-preview-tts": {
      "input_per_1m": Decimal("1.00"),
      "output_per_1m": Decimal("20.00"),
    },
  }

  # Normalize model name and handle version-specific names
  model_key = model_name.lower()
  # Handle versioned model names like "gemini-2.5-flash-preview-05-20"
  for key in pricing:
    if model_key.startswith(key):
      model_key = key
      break

  if model_key not in pricing:
    logger.warning(
      f"Unknown model for pricing: {model_name}, using Gemini 2.5 Flash pricing as fallback"
    )
    model_key = "gemini-2.5-flash"

  rates = pricing[model_key]

  # Determine which rates to use based on token counts
  if "input_per_1m_long" in rates and input_tokens > 200_000:
    input_rate = rates["input_per_1m_long"]
  else:
    input_rate = rates["input_per_1m"]

  if "output_per_1m_long" in rates and output_tokens > 200_000:
    output_rate = rates["output_per_1m_long"]
  else:
    output_rate = rates["output_per_1m"]

  # Calculate costs using Decimal for precision
  # Per Google Gemini API: promptTokenCount includes cached tokens in total count
  # So we need to calculate: (total_input - cached) at full price + cached at cache rate
  regular_input_tokens = max(0, input_tokens - cached_tokens)
  regular_input_cost = (Decimal(regular_input_tokens) / Decimal("1000000")) * input_rate

  # Cached tokens use specific cache pricing rates
  if cached_tokens > 0 and "cache_per_1m" in rates:
    # Determine cache rate based on token count for Pro models
    if "cache_per_1m_long" in rates and cached_tokens > 200_000:
      cache_rate = rates["cache_per_1m_long"]
    else:
      cache_rate = rates["cache_per_1m"]
    cached_input_cost = (Decimal(cached_tokens) / Decimal("1000000")) * cache_rate
  else:
    # Fallback to old 75% discount method if no cache pricing available
    cached_input_cost = (Decimal(cached_tokens) / Decimal("1000000")) * input_rate * Decimal("0.25")

  # Output tokens are always at full price
  output_cost = (Decimal(output_tokens) / Decimal("1000000")) * output_rate

  total_cost = regular_input_cost + cached_input_cost + output_cost

  # Calculate cache savings for logging
  if cached_tokens > 0:
    if "cache_per_1m" in rates:
      # Use specific cache rate
      effective_cache_rate = (
        rates["cache_per_1m_long"]
        if "cache_per_1m_long" in rates and cached_tokens > 200_000
        else rates["cache_per_1m"]
      )
      cache_savings = (Decimal(cached_tokens) / Decimal("1000000")) * (
        input_rate - effective_cache_rate
      )
    else:
      # Use old 75% discount method
      cache_savings = (Decimal(cached_tokens) / Decimal("1000000")) * input_rate * Decimal("0.75")
  else:
    cache_savings = Decimal("0")

  logger.debug(
    "Agent cost calculation",
    model=model_name,
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    cached_tokens=cached_tokens,
    regular_input_cost_usd=regular_input_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
    cached_input_cost_usd=cached_input_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
    output_cost_usd=output_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
    total_cost_usd=total_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
    cache_savings_usd=cache_savings.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
  )

  return total_cost


class CostTracker:
  """Accumulates and analyzes costs across the workflow."""

  def __init__(self):
    self.costs: list[AgentCost] = []

  def add_cost(self, cost: AgentCost) -> None:
    """Add a cost record to the tracker."""
    self.costs.append(cost)
    logger.debug(
      f"Cost tracked: {cost.agent_name} - ${cost.cost_usd:.4f}",
      agent=cost.agent_name,
      model=cost.model_name,
      cost_usd=cost.cost_usd,
      tokens_in=cost.input_tokens,
      tokens_out=cost.output_tokens,
    )

  def get_metrics(self) -> UsageMetrics:
    """Calculate comprehensive usage metrics."""
    metrics = UsageMetrics()

    for cost in self.costs:
      # Update totals
      metrics.total_cost_usd += cost.cost_usd
      metrics.total_input_tokens += cost.input_tokens
      metrics.total_output_tokens += cost.output_tokens
      metrics.total_cached_tokens += cost.cached_tokens
      if cost.duration_seconds:
        metrics.total_duration_seconds += cost.duration_seconds

      # Count by category
      if cost.category == CostCategory.AGENT:
        metrics.agent_call_count += 1
      elif cost.category == CostCategory.TTS:
        metrics.tts_call_count += 1
      elif cost.category == CostCategory.API:
        metrics.api_call_count += 1

      # Track cache hits/misses
      if cost.cached_tokens > 0:
        metrics.cache_hits += 1
      else:
        metrics.cache_misses += 1

      # Accumulate retries
      metrics.retry_count += cost.retry_count

      # Cost breakdowns
      category_key = str(cost.category)
      metrics.costs_by_category[category_key] = (
        metrics.costs_by_category.get(category_key, Decimal("0.00")) + cost.cost_usd
      )

      metrics.costs_by_agent[cost.agent_name] = (
        metrics.costs_by_agent.get(cost.agent_name, Decimal("0.00")) + cost.cost_usd
      )

      metrics.costs_by_model[cost.model_name] = (
        metrics.costs_by_model.get(cost.model_name, Decimal("0.00")) + cost.cost_usd
      )

      # Performance metrics by agent
      if cost.duration_seconds and cost.category == CostCategory.AGENT:
        if cost.agent_name not in metrics.performance_by_agent:
          metrics.performance_by_agent[cost.agent_name] = {
            "total_duration": 0.0,
            "call_count": 0,
            "avg_duration": 0.0,
            "total_tokens": 0,
            "tokens_per_second": 0.0,
          }

        perf = metrics.performance_by_agent[cost.agent_name]
        perf["total_duration"] += cost.duration_seconds
        perf["call_count"] += 1
        perf["avg_duration"] = perf["total_duration"] / perf["call_count"]
        perf["total_tokens"] += cost.input_tokens + cost.output_tokens
        if perf["total_duration"] > 0:
          perf["tokens_per_second"] = perf["total_tokens"] / perf["total_duration"]

    return metrics

  def generate_report(self, include_details: bool = True) -> str:
    """Generate a human-readable cost report."""
    metrics = self.get_metrics()

    report_lines = [
      "═══════════════════════════════════════════════",
      "            COST & USAGE REPORT",
      "═══════════════════════════════════════════════",
      f"Total Cost: ${metrics.total_cost_usd.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)}",
      f"Total Tokens: {metrics.total_input_tokens:,} in / {metrics.total_output_tokens:,} out",
      f"Cached Tokens: {metrics.total_cached_tokens:,} "
      f"(hits: {metrics.cache_hits}, misses: {metrics.cache_misses})",
      f"Total Duration: {metrics.total_duration_seconds:.1f}s",
      "",
      "Call Counts:",
      f"  Agent Calls: {metrics.agent_call_count}",
      f"  TTS Calls: {metrics.tts_call_count}",
      f"  API Calls: {metrics.api_call_count}",
      f"  Total Retries: {metrics.retry_count}",
    ]

    if metrics.costs_by_category:
      report_lines.extend(["", "Costs by Category:"])
      for category, cost in sorted(metrics.costs_by_category.items()):
        report_lines.append(
          f"  {category}: ${cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)}"
        )

    if metrics.costs_by_agent and include_details:
      report_lines.extend(["", "Costs by Agent:"])
      for agent, cost in sorted(metrics.costs_by_agent.items(), key=lambda x: x[1], reverse=True):
        report_lines.append(
          f"  {agent}: ${cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)}"
        )

    if metrics.costs_by_model and include_details:
      report_lines.extend(["", "Costs by Model:"])
      for model, cost in sorted(metrics.costs_by_model.items(), key=lambda x: x[1], reverse=True):
        report_lines.append(
          f"  {model}: ${cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)}"
        )

    if metrics.performance_by_agent and include_details:
      report_lines.extend(["", "Performance by Agent:"])
      for agent, perf in sorted(metrics.performance_by_agent.items()):
        report_lines.append(
          f"  {agent}: {perf['avg_duration']:.1f}s avg, {perf['tokens_per_second']:.0f} tok/s"
        )

    report_lines.append("═══════════════════════════════════════════════")

    return "\n".join(report_lines)

  def save_to_file(self, output_path: Path) -> None:
    """Save detailed cost data to JSON file."""
    metrics = self.get_metrics()

    data = {
      "summary": {
        "total_cost_usd": float(metrics.total_cost_usd),
        "total_input_tokens": metrics.total_input_tokens,
        "total_output_tokens": metrics.total_output_tokens,
        "total_cached_tokens": metrics.total_cached_tokens,
        "total_duration_seconds": metrics.total_duration_seconds,
        "timestamp": datetime.now().isoformat(),
      },
      "metrics": {
        "agent_call_count": metrics.agent_call_count,
        "tts_call_count": metrics.tts_call_count,
        "api_call_count": metrics.api_call_count,
        "cache_hits": metrics.cache_hits,
        "cache_misses": metrics.cache_misses,
        "retry_count": metrics.retry_count,
        "failure_count": metrics.failure_count,
      },
      "costs_by_category": {k: float(v) for k, v in metrics.costs_by_category.items()},
      "costs_by_agent": {k: float(v) for k, v in metrics.costs_by_agent.items()},
      "costs_by_model": {k: float(v) for k, v in metrics.costs_by_model.items()},
      "performance_by_agent": metrics.performance_by_agent,
      "detailed_costs": [
        {
          "agent_name": cost.agent_name,
          "model_name": cost.model_name,
          "input_tokens": cost.input_tokens,
          "output_tokens": cost.output_tokens,
          "cached_tokens": cost.cached_tokens,
          "cost_usd": float(cost.cost_usd),
          "timestamp": cost.timestamp.isoformat(),
          "duration_seconds": cost.duration_seconds,
          "retry_count": cost.retry_count,
          "category": cost.category,
          "metadata": cost.metadata,
        }
        for cost in self.costs
      ],
    }

    with open(output_path, "w") as f:
      json.dump(data, f, indent=2)

    logger.info(f"Cost data saved to {output_path}")
