# Using PRAXIS-VirtualCell

## Browser workflow

Start the local API with `praxis-vc serve`, then open the address printed by the command.
The bundled interface follows five stages:

1. **Ask**: describe the experiment or choose a structured preset.
2. **Review**: check species, cell context, perturbation, targets, and requested outputs.
3. **Route**: inspect candidate models and biological modules.
4. **Run**: confirm the request for deterministic execution.
5. **Results**: inspect predictions, evidence, routing, trace, provenance, and the report.

Offline mode makes no LLM calls. In LLM-assisted mode, an LLM may interpret the request,
suggest routes, critique, or narrate a result. The runtime determines compatibility,
numerical predictions, evidence requirements, and the final disposition.

## Reading results

An accepted result applies only to its recorded data, model, adapter, environment, and
validation scope. A `research_only` result remains a research artifact. Abstention means
the request cannot produce a supported prediction under the available evidence; do not
replace missing values with invented numbers.

The report and provenance identify the request and assets used. Export these artifacts
alongside any interpretation so another researcher can inspect the same execution context.

## Demonstration

Open [the interactive overview](presentation.html) for a presentation of the platform and
its evidence boundaries. It runs offline and includes a presentation mode and citation export.
See [examples](EXAMPLES.md), [installation](INSTALL.md), and [reproducibility](REPRODUCIBILITY.md).
