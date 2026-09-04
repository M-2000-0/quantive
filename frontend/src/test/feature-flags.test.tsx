import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import {
  PLANS,
  FEATURES,
  hasFeature,
  hasMinimumPlan,
  getPlanFeatures,
  getLockedFeatures,
  getRequiredPlan,
  getUpgradePlan,
  getAnnualSavings,
  getFeatureMatrix,
  getPlanLimits,
  checkPlanLimits,
  type PlanTier,
} from '../lib/featureFlags';
import PlanGate from '../components/PlanGate';
import UpgradePrompt from '../components/UpgradePrompt';
import UpgradeModal from '../components/UpgradeModal';

const renderWithRouter = (component: React.ReactNode) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

// ── featureFlags Utility Tests ───────────────────────────────────────

describe('featureFlags utility', () => {
  describe('PLANS', () => {
    it('defines 4 plans (demo, starter, professional, enterprise)', () => {
      expect(PLANS.demo).toBeDefined();
      expect(PLANS.starter).toBeDefined();
      expect(PLANS.professional).toBeDefined();
      expect(PLANS.enterprise).toBeDefined();
    });

    it('plans have correct pricing hierarchy', () => {
      expect(PLANS.starter.price).toBeLessThan(PLANS.professional.price);
      expect(PLANS.professional.price).toBeLessThan(PLANS.enterprise.price);
    });

    it('annual price is lower than monthly', () => {
      expect(PLANS.starter.priceAnnual).toBeLessThan(PLANS.starter.price);
      expect(PLANS.professional.priceAnnual).toBeLessThan(PLANS.professional.price);
      expect(PLANS.enterprise.priceAnnual).toBeLessThan(PLANS.enterprise.price);
    });

    it('higher tiers have higher limits', () => {
      expect(PLANS.starter.maxPortfolios).toBeLessThan(PLANS.professional.maxPortfolios);
      expect(PLANS.professional.maxUsers).toBeLessThan(PLANS.enterprise.maxUsers);
    });

    it('enterprise has unlimited users', () => {
      expect(PLANS.enterprise.maxUsers).toBeGreaterThanOrEqual(999);
    });
  });

  describe('FEATURES', () => {
    it('defines at least 40 features', () => {
      expect(FEATURES.length).toBeGreaterThanOrEqual(40);
    });

    it('each feature has required fields', () => {
      FEATURES.forEach((f) => {
        expect(f.id).toBeTruthy();
        expect(f.name).toBeTruthy();
        expect(f.description).toBeTruthy();
        expect(f.minPlan).toBeTruthy();
        expect(f.category).toBeTruthy();
      });
    });

    it('spans multiple categories', () => {
      const cats = new Set(FEATURES.map((f) => f.category));
      expect(cats.size).toBeGreaterThanOrEqual(8);
    });
  });

  describe('hasFeature', () => {
    it('starter has basic charts', () => {
      expect(hasFeature('starter', 'charts.basic')).toBe(true);
    });

    it('starter does not have optimization', () => {
      expect(hasFeature('starter', 'optimization.run')).toBe(false);
    });

    it('professional has optimization', () => {
      expect(hasFeature('professional', 'optimization.run')).toBe(true);
    });

    it('professional does not have Monte Carlo', () => {
      expect(hasFeature('professional', 'analytics.monte_carlo')).toBe(false);
    });

    it('enterprise has everything', () => {
      FEATURES.forEach((f) => {
        expect(hasFeature('enterprise', f.id)).toBe(true);
      });
    });

    it('demo has everything', () => {
      FEATURES.forEach((f) => {
        expect(hasFeature('demo', f.id)).toBe(true);
      });
    });
  });

  describe('hasMinimumPlan', () => {
    it('professional meets professional requirement', () => {
      expect(hasMinimumPlan('professional', 'professional')).toBe(true);
    });

    it('starter does not meet professional requirement', () => {
      expect(hasMinimumPlan('starter', 'professional')).toBe(false);
    });

    it('enterprise meets all requirements', () => {
      expect(hasMinimumPlan('enterprise', 'starter')).toBe(true);
      expect(hasMinimumPlan('enterprise', 'professional')).toBe(true);
      expect(hasMinimumPlan('enterprise', 'enterprise')).toBe(true);
    });
  });

  describe('getPlanFeatures', () => {
    it('starter has fewer features than professional', () => {
      const starterFeatures = getPlanFeatures('starter');
      const proFeatures = getPlanFeatures('professional');
      expect(starterFeatures.length).toBeLessThan(proFeatures.length);
    });

    it('enterprise has all features', () => {
      expect(getPlanFeatures('enterprise').length).toBe(FEATURES.length);
    });
  });

  describe('getLockedFeatures', () => {
    it('starter has locked features', () => {
      const locked = getLockedFeatures('starter');
      expect(locked.length).toBeGreaterThan(0);
    });

    it('enterprise has no locked features', () => {
      expect(getLockedFeatures('enterprise')).toHaveLength(0);
    });
  });

  describe('getRequiredPlan', () => {
    it('optimization requires professional', () => {
      expect(getRequiredPlan('optimization.run')).toBe('professional');
    });

    it('Monte Carlo requires enterprise', () => {
      expect(getRequiredPlan('analytics.monte_carlo')).toBe('enterprise');
    });
  });

  describe('getUpgradePlan', () => {
    it('starter upgrades to professional', () => {
      expect(getUpgradePlan('starter')).toBe('professional');
    });

    it('professional upgrades to enterprise', () => {
      expect(getUpgradePlan('professional')).toBe('enterprise');
    });

    it('enterprise has no upgrade', () => {
      expect(getUpgradePlan('enterprise')).toBeNull();
    });
  });

  describe('getAnnualSavings', () => {
    it('calculates savings for starter', () => {
      expect(getAnnualSavings('starter')).toBe((299 - 249) * 12);
    });

    it('calculates savings for enterprise', () => {
      expect(getAnnualSavings('enterprise')).toBe((2499 - 2099) * 12);
    });
  });

  describe('getFeatureMatrix', () => {
    it('returns features grouped by category', () => {
      const matrix = getFeatureMatrix();
      expect(matrix.length).toBeGreaterThan(0);
      matrix.forEach((group) => {
        expect(group.category).toBeTruthy();
        expect(group.features.length).toBeGreaterThan(0);
        group.features.forEach((row) => {
          expect(typeof row.starter).toBe('boolean');
          expect(typeof row.professional).toBe('boolean');
          expect(typeof row.enterprise).toBe('boolean');
        });
      });
    });
  });

  describe('getPlanLimits', () => {
    it('returns limits for starter', () => {
      const limits = getPlanLimits('starter');
      expect(limits.maxPortfolios).toBe(3);
      expect(limits.maxUsers).toBe(2);
    });

    it('returns limits for enterprise', () => {
      const limits = getPlanLimits('enterprise');
      expect(limits.maxPortfolios).toBeGreaterThanOrEqual(999);
    });
  });

  describe('checkPlanLimits', () => {
    it('passes when within limits', () => {
      const result = checkPlanLimits('professional', { portfolios: 5, users: 8 });
      expect(result.withinLimits).toBe(true);
      expect(result.violations).toHaveLength(0);
    });

    it('fails when exceeding portfolio limit', () => {
      const result = checkPlanLimits('starter', { portfolios: 5 });
      expect(result.withinLimits).toBe(false);
      expect(result.violations.length).toBe(1);
      expect(result.violations[0]).toContain('Portfolios');
    });

    it('fails when exceeding user limit', () => {
      const result = checkPlanLimits('starter', { users: 5 });
      expect(result.withinLimits).toBe(false);
      expect(result.violations[0]).toContain('Users');
    });

    it('fails when exceeding API provider limit', () => {
      const result = checkPlanLimits('starter', { apiProviders: 1 });
      expect(result.withinLimits).toBe(false);
      expect(result.violations[0]).toContain('API Providers');
    });

    it('reports multiple violations', () => {
      const result = checkPlanLimits('starter', { portfolios: 10, users: 5, apiProviders: 2 });
      expect(result.violations.length).toBe(3);
    });
  });
});

// ── PlanGate Component Tests ──────────────────────────────────────────

describe('PlanGate', () => {
  it('renders children when feature is accessible', () => {
    renderWithRouter(
      <PlanGate plan="professional" feature="optimization.run">
        <div>Optimization Content</div>
      </PlanGate>
    );
    expect(screen.getByText('Optimization Content')).toBeDefined();
  });

  it('hides content when feature is locked and hideWhenLocked is true', () => {
    const { container } = renderWithRouter(
      <PlanGate plan="starter" feature="optimization.run" hideWhenLocked>
        <div>Optimization Content</div>
      </PlanGate>
    );
    expect(screen.queryByText('Optimization Content')).toBeNull();
  });

  it('shows upgrade prompt when feature is locked', () => {
    renderWithRouter(
      <PlanGate plan="starter" feature="optimization.run">
        <div>Optimization Content</div>
      </PlanGate>
    );
    expect(screen.queryByText('Optimization Content')).toBeNull();
    expect(screen.getByText(/Upgrade/)).toBeDefined();
  });

  it('shows custom fallback when provided', () => {
    renderWithRouter(
      <PlanGate plan="starter" feature="optimization.run" fallback={<div>Custom Fallback</div>}>
        <div>Optimization Content</div>
      </PlanGate>
    );
    expect(screen.getByText('Custom Fallback')).toBeDefined();
  });

  it('respects minPlan instead of feature', () => {
    renderWithRouter(
      <PlanGate plan="enterprise" minPlan="enterprise">
        <div>Enterprise Content</div>
      </PlanGate>
    );
    expect(screen.getByText('Enterprise Content')).toBeDefined();
  });
});

// ── UpgradePrompt Component Tests ─────────────────────────────────────

describe('UpgradePrompt', () => {
  it('shows required plan name', () => {
    renderWithRouter(
      <UpgradePrompt currentPlan="starter" requiredPlan="professional" />
    );
    const text = screen.getAllByText(/Professional/);
    expect(text.length).toBeGreaterThan(0);
  });

  it('shows feature name when provided', () => {
    renderWithRouter(
      <UpgradePrompt
        currentPlan="starter"
        requiredPlan="professional"
        feature={{ id: 'optimization.run', name: 'Run Optimization', description: 'Test', minPlan: 'professional', category: 'Optimization' }}
      />
    );
    expect(screen.getByText('Run Optimization')).toBeDefined();
  });

  it('shows pricing', () => {
    renderWithRouter(
      <UpgradePrompt currentPlan="starter" requiredPlan="professional" />
    );
    expect(screen.getByText('$899')).toBeDefined();
  });

  it('shows current plan', () => {
    renderWithRouter(
      <UpgradePrompt currentPlan="starter" requiredPlan="professional" />
    );
    expect(screen.getByText('starter')).toBeDefined();
  });

  it('renders compact variant', () => {
    renderWithRouter(
      <UpgradePrompt
        currentPlan="starter"
        requiredPlan="professional"
        compact
        feature={{ id: 'optimization.run', name: 'Run Optimization', description: 'Test', minPlan: 'professional', category: 'Optimization' }}
      />
    );
    expect(screen.getByText(/Run Optimization/)).toBeDefined();
  });
});

// ── UpgradeModal Component Tests ──────────────────────────────────────

describe('UpgradeModal', () => {
  it('does not render when isOpen is false', () => {
    renderWithRouter(
      <UpgradeModal isOpen={false} onClose={() => {}} currentPlan="starter" />
    );
    expect(screen.queryByText('Choose Your Plan')).toBeNull();
  });

  it('renders when isOpen is true', () => {
    renderWithRouter(
      <UpgradeModal isOpen={true} onClose={() => {}} currentPlan="starter" />
    );
    expect(screen.getByText('Choose Your Plan')).toBeDefined();
  });

  it('shows all three tier cards', () => {
    renderWithRouter(
      <UpgradeModal isOpen={true} onClose={() => {}} currentPlan="starter" />
    );
    const starter = screen.getAllByText('Starter');
    expect(starter.length).toBeGreaterThan(0);
    const pro = screen.getAllByText('Professional');
    expect(pro.length).toBeGreaterThan(0);
    const ent = screen.getAllByText('Enterprise');
    expect(ent.length).toBeGreaterThan(0);
  });

  it('shows billing toggle', () => {
    renderWithRouter(
      <UpgradeModal isOpen={true} onClose={() => {}} currentPlan="starter" />
    );
    expect(screen.getByText('Monthly')).toBeDefined();
    expect(screen.getByText('Annual')).toBeDefined();
  });

  it('shows current plan badge', () => {
    renderWithRouter(
      <UpgradeModal isOpen={true} onClose={() => {}} currentPlan="starter" />
    );
    const badge = screen.getAllByText('Current Plan');
    expect(badge.length).toBeGreaterThan(0);
  });

  it('shows feature comparison table', () => {
    renderWithRouter(
      <UpgradeModal isOpen={true} onClose={() => {}} currentPlan="starter" />
    );
    expect(screen.getByText('Feature Comparison')).toBeDefined();
  });

  it('shows Most Popular badge for Professional', () => {
    renderWithRouter(
      <UpgradeModal isOpen={true} onClose={() => {}} currentPlan="starter" />
    );
    expect(screen.getByText('Most Popular')).toBeDefined();
  });

  it('shows pricing for each tier', () => {
    renderWithRouter(
      <UpgradeModal isOpen={true} onClose={() => {}} currentPlan="starter" />
    );
    expect(screen.getByText('$299')).toBeDefined();
    expect(screen.getByText('$899')).toBeDefined();
    expect(screen.getByText('$2499')).toBeDefined();
  });
});
