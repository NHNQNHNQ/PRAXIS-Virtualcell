# Historical offline validation summary

These counts are a historical snapshot from JUnit output, not the current test total.
The scope was `praxis_virtualcell/tests`, excluding the separate generic agent test suite.

| Scope | Tests, including skips | Failures | Errors | Skipped | Passed |
|---|---:|---:|---:|---:|---:|
| Offline selection (`not llm`) | 952 | 0 | 0 | 40 | 912 |
| Selection including nine external LLM tests | 961 | 0 | 0 | 40 | 921 |

The retained case tables distinguish prediction, advisory routing, and abstention.
For capability limitations, see [the scope audit](PHASE10_GATE.md).
Run the commands in [the testing guide](../../docs/TESTING.md) for current results.
