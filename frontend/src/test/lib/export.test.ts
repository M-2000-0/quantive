import { describe, it, expect, vi, beforeEach } from 'vitest';
import { toCSV, toJSON, toXLSX, exportData } from '../../lib/export';

describe('toCSV', () => {
  it('converts headers and rows to CSV', () => {
    const csv = toCSV(['Name', 'Value'], [['Alice', 100], ['Bob', 200]]);
    expect(csv).toBe('Name,Value\nAlice,100\nBob,200');
  });

  it('handles empty rows', () => {
    const csv = toCSV(['A', 'B'], []);
    expect(csv).toBe('A,B');
  });

  it('escapes commas in values', () => {
    const csv = toCSV(['Col'], [['a,b']]);
    expect(csv).toBe('Col\n"a,b"');
  });

  it('escapes double quotes', () => {
    const csv = toCSV(['Col'], [['say "hello"']]);
    expect(csv).toBe('Col\n"say ""hello"""');
  });

  it('escapes newlines', () => {
    const csv = toCSV(['Col'], [['line1\nline2']]);
    expect(csv).toBe('Col\n"line1\nline2"');
  });

  it('handles null and undefined', () => {
    const csv = toCSV(['Col'], [[null, undefined]]);
    expect(csv).toBe('Col\n,');
  });

  it('handles numeric values', () => {
    const csv = toCSV(['Rate'], [[3.14159]]);
    expect(csv).toBe('Rate\n3.14159');
  });
});

describe('toJSON', () => {
  it('serializes data with pretty print', () => {
    const result = toJSON({ a: 1 });
    expect(result).toBe('{\n  "a": 1\n}');
  });

  it('serializes data compactly', () => {
    const result = toJSON({ a: 1 }, false);
    expect(result).toBe('{"a":1}');
  });

  it('handles arrays', () => {
    const result = toJSON([1, 2, 3], false);
    expect(result).toBe('[1,2,3]');
  });

  it('handles nested objects', () => {
    const result = toJSON({ a: { b: 'c' } }, false);
    expect(result).toBe('{"a":{"b":"c"}}');
  });
});

describe('toXLSX', () => {
  it('generates valid XML spreadsheet', () => {
    const xml = toXLSX(['Name', 'Value'], [['Test', 42]]);
    expect(xml).toContain('<?xml version="1.0"?>');
    expect(xml).toContain('<Workbook');
    expect(xml).toContain('<Worksheet ss:Name="Data">');
    expect(xml).toContain('<Data ss:Type="String">Name</Data>');
    expect(xml).toContain('<Data ss:Type="Number">42</Data>');
    expect(xml).toContain('</Workbook>');
  });

  it('escapes XML special characters', () => {
    const xml = toXLSX(['Col'], [['<script>alert("xss")</script>']]);
    expect(xml).toContain('&lt;script&gt;');
    expect(xml).not.toContain('<script>');
  });
});

describe('exportData', () => {
  it('is exported and is a function', () => {
    expect(typeof exportData).toBe('function');
  });
});
