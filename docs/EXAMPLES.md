# Examples

## Interpret an experiment offline

```bash
praxis-vc ask --text "What happens when AHR is knocked out in human K562 cells?" --mode offline
```

Review the resulting structured request before running an experiment. Natural-language
parsing identifies explicit signals; it does not supply missing scientific evidence.

## Run a structured request

```bash
praxis-vc run --request praxis_virtualcell/examples/norman_mock_request.json --mode offline --out runs/example
```

Check the example files available in your checkout and choose a request compatible with
your installed Pack and model. An unbound request can abstain rather than return a prediction.

## Research protocols

The repository includes K562 Golden protocol, construction, evaluation, and replay scripts.
External datasets and model weights must be acquired separately under their source terms.
Follow [reproducibility](REPRODUCIBILITY.md) for the available artifacts and their scientific scope.
