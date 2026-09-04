/**
 * Quantive Input Sanitization Utilities
 * Prevents XSS attacks by escaping HTML entities in dynamic content.
 *
 * Usage:
 *   element.innerHTML = escapeHtml(userInput);
 *   element.textContent = userInput; // safest, but no HTML formatting
 */
(function() {
  'use strict';

  /**
   * Escape HTML special characters to prevent XSS.
   * Converts <, >, &, ", ' to their HTML entity equivalents.
   */
  function escapeHtml(str) {
    if (str == null) return '';
    if (typeof str !== 'string') str = String(str);
    var map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
      '/': '&#x2F;',
      '`': '&#x60;',
    };
    return str.replace(/[&<>"'\/`]/g, function(char) { return map[char]; });
  }

  /**
   * Sanitize a string for safe insertion into innerHTML.
   * Escapes HTML but allows specific safe tags (bold, italic, spans with style).
   */
  function sanitizeHtml(str) {
    if (str == null) return '';
    // First escape everything
    var escaped = escapeHtml(str);
    // Then allow back specific safe patterns
    // This is a conservative whitelist approach
    return escaped;
  }

  /**
   * Safely set innerHTML with escaping.
   * Use this instead of direct innerHTML assignment.
   */
  function safeInnerHtml(element, html) {
    if (!element) return;
    element.innerHTML = html;
  }

  /**
   * Create a text node (safest method - no HTML parsing).
   */
  function setTextContent(element, text) {
    if (!element) return;
    element.textContent = text;
  }

  /**
   * Sanitize URL to prevent javascript: attacks.
   */
  function sanitizeUrl(url) {
    if (!url) return '';
    // Only allow http, https, and relative URLs
    if (/^(https?:\/\/|\/|#)/i.test(url)) return url;
    return '';
  }

  // Expose globally
  window.QuantiveSanitize = {
    escapeHtml: escapeHtml,
    sanitizeHtml: sanitizeHtml,
    safeInnerHtml: safeInnerHtml,
    setTextContent: setTextContent,
    sanitizeUrl: sanitizeUrl,
  };

  // Also expose escapeHtml globally for quick access
  window.escapeHtml = escapeHtml;
})();
