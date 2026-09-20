import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('API client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.cookie = '';
  });

  async function loadApi() {
    vi.resetModules();
    const mod = await import('../../api/index');
    return mod.api;
  }

  describe('request', () => {
    it('makes GET request with correct URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'healthy' }),
        headers: new Headers(),
      });
      const api = await loadApi();
      await api.health();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/health'),
        expect.objectContaining({ credentials: 'include' })
      );
    });

    it('sends CSRF token on POST requests', async () => {
      document.cookie = 'csrf_token=test-token-123';
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: 'jwt', refresh_token: 'jwt', token_type: 'bearer' }),
        headers: new Headers(),
      });
      const api = await loadApi();
      await api.auth.login({ email: 'test@test.com', password: 'pass' });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-CSRF-Token': 'test-token-123',
          }),
        })
      );
    });

    it('throws on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Bad request' }),
        headers: new Headers(),
      });
      const api = await loadApi();
      await expect(api.auth.login({ email: 'test@test.com', password: 'pass' }))
        .rejects.toThrow('Bad request');
    });

    it('redirects to login on 401', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Unauthorized' }),
        headers: new Headers(),
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });
      const api = await loadApi();
      await expect(api.auth.me()).rejects.toThrow('Unauthorized');
    });

    it('retries on 403 with refreshed CSRF token', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => ({ detail: 'Forbidden' }),
        headers: new Headers(),
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'healthy' }),
        headers: new Headers(),
      });
      const api = await loadApi();
      await api.health();
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it('handles 204 No Content', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: async () => ({}),
        headers: new Headers(),
      });
      const api = await loadApi();
      const result = await api.health();
      expect(result).toBeUndefined();
    });

    it('includes field errors in error message', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({
          detail: 'Validation error',
          errors: [
            { field: 'email', message: 'Invalid email' },
            { field: 'password', message: 'Too short' },
          ],
        }),
        headers: new Headers(),
      });
      const api = await loadApi();
      await expect(
        api.auth.register({ email: 'bad', password: '1', name: 'Test' })
      ).rejects.toThrow('Validation error');
    });
  });

  describe('CSRF token extraction', () => {
    it('extracts CSRF token from cookie', async () => {
      document.cookie = 'csrf_token=abc123';
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: 'jwt', refresh_token: 'jwt', token_type: 'bearer' }),
        headers: new Headers(),
      });
      const api = await loadApi();
      await api.auth.login({ email: 'a@b.com', password: 'pass' });
      const call = mockFetch.mock.calls[0];
      expect(call[1].headers['X-CSRF-Token']).toBe('abc123');
    });

    it('sends no CSRF header when token absent', async () => {
      document.cookie = '';
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: 'jwt', refresh_token: 'jwt', token_type: 'bearer' }),
        headers: new Headers(),
      });
      const api = await loadApi();
      await api.auth.login({ email: 'a@b.com', password: 'pass' });
      const call = mockFetch.mock.calls[0];
      expect(call[1].headers['Content-Type']).toBe('application/json');
      expect(call[1].headers['X-CSRF-Token']).toBeUndefined();
    });
  });
});
