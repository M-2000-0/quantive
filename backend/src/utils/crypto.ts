import crypto from "crypto";

const ALGORITHM = "aes-256-ecb";

export function encrypt(text: string, key: string): string {
  const cipher = crypto.createCipheriv(ALGORITHM, Buffer.from(key, "hex"), null);
  let encrypted = cipher.update(text, "utf8", "hex");
  encrypted += cipher.final("hex");
  return encrypted;
}

export function decrypt(encryptedText: string, key: string): string {
  const decipher = crypto.createDecipheriv(ALGORITHM, Buffer.from(key, "hex"), null);
  let decrypted = decipher.update(encryptedText, "hex", "utf8");
  decrypted += decipher.final("utf8");
  return decrypted;
}

export function hashToken(token: string): string {
  return crypto.createHash("sha256").update(token).digest("hex");
}

export function generateTraceId(): string {
  return crypto.randomUUID();
}

export function generateSecret(length = 32): string {
  return crypto.randomBytes(length).toString("hex");
}
