import { renderHook, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  useTemplates,
  createTemplateFromWizardState,
  BUILT_IN_TEMPLATES,
} from '../stores/templates';

// ─── useTemplates ───────────────────────────────────────────────────────────

describe('useTemplates', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns all 4 built-in templates', () => {
    const { result } = renderHook(() => useTemplates());
    expect(result.current.builtInTemplates).toHaveLength(4);
    expect(result.current.builtInTemplates.every(t => t.isBuiltIn)).toBe(true);
  });

  it('returns empty custom templates initially', () => {
    const { result } = renderHook(() => useTemplates());
    expect(result.current.customTemplates).toHaveLength(0);
  });

  it('getAll returns built-in + custom', () => {
    const { result } = renderHook(() => useTemplates());
    expect(result.current.getAll()).toHaveLength(4);
  });

  it('getById finds built-in template', () => {
    const { result } = renderHook(() => useTemplates());
    const tpl = result.current.getById('cost-minimizer');
    expect(tpl).not.toBeNull();
    expect(tpl!.name).toBe('Cost Minimizer');
  });

  it('getById returns null for unknown id', () => {
    const { result } = renderHook(() => useTemplates());
    expect(result.current.getById('nonexistent')).toBeNull();
  });

  it('saveTemplate adds custom template', () => {
    const { result } = renderHook(() => useTemplates());

    const customTpl = {
      id: 'custom-test',
      name: 'Test Template',
      description: 'A test template',
      isBuiltIn: false,
      objectives: { financing: 25, refinancing: 25, interestRate: 25, currency: 25 },
      constraints: {
        maxFinancingCost: { enabled: false, value: '' },
        maxRefinancingConcentration: { enabled: false, value: '' },
        maxCurrencyExposure: { enabled: false, value: '' },
        maxFloatingRateExposure: { enabled: false, value: '' },
        minLiquidity: { enabled: false, value: '' },
        maturityConcentrationLimit: { enabled: false, value: '' },
      },
      scenario_config: {
        selectedScenarios: ['base'],
        monteCarloCount: 1000,
        monteCarloSeed: 42,
        includeBaseInMc: true,
        solverSeed: 42,
      },
    };

    act(() => {
      result.current.saveTemplate(customTpl);
    });

    expect(result.current.customTemplates).toHaveLength(1);
    expect(result.current.getAll()).toHaveLength(5);
    expect(result.current.getById('custom-test')!.name).toBe('Test Template');
  });

  it('saveTemplate updates existing custom template', () => {
    const { result } = renderHook(() => useTemplates());

    const tpl = {
      id: 'custom-x',
      name: 'Original',
      description: 'desc',
      objectives: { financing: 25, refinancing: 25, interestRate: 25, currency: 25 },
      constraints: {
        maxFinancingCost: { enabled: false, value: '' },
        maxRefinancingConcentration: { enabled: false, value: '' },
        maxCurrencyExposure: { enabled: false, value: '' },
        maxFloatingRateExposure: { enabled: false, value: '' },
        minLiquidity: { enabled: false, value: '' },
        maturityConcentrationLimit: { enabled: false, value: '' },
      },
      scenario_config: {
        selectedScenarios: ['base'],
        monteCarloCount: 1000,
        monteCarloSeed: 42,
        includeBaseInMc: true,
        solverSeed: 42,
      },
    };

    act(() => {
      result.current.saveTemplate(tpl);
    });

    act(() => {
      result.current.saveTemplate({ ...tpl, name: 'Updated' });
    });

    expect(result.current.customTemplates).toHaveLength(1);
    expect(result.current.getById('custom-x')!.name).toBe('Updated');
  });

  it('deleteTemplate removes custom template', () => {
    const { result } = renderHook(() => useTemplates());

    const tpl = {
      id: 'custom-del',
      name: 'Delete Me',
      description: '',
      objectives: { financing: 25, refinancing: 25, interestRate: 25, currency: 25 },
      constraints: {
        maxFinancingCost: { enabled: false, value: '' },
        maxRefinancingConcentration: { enabled: false, value: '' },
        maxCurrencyExposure: { enabled: false, value: '' },
        maxFloatingRateExposure: { enabled: false, value: '' },
        minLiquidity: { enabled: false, value: '' },
        maturityConcentrationLimit: { enabled: false, value: '' },
      },
      scenario_config: {
        selectedScenarios: ['base'],
        monteCarloCount: 1000,
        monteCarloSeed: 42,
        includeBaseInMc: true,
        solverSeed: 42,
      },
    };

    act(() => {
      result.current.saveTemplate(tpl);
    });

    act(() => {
      result.current.deleteTemplate('custom-del');
    });

    expect(result.current.customTemplates).toHaveLength(0);
  });

  it('deleteTemplate ignores built-in templates', () => {
    const { result } = renderHook(() => useTemplates());

    act(() => {
      result.current.deleteTemplate('cost-minimizer');
    });

    expect(result.current.builtInTemplates).toHaveLength(4);
  });

  it('persists custom templates to localStorage', () => {
    const { result } = renderHook(() => useTemplates());

    const tpl = {
      id: 'custom-persist',
      name: 'Persistent',
      description: '',
      objectives: { financing: 25, refinancing: 25, interestRate: 25, currency: 25 },
      constraints: {
        maxFinancingCost: { enabled: false, value: '' },
        maxRefinancingConcentration: { enabled: false, value: '' },
        maxCurrencyExposure: { enabled: false, value: '' },
        maxFloatingRateExposure: { enabled: false, value: '' },
        minLiquidity: { enabled: false, value: '' },
        maturityConcentrationLimit: { enabled: false, value: '' },
      },
      scenario_config: {
        selectedScenarios: ['base'],
        monteCarloCount: 1000,
        monteCarloSeed: 42,
        includeBaseInMc: true,
        solverSeed: 42,
      },
    };

    act(() => {
      result.current.saveTemplate(tpl);
    });

    const stored = JSON.parse(localStorage.getItem('quantive:optimization-templates') || '[]');
    expect(stored).toHaveLength(1);
    expect(stored[0].name).toBe('Persistent');
  });
});

// ─── createTemplateFromWizardState ──────────────────────────────────────────

describe('createTemplateFromWizardState', () => {
  it('creates template with correct id and name', () => {
    const tpl = createTemplateFromWizardState(
      'My Strategy',
      'Custom optimization',
      {
        objectives: { financing: 30, refinancing: 30, interestRate: 20, currency: 20 },
        constraints: {
          maxFinancingCost: { enabled: true, value: '5000000' },
          maxRefinancingConcentration: { enabled: false, value: '' },
          maxCurrencyExposure: { enabled: false, value: '' },
          maxFloatingRateExposure: { enabled: false, value: '' },
          minLiquidity: { enabled: false, value: '' },
          maturityConcentrationLimit: { enabled: false, value: '' },
        },
        selectedScenarios: ['base', 'stress'],
        monteCarloCount: 5000,
        monteCarloSeed: 99,
        includeBaseInMc: false,
        solverSeed: 99,
      }
    );

    expect(tpl.name).toBe('My Strategy');
    expect(tpl.description).toBe('Custom optimization');
    expect(tpl.id).toMatch(/^custom-my-strategy-/);
    expect(tpl.isBuiltIn).toBe(false);
    expect(tpl.objectives.financing).toBe(30);
    expect(tpl.constraints.maxFinancingCost.enabled).toBe(true);
    expect(tpl.scenario_config.selectedScenarios).toEqual(['base', 'stress']);
    expect(tpl.scenario_config.monteCarloCount).toBe(5000);
  });

  it('generates slug from name', () => {
    const tpl = createTemplateFromWizardState('FX Hedge Strategy', '', {
      objectives: { financing: 25, refinancing: 25, interestRate: 25, currency: 25 },
      constraints: {
        maxFinancingCost: { enabled: false, value: '' },
        maxRefinancingConcentration: { enabled: false, value: '' },
        maxCurrencyExposure: { enabled: false, value: '' },
        maxFloatingRateExposure: { enabled: false, value: '' },
        minLiquidity: { enabled: false, value: '' },
        maturityConcentrationLimit: { enabled: false, value: '' },
      },
      selectedScenarios: ['base'],
      monteCarloCount: 1000,
      monteCarloSeed: 42,
      includeBaseInMc: true,
      solverSeed: 42,
    });

    expect(tpl.id).toMatch(/^custom-fx-hedge-strategy-/);
  });

  it('deep-copies constraints and scenarios', () => {
    const wizardState = {
      objectives: { financing: 25, refinancing: 25, interestRate: 25, currency: 25 },
      constraints: {
        maxFinancingCost: { enabled: true, value: '100' },
        maxRefinancingConcentration: { enabled: false, value: '' },
        maxCurrencyExposure: { enabled: false, value: '' },
        maxFloatingRateExposure: { enabled: false, value: '' },
        minLiquidity: { enabled: false, value: '' },
        maturityConcentrationLimit: { enabled: false, value: '' },
      },
      selectedScenarios: ['base', 'stress'],
      monteCarloCount: 1000,
      monteCarloSeed: 42,
      includeBaseInMc: true,
      solverSeed: 42,
    };

    const tpl = createTemplateFromWizardState('Test', '', wizardState);

    // Mutating the original should not affect the template
    wizardState.selectedScenarios.push('extreme');
    wizardState.constraints.maxFinancingCost.value = '999';

    expect(tpl.scenario_config.selectedScenarios).toEqual(['base', 'stress']);
    expect(tpl.constraints.maxFinancingCost.value).toBe('100');
  });
});

// ─── Built-in template data integrity ───────────────────────────────────────

describe('BUILT_IN_TEMPLATES', () => {
  it('has 4 templates with unique ids', () => {
    const ids = BUILT_IN_TEMPLATES.map(t => t.id);
    expect(new Set(ids).size).toBe(4);
  });

  it('all have objectives that sum to 100', () => {
    for (const tpl of BUILT_IN_TEMPLATES) {
      const sum =
        tpl.objectives.financing +
        tpl.objectives.refinancing +
        tpl.objectives.interestRate +
        tpl.objectives.currency;
      expect(sum).toBe(100);
    }
  });

  it('all have names and descriptions', () => {
    for (const tpl of BUILT_IN_TEMPLATES) {
      expect(tpl.name.length).toBeGreaterThan(0);
      expect(tpl.description.length).toBeGreaterThan(0);
    }
  });

  it('all have scenario configs with selectedScenarios', () => {
    for (const tpl of BUILT_IN_TEMPLATES) {
      expect(tpl.scenario_config.selectedScenarios.length).toBeGreaterThan(0);
      expect(tpl.scenario_config.monteCarloCount).toBeGreaterThan(0);
    }
  });
});
