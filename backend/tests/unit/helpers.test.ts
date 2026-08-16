import { describe, it, expect } from "vitest";
import { scoreToLevel } from "../../src/utils/helpers";

describe("scoreToLevel", () => {
  it("returns LOW for scores below 0.25", () => {
    expect(scoreToLevel(0.1)).toBe("LOW");
    expect(scoreToLevel(0)).toBe("LOW");
  });

  it("returns MEDIUM for scores between 0.25 and 0.5", () => {
    expect(scoreToLevel(0.3)).toBe("MEDIUM");
    expect(scoreToLevel(0.5)).toBe("MEDIUM");
  });

  it("returns HIGH for scores between 0.5 and 0.75", () => {
    expect(scoreToLevel(0.6)).toBe("HIGH");
    expect(scoreToLevel(0.75)).toBe("HIGH");
  });

  it("returns CRITICAL for scores above 0.75", () => {
    expect(scoreToLevel(0.9)).toBe("CRITICAL");
    expect(scoreToLevel(1)).toBe("CRITICAL");
  });
});
