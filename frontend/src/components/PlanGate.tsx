// ── PlanGate Component ────────────────────────────────────────────────
// Conditionally renders children based on the user's plan tier.
// Shows an upgrade prompt when the feature is locked.

import { type ReactNode } from 'react';
import { hasFeature, hasMinimumPlan, getRequiredPlan, PLANS, type PlanTier, type FeatureDefinition } from '../lib/featureFlags';
import UpgradePrompt from './UpgradePrompt';

interface PlanGateProps {
  /** The current user's plan tier */
  plan: PlanTier;
  /** Feature ID to check (alternative to minPlan) */
  feature?: string;
  /** Minimum plan tier required (alternative to feature) */
  minPlan?: PlanTier;
  /** Content to render when access is granted */
  children: ReactNode;
  /** Custom content to show when locked (replaces default UpgradePrompt) */
  fallback?: ReactNode;
  /** Whether to hide completely instead of showing upgrade prompt */
  hideWhenLocked?: boolean;
  /** Additional CSS class for the wrapper */
  className?: string;
}

export default function PlanGate({
  plan,
  feature,
  minPlan,
  children,
  fallback,
  hideWhenLocked = false,
  className }: PlanGateProps) {
  // Check access
  const hasAccess = feature
    ? hasFeature(plan, feature)
    : minPlan
    ? hasMinimumPlan(plan, minPlan)
    : true;

  if (hasAccess) {
    return <>{children}</>;
  }

  if (hideWhenLocked) return null;

  // Determine what to show for locked content
  if (fallback) {
    return <div className={className}>{fallback}</div>;
  }

  // Find the required plan
  const requiredPlan = feature ? getRequiredPlan(feature) : minPlan;
  const requiredPlanDef = requiredPlan ? PLANS[requiredPlan] : null;

  const featureDef = feature
    ? { id: feature, minPlan: requiredPlan || 'enterprise', name: feature } as FeatureDefinition
    : undefined;

  return (
    <div className={className}>
      <UpgradePrompt
        currentPlan={plan}
        requiredPlan={requiredPlan || 'enterprise'}
        feature={featureDef}
        compact={false}
      />
    </div>
  );
}

/**
 * Higher-order component that wraps a component with plan gating.
 */
export function withPlanGate<P extends object>(
  Component: React.ComponentType<P>,
  options: { plan: PlanTier; feature?: string; minPlan?: PlanTier }
) {
  return function GatedComponent(props: P) {
    return (
      <PlanGate plan={options.plan} feature={options.feature} minPlan={options.minPlan}>
        <Component {...props} />
      </PlanGate>
    );
  };
}

/**
 * Hook-style check for use in components that need to conditionally render.
 */
export function usePlanAccess(plan: PlanTier) {
  return {
    hasFeature: (featureId: string) => hasFeature(plan, featureId),
    hasMinimumPlan: (minPlan: PlanTier) => hasMinimumPlan(plan, minPlan),
    getRequiredPlan: (featureId: string) => getRequiredPlan(featureId),
    isStarter: plan === 'starter',
    isProfessional: plan === 'professional',
    isEnterprise: plan === 'enterprise',
    isDemo: plan === 'demo' };
}
