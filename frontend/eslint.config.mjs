import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // React Compiler-era hooks rules. These used to be disabled because every
      // data-fetching page set state inside the effect body. The fetches now
      // deliver state through promise callbacks (or inline async IIFEs), so the
      // rules stay ON — no blanket exception, no per-file escape hatch.
      "react-hooks/set-state-in-effect": "error",
      "react-hooks/immutability": "error",
    },
  },
]);

export default eslintConfig;
