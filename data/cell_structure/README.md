# Cell structure facts

`catalog.json` contains 36 small facts: five topology nodes and four adjacency
relations for each of Acinetobacter baumannii (470), Escherichia coli (562),
Pseudomonas aeruginosa (287), and Klebsiella pneumoniae (573).

All shipped facts are `reference_knowledge` with `evidence_scope=species_prior`.
Source strains and source conditions remain separate metadata. The graph is a
species anatomical prior; it does not establish the requested strain's current
envelope, protein localization, drug accessibility, or permeability. Exact-strain
facts and native protein localization records currently number zero. Unsupported
taxa return zero facts rather than receiving a Gram-negative default.

Sources are original studies, with the exact sections/figures retained per fact:

- [Grinter et al. 2021](https://journals.asm.org/doi/10.1128/mbio.01480-21),
  introductory A. baumannii envelope model.
- [Matias et al. 2003](https://journals.asm.org/doi/10.1128/jb.185.20.6112-6118.2003),
  frozen-hydrated E. coli K-12 and P. aeruginosa PAO1 sections.
- [Srinivasan et al. 2012](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0041505),
  introductory layered envelope and separate membrane fractions in K. pneumoniae.
- [2012 KpOmpA study](https://www.sciencedirect.com/science/article/pii/S096921261100414X),
  introductory outer membrane/periplasm model. Native strain identity is not
  assigned from this paper.

Use `cell_structure_overview(profile.overview(), catalog_path=...)` or
`query_cell_structure(profile.overview(), structure_ids=[...], catalog_path=...)`.
The default catalog is this directory's JSON file. `data_root` refers to this
structure directory, independently of the omics root. Protein queries require
both native `protein_ids` and `protein_namespace`. Exact-strain records require
exact taxonomy, strain, namespace, and genotype scope; study namespaces cannot
cross sources. An unreported genotype remains unreported and never matches an
explicit wild-type or mutant genotype.
