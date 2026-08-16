import tseslint from "typescript-eslint";

export default tseslint.config({
  extends: [
    ...tseslint.configs.recommended,
  ],
  files: ["src/**/*.ts", "tests/**/*.ts"],
  rules: {
    "@typescript-eslint/no-explicit-any": "off",
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
  },
});
