# Project Setup

- Package manager: **uv**
- Use `uv add <package>` to install dependencies (not `pip` or `uv pip`)
- Use `uv run` to execute scripts
- Use `uv run pytest` to run tests

# Coding Style

Build the simplest thing that works, with these constraints:

- Prefer a direct mapping from input → actions. Avoid intermediate representations unless they reduce total code and duplication.
- Avoid encode/decode round-trips (don't transform data just to reconstruct it later). Keep information in the form that will be consumed.
- Use recursion only when it simplifies code
- No "framework" structure: avoid argparse, classes, logging, configuration layers, and boilerplate unless explicitly requested.
- Don't add "robustness" extras (heavy validation, performance optimizations, edge-case handling) unless I ask. Let Python raise naturally.
- Prefer `assert` over `if ...: raise ValueError(...)`
- Keep control flow obvious: minimal state, minimal branching, minimal helpers. Don't refactor for elegance if it adds indirection.
- Output should be copy-paste runnable and short; prioritize fewer concepts over "best practices".
- If you're unsure between two implementations, pick the one with fewer moving parts and less duplication, even if it's less general.
- If you're about to add a helper, encoding step, validation, or optimization, don't—unless it removes more code than it adds.

Provide exactly the minimal script that satisfies the contract.

See [STYLE_EXAMPLES.md](STYLE_EXAMPLES.md) for full bad vs good code examples.
