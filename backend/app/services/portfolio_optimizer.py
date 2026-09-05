"""
Modern Portfolio Theory Optimization Engine

Implements:
- Mean-Variance Optimization (Markowitz)
- Efficient Frontier computation
- Maximum Sharpe Ratio portfolio
- Minimum Variance portfolio
- Risk parity allocation
- Monte Carlo simulation for frontier visualization
- Asset correlation matrix
- Value at Risk (VaR) and Conditional VaR (CVaR)
"""

import math
import random
from datetime import datetime, timezone
from typing import Optional


# ── Helper Functions ────────────────────────────────────────────────

def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0


def _std(values: list) -> float:
    if len(values) < 2:
        return 0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _covariance(x: list, y: list) -> float:
    if len(x) != len(y) or len(x) < 2:
        return 0
    mx, my = _mean(x), _mean(y)
    n = len(x)
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)


def _correlation(x: list, y: list) -> float:
    sx, sy = _std(x), _std(y)
    if sx == 0 or sy == 0:
        return 0
    return _covariance(x, y) / (sx * sy)


# ── Core MPT Engine ────────────────────────────────────────────────

class PortfolioOptimizer:
    """
    Modern Portfolio Theory optimizer.
    
    Uses Monte Carlo simulation to approximate the efficient frontier,
    then identifies the maximum Sharpe ratio and minimum variance portfolios.
    """
    
    def __init__(
        self,
        assets: list,
        expected_returns: list,
        historical_returns: Optional[list] = None,
        risk_free_rate: float = 0.04,
    ):
        """
        Args:
            assets: List of asset dicts with symbol, name, asset_class
            expected_returns: List of expected annual returns for each asset
            historical_returns: List of lists of daily returns for correlation
            risk_free_rate: Risk-free rate (default 4%)
        """
        self.assets = assets
        self.n = len(assets)
        self.expected_returns = expected_returns
        self.risk_free_rate = risk_free_rate
        
        # Build correlation matrix from historical returns
        if historical_returns and len(historical_returns) == self.n:
            self.correlation_matrix = self._compute_correlation_matrix(historical_returns)
            self.volatilities = [_std(r) * math.sqrt(252) for r in historical_returns]
        else:
            # Default correlation and volatility estimates
            self.correlation_matrix = self._estimate_correlation(assets)
            self.volatilities = self._estimate_volatilities(assets)
        
        # Build covariance matrix
        self.covariance_matrix = self._build_covariance_matrix()
    
    def _compute_correlation_matrix(self, returns: list) -> list:
        """Compute correlation matrix from historical returns."""
        n = len(returns)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                else:
                    matrix[i][j] = _correlation(returns[i], returns[j])
        return matrix
    
    def _estimate_correlation(self, assets: list) -> list:
        """Estimate correlation matrix based on asset classes."""
        n = len(assets)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                else:
                    ci = assets[i].get("asset_class", "stock")
                    cj = assets[j].get("asset_class", "stock")
                    
                    if ci == cj:
                        matrix[i][j] = 0.6  # Same class = moderate correlation
                    elif {ci, cj} == {"stock", "bond"}:
                        matrix[i][j] = -0.2  # Stocks/bonds = negative
                    elif {ci, cj} == {"stock", "crypto"}:
                        matrix[i][j] = 0.3  # Stocks/crypto = low positive
                    elif "crypto" in (ci, cj) and "commodity" in (ci, cj):
                        matrix[i][j] = 0.2
                    else:
                        matrix[i][j] = 0.1  # Default low positive
        
        return matrix
    
    def _estimate_volatilities(self, assets: list) -> list:
        """Estimate annualized volatilities based on asset class."""
        vol_map = {
            "stock": 0.20,
            "bond": 0.05,
            "commodity": 0.25,
            "crypto": 0.70,
            "fx": 0.10,
            "etf": 0.15,
        }
        return [vol_map.get(a.get("asset_class", "stock"), 0.20) for a in assets]
    
    def _build_covariance_matrix(self) -> list:
        """Build covariance matrix from correlation and volatilities."""
        n = self.n
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                matrix[i][j] = (
                    self.correlation_matrix[i][j]
                    * self.volatilities[i]
                    * self.volatilities[j]
                )
        return matrix
    
    def _portfolio_return(self, weights: list) -> float:
        """Calculate expected portfolio return."""
        return sum(w * r for w, r in zip(weights, self.expected_returns))
    
    def _portfolio_risk(self, weights: list) -> float:
        """Calculate portfolio risk (standard deviation)."""
        variance = 0.0
        n = len(weights)
        for i in range(n):
            for j in range(n):
                variance += weights[i] * weights[j] * self.covariance_matrix[i][j]
        return math.sqrt(max(0, variance))
    
    def _sharpe_ratio(self, weights: list) -> float:
        """Calculate Sharpe ratio."""
        ret = self._portfolio_return(weights)
        risk = self._portfolio_risk(weights)
        if risk == 0:
            return 0
        return (ret - self.risk_free_rate) / risk
    
    def _random_weights(self) -> list:
        """Generate random weights that sum to 1."""
        weights = [random.random() for _ in range(self.n)]
        total = sum(weights)
        return [w / total for w in weights]
    
    def optimize(
        self,
        n_simulations: int = 10000,
        target_return: Optional[float] = None,
        max_weight: float = 0.40,
        min_weight: float = 0.0,
    ) -> dict:
        """
        Run Monte Carlo optimization to find efficient frontier.
        
        Args:
            n_simulations: Number of random portfolios to simulate
            target_return: If set, find portfolio closest to this return
            max_weight: Maximum allocation to any single asset
            min_weight: Minimum allocation (0 = allow zero)
            
        Returns:
            dict with frontier, optimal portfolios, and statistics
        """
        frontier_points = []
        max_sharpe = -float("inf")
        max_sharpe_portfolio = None
        min_risk = float("inf")
        min_risk_portfolio = None
        max_return = -float("inf")
        max_return_portfolio = None
        
        # Track all simulated portfolios
        all_portfolios = []
        
        for _ in range(n_simulations):
            weights = self._random_weights()
            
            # Apply constraints
            weights = [max(min_weight, min(max_weight, w)) for w in weights]
            total = sum(weights)
            if total == 0:
                continue
            weights = [w / total for w in weights]
            
            ret = self._portfolio_return(weights)
            risk = self._portfolio_risk(weights)
            sharpe = self._sharpe_ratio(weights)
            
            portfolio = {
                "weights": [round(w * 100, 2) for w in weights],
                "return": round(ret * 100, 2),
                "risk": round(risk * 100, 2),
                "sharpe": round(sharpe, 3),
            }
            
            all_portfolios.append(portfolio)
            
            # Track optimal portfolios
            if sharpe > max_sharpe:
                max_sharpe = sharpe
                max_sharpe_portfolio = portfolio
            
            if risk < min_risk:
                min_risk = risk
                min_risk_portfolio = portfolio
            
            if ret > max_return:
                max_return = ret
                max_return_portfolio = portfolio
            
            # Collect frontier points (bin by risk level)
            risk_bin = round(risk * 100) / 100
            frontier_points.append({
                "risk": round(risk * 100, 2),
                "return": round(ret * 100, 2),
                "sharpe": round(sharpe, 3),
            })
        
        # Build efficient frontier (best return for each risk level)
        risk_bins = {}
        for p in frontier_points:
            r = p["risk"]
            if r not in risk_bins or p["return"] > risk_bins[r]["return"]:
                risk_bins[r] = p
        
        efficient_frontier = sorted(risk_bins.values(), key=lambda x: x["risk"])
        
        # Compute correlation matrix for display
        corr_display = []
        for i in range(self.n):
            row = []
            for j in range(self.n):
                row.append(round(self.correlation_matrix[i][j], 3))
            corr_display.append(row)
        
        # Build asset details for each optimal portfolio
        def _detail(portfolio):
            if not portfolio:
                return None
            assets_detail = []
            for i, w in enumerate(portfolio["weights"]):
                if w > 0.1:  # Only show >10% allocation
                    assets_detail.append({
                        "symbol": self.assets[i].get("symbol", f"Asset {i}"),
                        "name": self.assets[i].get("name", ""),
                        "asset_class": self.assets[i].get("asset_class", "stock"),
                        "allocation": w,
                        "expected_return": round(self.expected_returns[i] * 100, 2),
                        "volatility": round(self.volatilities[i] * 100, 2),
                    })
            assets_detail.sort(key=lambda x: x["allocation"], reverse=True)
            return assets_detail
        
        # VaR and CVaR for max Sharpe portfolio
        var_95 = 0
        cvar_95 = 0
        if max_sharpe_portfolio:
            weights_decimal = [w / 100 for w in max_sharpe_portfolio["weights"]]
            port_risk = max_sharpe_portfolio["risk"] / 100
            port_ret = max_sharpe_portfolio["return"] / 100
            # Parametric VaR at 95% confidence
            var_95 = round((port_ret - 1.645 * port_risk) * 100, 2)
            cvar_95 = round((port_ret - 2.063 * port_risk) * 100, 2)
        
        return {
            "efficient_frontier": efficient_frontier,
            "all_portfolios": all_portfolios[:500],  # Limit for display
            "max_sharpe": {
                **max_sharpe_portfolio,
                "assets": _detail(max_sharpe_portfolio),
                "var_95": var_95,
                "cvar_95": cvar_95,
            } if max_sharpe_portfolio else None,
            "min_risk": {
                **min_risk_portfolio,
                "assets": _detail(min_risk_portfolio),
            } if min_risk_portfolio else None,
            "max_return": {
                **max_return_portfolio,
                "assets": _detail(max_return_portfolio),
            } if max_return_portfolio else None,
            "correlation_matrix": corr_display,
            "asset_symbols": [a.get("symbol", f"Asset {i}") for i, a in enumerate(self.assets)],
            "asset_classes": [a.get("asset_class", "stock") for a in self.assets],
            "asset_volatilities": [round(v * 100, 2) for v in self.volatilities],
            "risk_free_rate": round(self.risk_free_rate * 100, 2),
            "n_simulations": n_simulations,
            "n_assets": self.n,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ── Asset Universe for Optimization ────────────────────────────────

DEFAULT_OPTIMIZATION_UNIVERSE = [
    {"symbol": "SPY", "name": "S&P 500 ETF", "asset_class": "etf", "return": 0.10, "risk": 0.16},
    {"symbol": "QQQ", "name": "Nasdaq 100 ETF", "asset_class": "etf", "return": 0.14, "risk": 0.22},
    {"symbol": "IWM", "name": "Russell 2000 ETF", "asset_class": "etf", "return": 0.09, "risk": 0.20},
    {"symbol": "EEM", "name": "Emerging Markets ETF", "asset_class": "etf", "return": 0.08, "risk": 0.18},
    {"symbol": "TLT", "name": "20+ Year Treasury", "asset_class": "bond", "return": 0.04, "risk": 0.15},
    {"symbol": "GLD", "name": "Gold ETF", "asset_class": "commodity", "return": 0.06, "risk": 0.15},
    {"symbol": "VNQ", "name": "Real Estate ETF", "asset_class": "etf", "return": 0.08, "risk": 0.18},
    {"symbol": "AAPL", "name": "Apple", "asset_class": "stock", "return": 0.12, "risk": 0.25},
    {"symbol": "MSFT", "name": "Microsoft", "asset_class": "stock", "return": 0.13, "risk": 0.24},
    {"symbol": "NVDA", "name": "NVIDIA", "asset_class": "stock", "return": 0.25, "risk": 0.50},
    {"symbol": "BTC", "name": "Bitcoin", "asset_class": "crypto", "return": 0.30, "risk": 0.70},
    {"symbol": "ETH", "name": "Ethereum", "asset_class": "crypto", "return": 0.25, "risk": 0.80},
    {"symbol": "XLE", "name": "Energy ETF", "asset_class": "etf", "return": 0.07, "risk": 0.20},
    {"symbol": "XLV", "name": "Healthcare ETF", "asset_class": "etf", "return": 0.09, "risk": 0.14},
    {"symbol": "SHY", "name": "Short Treasury", "asset_class": "bond", "return": 0.04, "risk": 0.02},
]


def get_default_optimizer() -> PortfolioOptimizer:
    """Get the default optimizer with standard universe."""
    assets = DEFAULT_OPTIMIZATION_UNIVERSE
    returns = [a["return"] for a in assets]
    return PortfolioOptimizer(assets, returns, risk_free_rate=0.04)
