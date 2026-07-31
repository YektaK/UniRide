import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import { dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const eslintConfig = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    linterOptions: {
      reportUnusedDisableDirectives: "warn",
    },
    rules: {
      // TypeScript rules
      "@typescript-eslint/no-explicit-any": "warn",

      // React hooks rules — set-state-in-effect and purity were previously
      // disabled because their disables were believed to require Flow-style
      // comments. Standard eslint-disable-next-line works (verified 2026-07-31);
      // remaining intentional suppressions are marked inline where the pattern
      // is deliberate (fetch-on-mount, subscription notifications).
      "react-hooks/set-state-in-effect": "error",
      "react-hooks/purity": "error",

      // react/no-unescaped-entities flags `'` in JSX — pre-existing pattern
      "react/no-unescaped-entities": "off",

      // General JavaScript rules
      "no-fallthrough": "error",
      "no-unreachable": "error",
    },
  },
  {
    ignores: ["node_modules/**", ".next/**", "out/**", "build/**", "next-env.d.ts", "examples/**", "skills"]
  }
];

export default eslintConfig;
