# Community readiness checklist

> Phase: P10 CommunityPack pre-interface
>
> Authorized starting baseline:
> `b0064fab936f06d09a88eea5292e934410302145`
>
> Scope: deterministic contracts only. This phase does **not** implement or
> claim a microbial-community world model.

## Implemented contract gates

- [x] `vc.community-pack.v1` binds a community ID/version and canonical
  SHA-256 fingerprint.
- [x] Every member binds an already validated VirtualCellPack by exact
  `pack_id`, `pack_version`, and manifest fingerprint. Community registration
  revalidates the member Pack's current asset bytes and semantics.
- [x] Abundance is an explicit base-10 string in `fraction` units. Values must
  be positive and sum exactly to one; floats, exponent notation, missing
  values, normalization, padding, and deduplication are rejected.
- [x] Medium, shared-medium compartment, non-negative time interval, and
  `well_mixed` space representation are explicit. `well_mixed` is metadata,
  not a spatial simulation.
- [x] The shared-metabolite namespace binds an exact prefix, version,
  CURIE set, and amount unit. Member exchange declarations, medium
  components, and interaction evidence must reference those exact IDs.
- [x] Units are compared literally. P10 performs no conversion between
  `mmol`, `umol`, concentration, biomass-normalized flux, or time units.
- [x] Interaction evidence binds source member, target member, metabolite,
  evidence type, and reference. The shipped interaction is marked
  `contract_fixture`, not experimental evidence.
- [x] A one-member CommunityPack with abundance exactly one and no
  interaction evidence resolves to the original `RegisteredPack`; no matrix,
  feature, or metadata transformation occurs.
- [x] `vc.community-exchange-ledger.v1` requires every shared metabolite to
  appear explicitly. It checks participant, compartment, member exchange ID,
  unit, and exact rational balance; no omitted-metabolite zero fill or
  numerical tolerance is used.
- [x] `CommunityModelAdapter` is an abstract boundary with explicit model
  name, revision, fingerprint, plan, and run methods. P10 ships no
  implementation.
- [x] With no real adapter, `vc.community-execution-plan.v1` is deterministic
  with `executable=false` and no steps; `vc.community-run-result.v1` always
  returns `abstain=true`, `prediction=null`, and
  `community_model_unavailable`. There is no mock fallback.
- [x] All CommunityPack, exchange validation, plan, and run contracts fix
  `scientifically_validated=false`.

## Tiny member Packs

| Member | Pack identity | Taxon / assembly | Feature IDs | Evidence boundary |
|---|---|---|---|---|
| E. coli | `p8-bacteria-tiny@1.0.0`, fingerprint `8600261ad68302432186e7107f053a7a0fdf0e3dbc61dc9754a502b20a95b1fe` | `NCBITaxon:562`, `GCF_000005845.2` | `NCBIGene` | Existing synthetic P8 fixture |
| S. cerevisiae | `p10-yeast-tiny@1.0.0`, fingerprint `7f3bc08f6fd64209683603b1fc93b38a5e646b866eb05878160ec69a755b9ff1` | `NCBITaxon:4932`, `GCF_000146045.2` | `NCBIGene:855828` (GAL4), `NCBIGene:854954` (GAL80) | New synthetic P10 fixture; not P7 GEO data |

The yeast H5AD is 43,848 bytes. Two consecutive builds produced SHA-256
`c675ddee3d96aef9000e48ca7480cd0169eb10d3d4eced0fb08891178c7c46fc`.
The assembly and gene identifiers are anchored to the
[NCBI R64 assembly](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_000146045.2),
[GAL4](https://www.ncbi.nlm.nih.gov/gene/855828), and
[GAL80](https://www.ncbi.nlm.nih.gov/gene/854954) records. Expression values,
conditions, and interaction records remain synthetic contract fixtures.

## Test evidence

`praxis_virtualcell/tests/test_community_packs.py` covers:

- both tiny member Packs through the existing full `PackRegistry`;
- immutable canonical CommunityPack fingerprinting;
- abundance type, exact-sum, missing-value, and duplicate rejection;
- namespace, metabolite, member, compartment, and unit conflicts;
- current-byte member Pack revalidation and fingerprint mismatch;
- single-member identity equivalence;
- balanced toy exchange and a `1e-30`-scale residual that must fail;
- ledger participant, exchange-contract, unit, ID, and fingerprint conflicts;
- deterministic no-model plan and honest abstention; and
- the abstract, unimplemented `CommunityModelAdapter` boundary.

The exact directional and full-suite counts belong in the P10 completion
report after the final committed candidate is tested. A passing contract test
does not constitute biological validation.

## Experimental and model readiness: not completed

- [ ] No real mono-culture or co-culture abundance time series has been
  ingested, split, or evaluated.
- [ ] No uptake, secretion, isotope-tracing, extracellular metabolomics, or
  fluxomics measurement validates the toy exchange.
- [ ] No experimentally measured medium depletion/repletion, biomass, growth
  rate, carrying capacity, or death rate is bound to this contract.
- [ ] No strain-resolved interaction, competition, cooperation,
  cross-feeding, inhibition, or host-microbe effect has been validated.
- [ ] No metabolite ontology mapping or identifier conversion asset exists.
  The local `PRAXISMET` fixture namespace must not be interpreted as ChEBI,
  BiGG, MetaNetX, KEGG, or another external namespace.
- [ ] No dynamic FBA, community GEM, ordinary differential equation,
  ecological, agent-based, graph, foundation, or other community model is
  implemented or registered.
- [ ] No real `CommunityModelAdapter`, model card, model asset, checkpoint,
  compatibility benchmark, calibration, uncertainty estimate, or OOD
  evaluation exists.
- [ ] No spatial geometry, diffusion, migration, gradients, compartment
  transport, or time integration is executed.
- [ ] Toy mass balance checks only exact declared amount deltas. They do not
  establish elemental, charge, redox, energy, biomass, or thermodynamic
  feasibility.
- [ ] No predefined train/validation/test community benchmark, simple
  predictive baseline, prospective experiment, independent replication, or
  wet-lab validation has been completed.
- [ ] No claim of generalization across species, strains, media, abundance
  regimes, time ranges, spatial settings, laboratories, or clinical contexts
  is supported.

Until these items are addressed in separately authorized phases with
hash-bound data, predeclared evaluation, and independent evidence, the only
permitted outputs are contract validation, an execution plan, or abstention.
