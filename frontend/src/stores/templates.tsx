import { useState, useEffect, useCallback } from 'react';

/**
 * Optimization template / preset types
 * Matches wizard state shape for direct apply.
 */
export interface TemplateObjectives {
  financing: number;
  refinancing: number;
  interestRate: number;
  currency: number;
}

export interface TemplateConstraints {
  maxFinancingCost: { enabled: boolean; value: string };
  maxRefinancingConcentration: { enabled: boolean; value: string };
  maxCurrencyExposure: { enabled: boolean; value: string };
  maxFloatingRateExposure: { enabled: boolean; value: string };
  minLiquidity: { enabled: boolean; value: string };
  maturityConcentrationLimit: { enabled: boolean; value: string };
}

export interface TemplateScenarioConfig {
  selectedScenarios: string[];
  monteCarloCount: number;
  monteCarloSeed: number;
  includeBaseInMc: boolean;
  solverSeed: number;
}

export interface OptimizationTemplate {
  id: string;
  name: string;
  description: string;
  isBuiltIn?: boolean;
  objectives: TemplateObjectives;
  constraints: TemplateConstraints;
  scenario_config: TemplateScenarioConfig;
}

const STORAGE_KEY = 'quantive:optimization-templates';

export const BUILT_IN_TEMPLATES: OptimizationTemplate[] = [
  {
    id: 'cost-minimizer',
    name: 'Cost Minimizer',
    description: 'Prioritizes financing cost reduction with relaxed risk limits.',
    isBuiltIn: true,
    objectives: { financing: 60, refinancing: 15, interestRate: 15, currency: 10 },
    constraints: {
      maxFinancingCost: { enabled: true, value: '6500000000' },
      maxRefinancingConcentration: { enabled: true, value: '0.40' },
      maxCurrencyExposure: { enabled: false, value: '' },
      maxFloatingRateExposure: { enabled: true, value: '0.35' },
      minLiquidity: { enabled: true, value: '3000000000' },
      maturityConcentrationLimit: { enabled: true, value: '0.40' },
    },
    scenario_config: {
      selectedScenarios: ['base'],
      monteCarloCount: 10000,
      monteCarloSeed: 42,
      includeBaseInMc: true,
      solverSeed: 42,
    },
  },
  {
    id: 'risk-averse',
    name: 'Risk Averse',
    description: 'Minimizes refinancing and interest rate risk with tight concentration limits.',
    isBuiltIn: true,
    objectives: { financing: 15, refinancing: 40, interestRate: 30, currency: 15 },
    constraints: {
      maxFinancingCost: { enabled: true, value: '6000000000' },
      maxRefinancingConcentration: { enabled: true, value: '0.20' },
      maxCurrencyExposure: { enabled: true, value: '0.15' },
      maxFloatingRateExposure: { enabled: true, value: '0.15' },
      minLiquidity: { enabled: true, value: '8000000000' },
      maturityConcentrationLimit: { enabled: true, value: '0.25' },
    },
    scenario_config: {
      selectedScenarios: ['base', 'high_interest', 'liquidity_shock'],
      monteCarloCount: 20000,
      monteCarloSeed: 42,
      includeBaseInMc: true,
      solverSeed: 42,
    },
  },
  {
    id: 'balanced',
    name: 'Balanced',
    description: 'Even trade-off across cost, risk and currency objectives.',
    isBuiltIn: true,
    objectives: { financing: 35, refinancing: 25, interestRate: 20, currency: 20 },
    constraints: {
      maxFinancingCost: { enabled: false, value: '' },
      maxRefinancingConcentration: { enabled: true, value: '0.30' },
      maxCurrencyExposure: { enabled: false, value: '' },
      maxFloatingRateExposure: { enabled: true, value: '0.25' },
      minLiquidity: { enabled: true, value: '5000000000' },
      maturityConcentrationLimit: { enabled: true, value: '0.35' },
    },
    scenario_config: {
      selectedScenarios: ['base', 'high_interest', 'low_interest'],
      monteCarloCount: 10000,
      monteCarloSeed: 42,
      includeBaseInMc: true,
      solverSeed: 42,
    },
  },
  {
    id: 'fx-hedge',
    name: 'FX Hedge',
    description: 'Hedges foreign currency exposure; stresses FX and inflation scenarios.',
    isBuiltIn: true,
    objectives: { financing: 20, refinancing: 20, interestRate: 15, currency: 45 },
    constraints: {
      maxFinancingCost: { enabled: false, value: '' },
      maxRefinancingConcentration: { enabled: true, value: '0.30' },
      maxCurrencyExposure: { enabled: true, value: '0.10' },
      maxFloatingRateExposure: { enabled: true, value: '0.20' },
      minLiquidity: { enabled: true, value: '5000000000' },
      maturityConcentrationLimit: { enabled: true, value: '0.35' },
    },
    scenario_config: {
      selectedScenarios: ['base', 'fx_shock'],
      monteCarloCount: 15000,
      monteCarloSeed: 42,
      includeBaseInMc: true,
      solverSeed: 42,
    },
  },
];

function loadCustomFromStorage(): OptimizationTemplate[] {
  if (typeof window === 'undefined' || !window.localStorage) return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as OptimizationTemplate[];
    if (!Array.isArray(parsed)) return [];
    // ensure custom templates are not marked builtIn
    return parsed.map((t) => ({ ...t, isBuiltIn: false }));
  } catch {
    return [];
  }
}

function persistCustom(templates: OptimizationTemplate[]) {
  if (typeof window === 'undefined' || !window.localStorage) return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(templates));
  } catch {
    // quota exceeded — ignore
  }
}

export function useTemplates() {
  const [customTemplates, setCustomTemplates] = useState<OptimizationTemplate[]>(() => loadCustomFromStorage());

  useEffect(() => {
    // re-sync on mount (handles SSR hydration mismatch)
    setCustomTemplates(loadCustomFromStorage());
  }, []);

  const saveTemplate = useCallback((tpl: OptimizationTemplate) => {
    setCustomTemplates((prev) => {
      const filtered = prev.filter((t) => t.id !== tpl.id);
      const next = [...filtered, { ...tpl, isBuiltIn: false }];
      persistCustom(next);
      return next;
    });
  }, []);

  const deleteTemplate = useCallback((id: string) => {
    setCustomTemplates((prev) => {
      // only allow deleting custom; ignore built-in
      if (BUILT_IN_TEMPLATES.some((t) => t.id === id)) return prev;
      const next = prev.filter((t) => t.id !== id);
      persistCustom(next);
      return next;
    });
  }, []);

  const getAll = useCallback(() => [...BUILT_IN_TEMPLATES, ...customTemplates], [customTemplates]);

  const getById = useCallback(
    (id: string) => {
      const all = [...BUILT_IN_TEMPLATES, ...customTemplates];
      return all.find((t) => t.id === id) || null;
    },
    [customTemplates]
  );

  return {
    builtInTemplates: BUILT_IN_TEMPLATES,
    customTemplates,
    allTemplates: [...BUILT_IN_TEMPLATES, ...customTemplates],
    getAll,
    getById,
    saveTemplate,
    deleteTemplate,
  };
}

export function createTemplateFromWizardState(
  name: string,
  description: string,
  wizardState: {
    objectives: TemplateObjectives;
    constraints: TemplateConstraints;
    selectedScenarios: string[];
    monteCarloCount: number;
    monteCarloSeed: number;
    includeBaseInMc: boolean;
    solverSeed: number;
  }
): OptimizationTemplate {
  const slug = name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || `custom-${Date.now()}`;
  return {
    id: `custom-${slug}-${Date.now().toString(36)}`,
    name: name.trim(),
    description: description.trim(),
    isBuiltIn: false,
    objectives: { ...wizardState.objectives },
    constraints: {
      maxFinancingCost: { ...wizardState.constraints.maxFinancingCost },
      maxRefinancingConcentration: { ...wizardState.constraints.maxRefinancingConcentration },
      maxCurrencyExposure: { ...wizardState.constraints.maxCurrencyExposure },
      maxFloatingRateExposure: { ...wizardState.constraints.maxFloatingRateExposure },
      minLiquidity: { ...wizardState.constraints.minLiquidity },
      maturityConcentrationLimit: { ...wizardState.constraints.maturityConcentrationLimit },
    },
    scenario_config: {
      selectedScenarios: [...wizardState.selectedScenarios],
      monteCarloCount: wizardState.monteCarloCount,
      monteCarloSeed: wizardState.monteCarloSeed,
      includeBaseInMc: wizardState.includeBaseInMc,
      solverSeed: wizardState.solverSeed,
    },
  };
}
