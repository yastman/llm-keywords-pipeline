# Archive

One-off migration and audit scripts moved out of `src/llm_keywords_pipeline/` (same package
paths: `fix/`, `sync/`, `audit/`). They are kept for reference only: the pipeline does not run
them, they are not importable from the package, and they have no tests. Ruff skips this
directory.
