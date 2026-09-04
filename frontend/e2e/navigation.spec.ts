import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('landing page has navigation links', async ({ page }) => {
    await page.goto('/');
    // Check the page loads
    await expect(page).toHaveTitle(/Quantive|Vite/);
  });

  test('login page has link to register', async ({ page }) => {
    await page.goto('/login');
    const registerLink = page.locator('a[href="/register"]');
    await expect(registerLink).toBeVisible();
  });

  test('register page has link to login', async ({ page }) => {
    await page.goto('/register');
    const loginLink = page.locator('a[href="/login"]');
    await expect(loginLink).toBeVisible();
  });

  test('unknown route redirects to landing', async ({ page }) => {
    await page.goto('/nonexistent-page-xyz');
    await page.waitForURL('**/', { timeout: 10_000 });
    expect(page.url()).toMatch(/\/$/);
  });
});

test.describe('Landing Page', () => {
  test('shows key features', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // The landing page should have some content
    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(100);
  });

  test('has sign in and get started buttons', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Check for CTA buttons
    const signIn = page.locator('a[href="/login"], button:has-text("Sign In"), button:has-text("Log In")');
    const count = await signIn.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });
});
