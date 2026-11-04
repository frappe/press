# Linting guidelines

Guidelines for linting and formatting code in this project.

Python (via ruff — runs on pre-commit):
```bash
ruff check press/
ruff format press/
```

JavaScript/Vue (via Biome). Do NOT use `npx biome`. It resolves to an unrelated
package (v0.3.3) that does nothing and reports no error. Use the real Biome
(v2.x) that the pre-commit hook installs, with the repo-root `biome.json` and
absolute file paths:
```bash
BIOME=$(ls ~/.cache/pre-commit/*/node_env-default/lib/node_modules/@biomejs/pre-commit/node_modules/@biomejs/cli-linux-x64/biome | head -1)
"$BIOME" check --write --config-path="$(pwd)/biome.json" <absolute-paths>
```

Install the pre-commit hooks once with:
```bash
bash setup-pre-commit.sh
```
