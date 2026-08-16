import { describe, it, expect } from "vitest";
import { encrypt, decrypt, generateTraceId, generateSecret } from "../../src/utils/crypto";

const TEST_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

describe("crypto utils", () => {
  it("encrypts and decrypts", () => {
    const plain = "sensitive-api-key-123";
    const encrypted = encrypt(plain, TEST_KEY);
    expect(encrypted).not.toBe(plain);
    const decrypted = decrypt(encrypted, TEST_KEY);
    expect(decrypted).toBe(plain);
  });

  it("generates trace IDs", () => {
    const id = generateTraceId();
    expect(id).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("generates secrets", () => {
    const secret = generateSecret();
    expect(secret.length).toBe(64);
  });
});
