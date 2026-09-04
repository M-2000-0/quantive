// ── Pipeline Orchestrator ───────────────────────────────────────────
// Connects continuousOptimizer real-time signal stream to the
// autoDraftPipeline, automatically generating memos and routing
// for approval when new signals arrive. Includes live notification
// system for pipeline events.

import { getContinuousOptimizer, type OptimizationSignal } from './continuousOptimizer';
import { getAutoDraftPipeline, type PipelineRun, type MemoDraft } from './autoDraftPipeline';

// ── Types ────────────────────────────────────────────────────────────

export type PipelineEventType =
  | 'signal_received'
  | 'memo_generated'
  | 'routed_for_approval'
  | 'approved'
  | 'rejected'
  | 'executed'
  | 'failed'
  | 'pipeline_error';

export interface PipelineEvent {
  id: string;
  type: PipelineEventType;
  timestamp: string;
  signalId: string;
  pipelineRunId?: string;
  memoDraft?: MemoDraft;
  message: string;
  severity: 'info' | 'success' | 'warning' | 'error';
}

export interface OrchestratorConfig {
  /** Auto-process signals when detected */
  autoProcess: boolean;
  /** Show toast notifications for pipeline events */
  showToastNotifications: boolean;
  /** Log events to console for debugging */
  debugMode: boolean;
  /** Maximum events to keep in history */
  maxEventHistory: number;
}

const DEFAULT_CONFIG: OrchestratorConfig = {
  autoProcess: true,
  showToastNotifications: true,
  debugMode: false,
  maxEventHistory: 100,
};

// ── Orchestrator Service ────────────────────────────────────────────

export class PipelineOrchestrator {
  private events: PipelineEvent[] = [];
  private config: OrchestratorConfig;
  private listeners: Set<(event: PipelineEvent) => void> = new Set();
  private unsubscribers: Array<() => void> = [];
  private eventIdCounter: number = 0;
  private isRunning: boolean = false;
  private processedSignalIds: Set<string> = new Set();

  constructor(config: Partial<OrchestratorConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /** Start listening for signals and processing them */
  start(): void {
    if (this.isRunning) return;
    this.isRunning = true;

    const optimizer = getContinuousOptimizer();
    const pipeline = getAutoDraftPipeline();

    // Subscribe to new signals from the continuous optimizer
    const unsubSignals = optimizer.onSignalsUpdate(async (signals) => {
      if (!this.config.autoProcess) return;

      // Process only new signals we haven't seen
      const newSignals = signals.filter(
        (s) => s.status === 'new' && !this.processedSignalIds.has(s.id),
      );

      for (const signal of newSignals) {
        await this.processSignal(signal);
      }
    });

    this.unsubscribers.push(unsubSignals);

    this.emit({
      type: 'signal_received',
      timestamp: new Date().toISOString(),
      signalId: 'system',
      message: 'Pipeline orchestrator started — listening for optimization signals',
      severity: 'info',
    });
  }

  /** Stop listening and processing */
  stop(): void {
    this.isRunning = false;
    this.unsubscribers.forEach((unsub) => unsub());
    this.unsubscribers = [];

    this.emit({
      type: 'signal_received',
      timestamp: new Date().toISOString(),
      signalId: 'system',
      message: 'Pipeline orchestrator stopped',
      severity: 'info',
    });
  }

  /** Process a single signal through the pipeline */
  async processSignal(signal: OptimizationSignal): Promise<PipelineRun | null> {
    const pipeline = getAutoDraftPipeline();

    // Mark as processed
    this.processedSignalIds.add(signal.id);

    // Emit signal received event
    this.emit({
      type: 'signal_received',
      timestamp: new Date().toISOString(),
      signalId: signal.id,
      message: `New ${signal.severity} priority signal: ${signal.type.replace(/_/g, ' ')}`,
      severity: signal.severity === 'critical' ? 'warning' : 'info',
    });

    try {
      // Process through the pipeline
      const run = await pipeline.processSignal(signal);

      if (run) {
        // Memo was generated
        this.emit({
          type: 'memo_generated',
          timestamp: new Date().toISOString(),
          signalId: signal.id,
          pipelineRunId: run.id,
          memoDraft: run.memoDraft || undefined,
          message: `Auto-drafted memo: ${run.memoDraft?.title || 'Unknown'}`,
          severity: 'success',
        });

        // If routed for approval
        if (run.stage === 'under_review' || run.stage === 'routed_for_approval') {
          this.emit({
            type: 'routed_for_approval',
            timestamp: new Date().toISOString(),
            signalId: signal.id,
            pipelineRunId: run.id,
            memoDraft: run.memoDraft || undefined,
            message: `Memo routed for approval — assigned to ${run.memoDraft?.assignees.join(', ') || 'team'}`,
            severity: 'info',
          });
        }
      }

      return run;
    } catch (error) {
      this.emit({
        type: 'pipeline_error',
        timestamp: new Date().toISOString(),
        signalId: signal.id,
        message: `Pipeline error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        severity: 'error',
      });
      return null;
    }
  }

  /** Approve a pipeline run */
  approveRun(runId: string, approver: string, notes?: string): PipelineRun | null {
    const pipeline = getAutoDraftPipeline();
    const result = pipeline.approve(runId, approver, notes);

    if (result) {
      this.emit({
        type: 'approved',
        timestamp: new Date().toISOString(),
        signalId: result.signalId,
        pipelineRunId: runId,
        message: `Pipeline run approved by ${approver}${notes ? `: ${notes}` : ''}`,
        severity: 'success',
      });
    }

    return result;
  }

  /** Reject a pipeline run */
  rejectRun(runId: string, rejector: string, reason: string): PipelineRun | null {
    const pipeline = getAutoDraftPipeline();
    const result = pipeline.reject(runId, rejector, reason);

    if (result) {
      this.emit({
        type: 'rejected',
        timestamp: new Date().toISOString(),
        signalId: result.signalId,
        pipelineRunId: runId,
        message: `Pipeline run rejected by ${rejector}: ${reason}`,
        severity: 'warning',
      });
    }

    return result;
  }

  /** Subscribe to pipeline events */
  onEvent(listener: (event: PipelineEvent) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Get event history */
  getEvents(): PipelineEvent[] {
    return [...this.events];
  }

  /** Get events by type */
  getEventsByType(type: PipelineEventType): PipelineEvent[] {
    return this.events.filter((e) => e.type === type);
  }

  /** Get recent events */
  getRecentEvents(count: number = 10): PipelineEvent[] {
    return this.events.slice(-count);
  }

  /** Get stats */
  getStats() {
    return {
      totalEvents: this.events.length,
      isRunning: this.isRunning,
      processedSignals: this.processedSignalIds.size,
      memosGenerated: this.events.filter((e) => e.type === 'memo_generated').length,
      approvalsPending: this.events.filter((e) => e.type === 'routed_for_approval').length,
      approved: this.events.filter((e) => e.type === 'approved').length,
      rejected: this.events.filter((e) => e.type === 'rejected').length,
      errors: this.events.filter((e) => e.type === 'pipeline_error').length,
    };
  }

  /** Update config */
  updateConfig(updates: Partial<OrchestratorConfig>) {
    this.config = { ...this.config, ...updates };
  }

  private emit(eventData: Omit<PipelineEvent, 'id'>) {
    const event: PipelineEvent = {
      ...eventData,
      id: `evt-${Date.now()}-${++this.eventIdCounter}`,
    };

    this.events.push(event);

    // Trim to max history
    if (this.events.length > this.config.maxEventHistory) {
      this.events = this.events.slice(-this.config.maxEventHistory);
    }

    // Notify listeners
    this.listeners.forEach((l) => l(event));

    // Debug logging
    if (this.config.debugMode) {
      console.log(`[Pipeline] ${event.severity.toUpperCase()}: ${event.message}`, event);
    }
  }
}

// ── Singleton ────────────────────────────────────────────────────────

let _orchestrator: PipelineOrchestrator | null = null;

export function getPipelineOrchestrator(config?: Partial<OrchestratorConfig>): PipelineOrchestrator {
  if (!_orchestrator) {
    _orchestrator = new PipelineOrchestrator(config);
  }
  return _orchestrator;
}
