/**
 * HTML Sanitizer — prevents XSS by escaping HTML entities.
 * Used as a safety layer before dangerouslySetInnerHTML.
 */

const ENTITY_MAP: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#x27;',
  '/': '&#x2F;',
  '`': '&#x60;',
};

export function escapeHtml(str: string): string {
  return str.replace(/[&<>"'`/]/g, (char) => ENTITY_MAP[char] || char);
}

/**
 * Sanitize markdown-derived HTML.
 * Allows safe tags (h2, strong, li, br, table, tr, td) but escapes everything else.
 */
export function sanitizeMarkdownHtml(html: string): string {
  // First escape any HTML that shouldn't be there
  let safe = escapeHtml(html);
  
  // Then re-allow our specific safe tags
  const allowedTags = ['h2', 'strong', 'li', 'br', 'table', 'tr', 'td', 'p', 'em', 'ul', 'ol'];
  for (const tag of allowedTags) {
    const openRegex = new RegExp('&lt;' + tag + '(\s[^&]*)?&gt;', 'gi');
    const closeRegex = new RegExp('&lt;\/' + tag + '&gt;', 'gi');
    safe = safe.replace(openRegex, (match) => match.replace(/&lt;/g, '<').replace(/&gt;/g, '>'));
    safe = safe.replace(closeRegex, (match) => match.replace(/&lt;/g, '<').replace(/&gt;/g, '>'));
  }
  
  // Allow class attributes on allowed tags
  safe = safe.replace(/class=&quot;/g, 'class="');
  
  return safe;
}
