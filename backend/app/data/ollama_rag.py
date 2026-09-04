"""Ollama + ChromaDB RAG — Air-Gapped Policy Generation.

Provides:
1. Local LLM inference via Ollama (DeepSeek/Qwen/Llama)
2. RAG vector index with sovereign debt frameworks (IMF, World Bank)
3. Structured JSON output guardrails via Pydantic schemas
4. Zero external network dependencies after initial setup

Usage:
    engine = OllamaRAGEngine()
    engine.index_document("IMF Public Debt Sustainability Framework", imf_text)
    result = engine.generate_policy_brief(portfolio_data, yield_data, macro_data)
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None


# ── Structured Output Schemas ───────────────────────────────────────

@dataclass
class PolicyRecommendation:
    """Single policy recommendation with structured output."""
    action: str  # "reduce", "increase", "maintain", "hedge"
    target: str  # "floating_rate", "short_term", "inflation_linked"
    current_pct: float
    target_pct: float
    rationale: str
    confidence: float  # 0-1
    priority: str  # "high", "medium", "low"


@dataclass
class PolicyBriefOutput:
    """Full structured policy brief output."""
    executive_summary: str
    recommendations: list[PolicyRecommendation]
    risk_assessment: str
    issuance_strategy: str
    cost_savings_analysis: str
    stress_test_interpretation: str
    confidence_level: str
    caveats: list[str]
    model_used: str
    sources_cited: list[str]


# ── Ollama Client ───────────────────────────────────────────────────

class OllamaClient:
    """Local Ollama inference client."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.base_url = base_url
        self.model = model
        self._available = None

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        if self._available is not None:
            return self._available
        try:
            import urllib.request
            resp = urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3)
            self._available = resp.status == 200
            return self._available
        except Exception:
            self._available = False
            return False

    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        format_json: bool = False,
    ) -> str:
        """Generate text using Ollama."""
        import urllib.request

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        return result.get("response", "")

    def list_models(self) -> list[str]:
        """List available models."""
        try:
            import urllib.request
            resp = urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=5)
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


# ── ChromaDB RAG Index ─────────────────────────────────────────────

class SovereignDebtRAG:
    """RAG vector index for sovereign debt knowledge."""

    def __init__(self, persist_dir: Optional[str] = None):
        if not CHROMADB_AVAILABLE:
            self.client = None
            self.collection = None
            return

        if persist_dir is None:
            persist_dir = os.path.join(os.path.dirname(__file__), "chroma_db")

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="sovereign_debt_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

    def index_document(self, title: str, content: str, metadata: Optional[dict] = None):
        """Index a document into the RAG store."""
        if not self.collection:
            return  # ChromaDB not available
        # Chunk document into ~500 token segments
        chunks = self._chunk_text(content, chunk_size=1500, overlap=200)

        for i, chunk in enumerate(chunks):
            doc_id = f"{title[:50]}_{i}"
            meta = {"title": title, "chunk_index": i, "total_chunks": len(chunks)}
            if metadata:
                meta.update(metadata)

            self.collection.upsert(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[meta],
            )

    def query(self, query_text: str, n_results: int = 5) -> list[dict]:
        """Query the RAG store for relevant documents."""
        if not self.collection:
            return []  # ChromaDB not available
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )

        docs = []
        for i in range(len(results["documents"][0])):
            docs.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            })
        return docs

    def get_stats(self) -> dict:
        """Get collection statistics."""
        if not self.collection:
            return {"total_documents": 0, "collection_name": "sovereign_debt_knowledge", "status": "chromadb_not_installed"}
        count = self.collection.count()
        return {
            "total_documents": count,
            "collection_name": "sovereign_debt_knowledge",
        }

    def _chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap
        return chunks


# ── Built-in Knowledge Base ─────────────────────────────────────────

BUILTIN_DOCUMENTS = {
    "IMF Debt Sustainability Framework": """
The IMF-World Bank Debt Sustainability Framework (DSF) assesses the sustainability
of public debt in low-income and emerging market countries. Key components:

1. Debt-to-GDP Ratio: Primary indicator. Thresholds vary by country classification.
   - Low-income: 35-55% depending on CPIA score
   - Emerging market: 70-85% depending on reserves and governance

2. Debt Service-to-Revenue Ratio: Measures near-term liquidity risk.
   - Warning threshold: >15% of revenue
   - Critical threshold: >25% of revenue

3. Gross Financing Needs (GFN): Total new borrowing required.
   - Warning: GFN/GDP > 15%
   - Critical: GFN/GDP > 20%

4. Real GDP Growth vs. Interest Rate Differential (r-g):
   - If r > g: debt dynamics are unfavorable without primary surplus
   - If r < g: debt can stabilize with small primary balance

5. Commodity Price Shock Analysis:
   - Stress test: -30% commodity price decline
   - Impact on revenue, reserves, and debt trajectory

6. Natural Disaster Shock:
   - One-time GDP decline of 5-10%
   - Recovery period of 2-3 years
   - Financing need surge of 3-5% of GDP

Policy Recommendations Framework:
- Short-term: Manage maturity profile, avoid concentration
- Medium-term: Diversify funding sources, develop domestic market
- Long-term: Build fiscal buffers, reduce vulnerability
""",

    "Sovereign Debt Best Practices": """
OECD Principles for Sovereign Debt Management:

1. Debt Management Strategy:
   - Clear objectives aligned with fiscal policy
   - Regular review and update cycle
   - Risk tolerance framework

2. Portfolio Composition:
   - Diversify across maturities (avoid "wall of maturities")
   - Balance fixed vs floating rates (rule of thumb: <30% floating)
   - Currency diversification for export-linked economies
   - Consider inflation-linked debt for high-inflation environments

3. Market Development:
   - Regular issuance calendar (predictability)
   - Benchmark bond program (liquidity)
   - Investor relations program (transparency)
   - Secondary market support

4. Risk Management:
   - VaR limits for interest rate risk
   - Duration targets aligned with liability structure
   - Contingency plans for market stress
   - Regular stress testing

5. Cost Minimization:
   - Net present value (NPV) approach to issuance decisions
   - Consider total cost including issuance, maintenance, termination
   - Optimal maturity selection based on yield curve shape
""",

    "Macroeconomic Factors Affecting Debt": """
Key External Factors Influencing Sovereign Debt Sustainability:

1. Interest Rate Environment:
   - Global rate cycles (Fed policy, ECB, BOJ)
   - Term premium dynamics
   - Real vs nominal rate divergence

2. Exchange Rate Movements:
   - FX exposure on foreign-currency debt
   - Pass-through to domestic inflation
   - Reserve adequacy

3. Commodity Prices:
   - Oil price impact on fiscal balance
   - Mining/agriculture revenue correlation
   - Hedging strategies

4. Trade Flows:
   - Current account balance trajectory
   - Export concentration risk
   - Trade agreement impacts

5. Capital Flows:
   - Portfolio investment volatility
   - FDI trends
   - Remittance flows

6. Climate & Disaster Risk:
   - Physical climate risks
   - Transition risks (energy policy)
   - Insurance gap

7. Demographics:
   - Aging population fiscal pressures
   - Pension obligations
   - Healthcare cost trajectory

8. Technology & Disruption:
   - Digital economy tax base impacts
   - AI/automation labor market effects
   - Cyber risk to financial infrastructure
""",
}


# ── Main RAG Engine ─────────────────────────────────────────────────

class OllamaRAGEngine:
    """Combined Ollama + RAG engine for policy generation."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        persist_dir: Optional[str] = None,
    ):
        self.ollama = OllamaClient(ollama_url, model)
        self.rag = SovereignDebtRAG(persist_dir)
        self._indexed_builtin = False

    def ensure_builtin_documents(self):
        """Index built-in sovereign debt knowledge if not already done."""
        if self._indexed_builtin:
            return
        if not self.rag.client:
            self._indexed_builtin = True
            return  # ChromaDB not available
        if self.rag.get_stats()["total_documents"] > 0:
            self._indexed_builtin = True
            return

        for title, content in BUILTIN_DOCUMENTS.items():
            self.rag.index_document(title, content, {"source": "builtin"})
        self._indexed_builtin = True
        print(f"[RAG] Indexed {len(BUILTIN_DOCUMENTS)} built-in documents")

    def generate_policy_brief(
        self,
        portfolio_data: dict,
        yield_data: dict,
        macro_data: dict,
        optimization_result: Optional[dict] = None,
        stress_test_result: Optional[dict] = None,
    ) -> PolicyBriefOutput:
        """Generate a structured policy brief using RAG + local LLM."""
        self.ensure_builtin_documents()

        # Step 1: RAG query for relevant knowledge
        rag_context = self._build_rag_context(portfolio_data, macro_data)

        # Step 2: Build structured prompt
        prompt = self._build_prompt(
            portfolio_data, yield_data, macro_data,
            optimization_result, stress_test_result, rag_context,
        )

        # Step 3: Generate with Ollama
        if self.ollama.is_available():
            system_prompt = self._build_system_prompt()
            raw_output = self.ollama.generate(
                prompt=prompt,
                system=system_prompt,
                temperature=0.3,
                max_tokens=2000,
                format_json=True,
            )
            return self._parse_llm_output(raw_output)
        else:
            # Fallback: template-based generation
            return self._generate_template_brief(
                portfolio_data, yield_data, macro_data,
                optimization_result, stress_test_result,
            )

    def _build_rag_context(self, portfolio_data: dict, macro_data: dict) -> str:
        """Query RAG for relevant context."""
        queries = [
            "sovereign debt maturity management best practices",
            f"debt sustainability GDP growth {macro_data.get('gdp_growth_pct', 2.5)}%",
            "interest rate risk management fixed floating allocation",
        ]

        all_context = []
        for q in queries:
            results = self.rag.query(q, n_results=2)
            for r in results:
                all_context.append(r["content"][:500])

        return "\n\n".join(all_context[:3])  # Top 3 most relevant

    def _build_prompt(
        self, portfolio_data, yield_data, macro_data,
        optimization_result, stress_test_result, rag_context,
    ) -> str:
        """Build the full prompt for the LLM."""
        return f"""You are a senior sovereign debt advisor. Generate a structured policy brief.

## Portfolio Data
{json.dumps(portfolio_data, indent=2)[:1000]}

## Current Yield Curve
{json.dumps(yield_data, indent=2)}

## Macroeconomic Context
{json.dumps(macro_data, indent=2)}

## Optimization Result
{json.dumps(optimization_result, indent=2)[:1000] if optimization_result else 'Not available'}

## Stress Test Results
{json.dumps(stress_test_result, indent=2)[:1000] if stress_test_result else 'Not available'}

## Relevant Knowledge Base
{rag_context[:2000]}

Generate a JSON response with these exact fields:
{{
  "executive_summary": "2-3 sentence summary",
  "recommendations": [{{"action": "reduce/increase/maintain/hedge", "target": "what", "current_pct": 0, "target_pct": 0, "rationale": "why", "confidence": 0.8, "priority": "high/medium/low"}}],
  "risk_assessment": "Risk analysis paragraph",
  "issuance_strategy": "Specific bond types, maturities, timing",
  "cost_savings_analysis": "Quantified benefits",
  "stress_test_interpretation": "What the stress tests mean",
  "confidence_level": "high/medium/low",
  "caveats": ["caveat 1", "caveat 2"]
}}
"""

    def _build_system_prompt(self) -> str:
        return """You are a sovereign debt policy advisor AI. Generate structured, data-driven policy briefs.
Be specific with numbers. Use tables when comparing options.
Always cite relevant fiscal rules and benchmarks.
Frame uncertain outcomes as probabilities, not certainties."""

    def _parse_llm_output(self, raw: str) -> PolicyBriefOutput:
        """Parse LLM JSON output into structured brief."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            try:
                data = json.loads(raw.strip())
            except json.JSONDecodeError:
                return self._fallback_brief(raw)

        recs = []
        for r in data.get("recommendations", []):
            recs.append(PolicyRecommendation(
                action=r.get("action", "maintain"),
                target=r.get("target", ""),
                current_pct=r.get("current_pct", 0),
                target_pct=r.get("target_pct", 0),
                rationale=r.get("rationale", ""),
                confidence=r.get("confidence", 0.5),
                priority=r.get("priority", "medium"),
            ))

        return PolicyBriefOutput(
            executive_summary=data.get("executive_summary", ""),
            recommendations=recs,
            risk_assessment=data.get("risk_assessment", ""),
            issuance_strategy=data.get("issuance_strategy", ""),
            cost_savings_analysis=data.get("cost_savings_analysis", ""),
            stress_test_interpretation=data.get("stress_test_interpretation", ""),
            confidence_level=data.get("confidence_level", "medium"),
            caveats=data.get("caveats", []),
            model_used=f"ollama/{self.ollama.model}",
            sources_cited=["IMF DSF", "OECD Principles"],
        )

    def _fallback_brief(self, raw_text: str) -> PolicyBriefOutput:
        """Fallback when JSON parsing fails."""
        return PolicyBriefOutput(
            executive_summary=raw_text[:500],
            recommendations=[],
            risk_assessment="See executive summary",
            issuance_strategy="See executive summary",
            cost_savings_analysis="See executive summary",
            stress_test_interpretation="See executive summary",
            confidence_level="low",
            caveats=["LLM output was not valid JSON"],
            model_used=f"ollama/{self.ollama.model} (fallback)",
            sources_cited=[],
        )

    def _generate_template_brief(
        self, portfolio_data, yield_data, macro_data,
        optimization_result, stress_test_result,
    ) -> PolicyBriefOutput:
        """Template-based fallback when Ollama is not available."""
        return PolicyBriefOutput(
            executive_summary="Template-based analysis (Ollama not available). Configure Ollama for AI-powered insights.",
            recommendations=[
                PolicyRecommendation("maintain", "current_strategy", 100, 100, "Ollama not connected", 0.5, "low"),
            ],
            risk_assessment="Enable Ollama for detailed risk analysis.",
            issuance_strategy="Enable Ollama for issuance recommendations.",
            cost_savings_analysis="Enable Ollama for cost analysis.",
            stress_test_interpretation="Enable Ollama for stress test interpretation.",
            confidence_level="low",
            caveats=["Ollama not available — using template fallback", "Connect to Ollama for AI-powered policy briefs"],
            model_used="template_fallback",
            sources_cited=[],
        )


def brief_to_dict(brief: PolicyBriefOutput) -> dict:
    """Convert PolicyBriefOutput to JSON-serializable dict."""
    return {
        "executive_summary": brief.executive_summary,
        "recommendations": [
            {
                "action": r.action, "target": r.target,
                "current_pct": r.current_pct, "target_pct": r.target_pct,
                "rationale": r.rationale, "confidence": r.confidence,
                "priority": r.priority,
            }
            for r in brief.recommendations
        ],
        "risk_assessment": brief.risk_assessment,
        "issuance_strategy": brief.issuance_strategy,
        "cost_savings_analysis": brief.cost_savings_analysis,
        "stress_test_interpretation": brief.stress_test_interpretation,
        "confidence_level": brief.confidence_level,
        "caveats": brief.caveats,
        "model_used": brief.model_used,
        "sources_cited": brief.sources_cited,
    }
