# Contributing

1. Use Python 3.12+.
2. Keep Cogent pure infrastructure: do not add a project-owned Intelligent Contract or frontend.
3. Add tests for behavioral/statistical changes.
4. Preserve deterministic seeds in tests and simulations.
5. Keep methodology claims empirical and scoped to the supplied corpus.
6. Never commit API keys or private validator credentials.

Run before opening a pull request:

```bash
python -m compileall cogent
pytest
```
