import React, { useState, useEffect, useCallback } from "react";
import Card from "./ui/Card";
import StatCard from "./ui/StatCard";
import Button from "./ui/Button";
import { api } from "../api";
import { WasteType, BottleneckType } from "../types";

interface ProcurementItemSummary {
  id: string;
  name: string;
  category: string;
  estimated_value: number;
  status: string;
  supplier: string | null;
}

interface WasteAlertSummary {
  id: string;
  waste_type: string;
  severity: string;
  title: string;
  monetary_impact: number;
}

interface BottleneckSummary {
  id: string;
  type: string;
  title: string;
  severity: string;
  impact_days: number;
}

interface VendorBenchmark {
  category: string;
  metric: string;
  user_value: number;
  percentile: number;
  insight: string;
}

interface ForecastSummary {
  horizon_days: number;
  projected_total: number;
  projected_savings: number;
  confidence: number;
  scenarios: Array<{
    name: string;
    probability: number;
    projected_total: number;
  }>;
}

export default function ProcurementDashboard() {
  const [requests, setRequests] = useState<ProcurementItemSummary[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [wasteAlerts, setWasteAlerts] = useState<WasteAlertSummary[]>([]);
  const [bottlenecks, setBottlenecks] = useState<BottleneckSummary[]>([]);
  const [benchmarks, setBenchmarks] = useState<VendorBenchmark[]>([]);
  const [forecast, setForecast] = useState<ForecastSummary | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newRequest, setNewRequest] = useState<{
    id: string;
    name: string;
    description: string;
    items: Array<{
      name: string;
      category: string;
      estimated_value: number;
      quantity: number;
      unit: string;
      supplier: string | null;
    }>;
  }>({
    id: "",
    name: "",
    description: "",
    items: [] });

  const loadRequests = useCallback(async () => {
    setLoading(true);
    try {
      const result: any = await api.procurement.list_requests();
      // Transform to summary items
      const summaries = result.map((r: any) => ({
        id: r.id,
        name: r.name,
        category: r.items?.[0]?.category || "-",
        estimated_value: r.items?.reduce((sum: number, item: any) => sum + (item.estimated_value || 0), 0) || 0,
        status: r.status || "pending",
        supplier: r.items?.[0]?.supplier || null }));
      setRequests(summaries);
      if (summaries.length > 0 && !selectedRequestId) {
        setSelectedRequestId(summaries[0].id);
        fetchRequestDetails(summaries[0].id);
      }
    } catch (err) {
      console.error("Failed to load procurement requests:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedRequestId]);

  const fetchRequestDetails = useCallback(async (requestId: string) => {
    setLoading(true);
    try {
      // Fetch waste alerts
      const wasteResult: any = await api.procurement.waste_summary(requestId);
      setWasteAlerts(wasteResult.alerts || []);

      // Fetch bottlenecks
      const bottleneckResult: any = await api.procurement.bottlenecks_summary(requestId);
      setBottlenecks(bottleneckResult.by_type ? Object.entries(bottleneckResult.by_type).map(([k, v]: any) => ({
        id: k,
        type: k,
        title: `${k.replace(/_/g, " ")}`,
        severity: "medium",
        impact_days: bottleneckResult.estimated_delay_days / Math.max(1, Object.keys(bottleneckResult.by_type || {}).length) })) : []);

      // Fetch benchmarks
      const benchmarkResult: any = await api.procurement.benchmarks_summary(requestId);
      setBenchmarks(benchmarkResult.by_category ? Object.entries(benchmarkResult.by_category).flatMap(([cat, items]: any) =>
        items.map((b: any) => ({
          category: cat,
          metric: b.metric,
          user_value: b.user_value,
          percentile: b.percentile,
          insight: b.insight }))
      ) : []);

      // Fetch forecast
      const forecastResult: any = await api.procurement.forecast_summary(requestId);
      setForecast({
        horizon_days: forecastResult.horizon_days || 90,
        projected_total: forecastResult.projected_total || 0,
        projected_savings: forecastResult.projected_savings || 0,
        confidence: forecastResult.confidence || 50,
        scenarios: forecastResult.scenarios || [] });
    } catch (err) {
      console.error("Failed to fetch procurement details:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleCreate = useCallback(async () => {
    setLoading(true);
    try {
      const request_data = {
        id: newRequest.id || `procurement-${uuid4()}`,
        name: newRequest.name,
        description: newRequest.description,
        items: newRequest.items.map((item: any) => ({
          id: item.id || uuid4(),
          name: item.name,
          category: item.category,
          estimated_value: item.estimated_value,
          currency: "USD",
          quantity: item.quantity || 1,
          unit: item.unit || "each",
          supplier: item.supplier || null,
          status: "pending",
          priority: "medium",
          estimated_start: null,
          estimated_end: null,
          requirements: [],
          constraints: [] })),
        budget_cap: null,
        timeline_days: null,
        department: "Procurement",
        requestor: "System",
        tags: [],
        created_at: new Date().toISOString(),
        status: "pending" };

      await api.procurement.create_request(request_data as any);
      setShowCreateModal(false);
      setNewRequest({
        id: "",
        name: "",
        description: "",
        items: [] });
      loadRequests();
    } catch (err) {
      console.error("Failed to create procurement request:", err);
    } finally {
      setLoading(false);
    }
  }, [newRequest]);

  const uuid4 = () => Math.random().toString(36).substr(2, 9);

  return (
    <div className="space-y-6">
      {/* Requests list and details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Requests list */}
        <div className="lg:col-span-1">
          <Card className="glass">
            <div className="p-6">
              <h3 className="text-xl font-bold text-white mb-4">Procurement Requests</h3>
              {loading ? (
                <p className="text-slate-500">Loading requests...</p>
              ) : requests.length === 0 ? (
                <p className="text-slate-500 text-sm">No procurement requests found. Create one above.</p>
              ) : (
                <div className="space-y-2">
                  {requests.map((req: ProcurementItemSummary) => (
                    <Button
                      key={req.id}
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setSelectedRequestId(req.id);
                        fetchRequestDetails(req.id);
                      }}
                    >
                      {req.name} — ${req.estimated_value.toLocaleString()}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          </Card>

          {/* Create New Request Modal */}
          <Card className="glass">
            <div className="p-6">
              <h3 className="text-xl font-bold text-white mb-4">Create New Request</h3>
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-slate-300 mb-2 block">Request Name</label>
                  <input
                    value={newRequest.name}
                    onChange={(e) =>
                      setNewRequest({ ...newRequest, name: e.target.value })
                    }
                    className="glass p-3 rounded-xl text-white border border-slate-600 focus:outline-none focus:border-cyan-500"
                    placeholder="e.g., Q4 IT Infrastructure Procurement"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-300 mb-2 block">Description</label>
                  <textarea
                    value={newRequest.description}
                    onChange={(e) =>
                      setNewRequest({ ...newRequest, description: e.target.value })
                    }
                    className="glass p-3 rounded-xl text-white border border-slate-600 resize-none h-20 focus:outline-none focus:border-cyan-500"
                    placeholder="Detailed description of needs..."
                  ></textarea>
                </div>
                <div>
                  <label className="text-sm text-slate-300 mb-2 block">Items</label>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3" id="items-grid">
                    {newRequest.items.map((item: any, i: number) => (
                      <div key={i} className="glass p-3 rounded-xl">
                        <input
                          value={item.name || ""}
                          onChange={(e) => {
                            const newItems = [...newRequest.items];
                            newItems[i] = { ...newItems[i], name: e.target.value };
                            setNewRequest({ ...newRequest, items: newItems });
                          }}
                          className="w-full p-2 rounded text-slate-800 bg-white/10 border border-slate-600 focus:outline-none focus:border-cyan-500"
                          placeholder="Item name"
                        />
                        <input
                          value={item.category || ""}
                          onChange={(e) => {
                            const newItems = [...newRequest.items];
                            newItems[i] = { ...newItems[i], category: e.target.value };
                            setNewRequest({ ...newRequest, items: newItems });
                          }}
                          className="w-full p-2 rounded text-slate-800 bg-white/10 border border-slate-600 focus:outline-none focus:border-cyan-500"
                          placeholder="Category"
                        />
                        <input
                          value={item.estimated_value || 0}
                          onChange={(e) => {
                            const newItems = [...newRequest.items];
                            newItems[i] = { ...newItems[i], estimated_value: Number(e.target.value) || 0 };
                            setNewRequest({ ...newRequest, items: newItems });
                          }}
                          className="w-full p-2 rounded text-slate-800 bg-white/10 border border-slate-600 focus:outline-none focus:border-cyan-500"
                          type="number"
                          placeholder="Value"
                        />
                        <input
                          value={item.quantity ?? 1}
                          onChange={(e) => {
                            const newItems = [...newRequest.items];
                            newItems[i] = { ...newItems[i], quantity: Number(e.target.value) };
                            setNewRequest({ ...newRequest, items: newItems });
                          }}
                          className="w-full p-2 rounded text-slate-800 bg-white/10 border border-slate-600 focus:outline-none focus:border-cyan-500"
                          type="number"
                          placeholder="Qty"
                        />
                        <input
                          value={item.supplier || ""}
                          onChange={(e) => {
                            const newItems = [...newRequest.items];
                            newItems[i] = { ...newItems[i], supplier: e.target.value };
                            setNewRequest({ ...newRequest, items: newItems });
                          }}
                          className="w-full p-2 rounded text-slate-800 bg-white/10 border border-slate-600 focus:outline-none focus:border-cyan-500"
                          placeholder="Supplier"
                        />
                      </div>
                    ))}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      setNewRequest({
                        ...newRequest,
                        items: [...newRequest.items, { name: "", category: "", estimated_value: 0, quantity: 1, unit: "each", supplier: "" }] })
                    }
                  >
                    + Add Item
                  </Button>
                </div>
              </div>
              <Button
                variant="primary"
                onClick={handleCreate}
                disabled={showCreateModal}
              >
                Create Request
              </Button>
            </div>
          </Card>
        </div>

        {/* Right: Dashboard details */}
        <div>
          {selectedRequestId ? (
            <Card className="glass">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white">
                      {requests.find((r) => r.id === selectedRequestId)?.name || "Details"}
                    </h2>
                    <p className="text-slate-400">Request ID: {selectedRequestId}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedRequestId("")}
                  >
                    Close
                  </Button>
                </div>

                {/* Waste Detection */}
                <Card className="glass" style={{ marginBottom: "1rem" }}>
                  <div className="p-4">
                    <h4 className="text-white font-medium mb-3">Waste Detection</h4>
                    {wasteAlerts.length === 0 ? (
                      <p className="text-slate-400">No waste detected — excellent!</p>
                    ) : (
                      <div className="grid grid-cols-2 gap-3">
                        {wasteAlerts.map((alert: WasteAlertSummary) => (
                          <div
                            key={alert.id}
                            className={`glass rounded-xl p-3 transition-all hover:bg-white/5 ${
                              alert.severity === "critical"
                                ? "border-l-4 border-red-500"
                                : alert.severity === "high"
                                  ? "border-l-4 border-orange-500"
                                  : ""
                            }`}
                          >
                            <div className="flex items-start gap-2">
                              <span className="text-lg">{alert.title}</span>
                            </div>
                            <p className="text-xs text-slate-400">{alert.monetary_impact.toLocaleString()} USD impact</p>
                            <p className="text-xs text-slate-500">{alert.waste_type.replace(/_/g, " ")}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </Card>

                {/* Bottlenecks */}
                <Card className="glass" style={{ marginBottom: "1rem" }}>
                  <div className="p-4">
                    <h4 className="text-white font-medium mb-3">Bottlenecks</h4>
                    {bottlenecks.length === 0 ? (
                      <p className="text-slate-400">No bottlenecks identified.</p>
                    ) : (
                      <div className="grid grid-cols-2 gap-3">
                        {bottlenecks.map((b: BottleneckSummary) => (
                          <div
                            key={b.id}
                            className={`glass rounded-xl p-3 transition-all hover:bg-white/5 ${
                              b.severity === "high" || b.severity === "critical"
                                ? "border-l-4 border-red-500"
                                : ""
                            }`}
                          >
                            <div className="flex items-start gap-2">
                              <span className="text-lg">{b.title}</span>
                            </div>
                            <p className="text-xs text-slate-400">{b.impact_days} day impact</p>
                            <p className="text-xs text-slate-500">{b.type.replace(/_/g, " ")}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </Card>

                {/* Vendor Benchmarks */}
                <Card className="glass" style={{ marginBottom: "1rem" }}>
                  <div className="p-4">
                    <h4 className="text-white font-medium mb-3">Vendor Benchmarks</h4>
                    {benchmarks.length === 0 ? (
                      <p className="text-slate-400">No vendor benchmarks available.</p>
                    ) : (
                      <div className="space-y-3">
                        {benchmarks.map((b: VendorBenchmark) => (
                          <div key={b.category} className="glass p-3 rounded-xl">
                            <div className="flex items-center justify-between">
                              <span className="text-white">{b.metric}</span>
                              <span className="text-slate-400 text-sm">{b.percentile}%</span>
                            </div>
                            <div className="mt-2">
                              <div className="w-full bg-white/20 rounded-full h-2">
                                <div
                                  className={`h-full rounded-full transition-width ${b.percentile >= 75 ? "bg-green-500" : b.percentile >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                                  style={{ width: `${b.percentile}%` }}
                                />
                              </div>
                              <span className="text-xs text-slate-400 ml-2">{b.user_value}</span>
                            </div>
                            <p className="text-xs text-slate-500 mt-1">{b.insight}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </Card>

                {/* Forecast */}
                <Card className="glass">
                  <div className="p-4">
                    <h4 className="text-white font-medium mb-3">Outcome Forecast</h4>
                    {forecast ? (
                      <>
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <p className="text-2xl font-bold text-white">{forecast.projected_total.toLocaleString()}</p>
                          <p className="text-xs text-slate-400">Projected Total</p>
                        </div>
                        <div>
                          <p className="text-2xl font-bold text-green-400">{forecast.projected_savings.toLocaleString()}</p>
                          <p className="text-xs text-slate-400">Projected Savings</p>
                        </div>
                        <div>
                          <p className="text-2xl font-bold text-yellow-400">{forecast.confidence}%</p>
                          <p className="text-xs text-slate-400">Confidence</p>
                        </div>
                      </div>
                      <div className="mt-4 p-3 bg-white/10 rounded-xl">
                        <h5 className="text-sm text-slate-400 mb-2">Scenarios</h5>
                        <div className="grid grid-cols-2 gap-2">
                          {forecast.scenarios.map((s: any, i: number) => (
                            <div key={i} className="glass p-2 rounded">
                              <span className="text-xs text-slate-300">{s.name}</span>
                              <span className="text-xs text-white ml-2">{s.projected_total.toLocaleString()} USD</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      </>
                    ) : (
                      <p className="text-slate-500">Load a request to see forecast</p>
                    )}
                  </div>
                </Card>
              </div>
            </Card>
          ) : (
            <Card className="glass">
              <div className="p-6 text-center">
                <p className="text-slate-500">Select a procurement request from the list to view analysis.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}