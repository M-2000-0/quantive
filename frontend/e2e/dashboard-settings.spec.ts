import { test, expect } from '@playwright/test';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    // Set up demo mode in localStorage before navigating
    await page.addInitScript(() => {
      localStorage.setItem('demo_mode', 'true');
      localStorage.setItem('user', JSON.stringify({
        id: 'demo-user',
        email: 'demo@quantive.gov',
        name: 'Demo User',
        role: 'admin',
        org_id: 'demo-org',
      }));
    });
  });

  test('dashboard loads in demo mode', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Dashboard should render without redirecting to login
    expect(page.url()).toContain('/dashboard');
  });

  test('dashboard shows portfolio health section', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    const body = await page.textContent('body');
    expect(body).toContain('Health');
  });

  test('dashboard shows rebalancing alerts', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    const body = await page.textContent('body');
    expect(body).toContain('Rebalanc');
  });

  test('dashboard shows team section', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    const body = await page.textContent('body');
    expect(body).toContain('Team');
  });
});

test.describe('Settings Page Tabs', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('demo_mode', 'true');
      localStorage.setItem('user', JSON.stringify({
        id: 'demo-user',
        email: 'demo@quantive.gov',
        name: 'Demo User',
        role: 'admin',
        org_id: 'demo-org',
      }));
    });
  });

  test('settings page loads with tabs', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/settings');
    const body = await page.textContent('body');
    expect(body).toContain('Profile');
    expect(body).toContain('Security');
    expect(body).toContain('Appearance');
  });

  test('settings page tab switching works', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    // Click Security tab
    await page.click('button:has-text("Security")');
    await page.waitForTimeout(300);
    const body = await page.textContent('body');
    expect(body).toContain('Change Password');
  });

  test('settings page shows roles tab for admin', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    const body = await page.textContent('body');
    expect(body).toContain('Roles');
    expect(body).toContain('Permissions');
  });
});
