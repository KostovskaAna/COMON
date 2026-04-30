# ontology/

Contains the core OWL ontology that defines the COMON vocabulary.

## Files

| File | Description |
|------|-------------|
| `COMON.owl` | Main ontology in RDF/XML format |
| `catalog-v001.xml` | Protégé catalog for resolving imports |
| `external/iao.owl` | Local copy of the Information Artifact Ontology (IAO) dependency |
| `external/catalog-v001.xml` | Catalog for the external dependency |

## COMON.owl

**IRI:** `http://w3id.org/COMON/`  
**Version:** 1.0.0

The ontology imports [IAO](http://purl.obolibrary.org/obo/iao.owl) from OBO Foundry and reuses properties from OBI, BFO, Dublin Core, and DCAT.

### Key classes

| Class | IRI | Description |
|-------|-----|-------------|
| CMOAlgorithm | `COMON_000001` | An optimization algorithm |
| CMOExperiment | `COMON_000002` | An experiment specification |
| CMOPerformanceIndicator | `COMON_000003` | A quality indicator |
| CMOAlgorithmImplementation | `COMON_000004` | A concrete implementation of an algorithm |
| CMOAlgorithmExecution | `COMON_000006` | A single algorithm run |
| CMOPerformanceIndicatorExecution | `COMON_000007` | Execution of a PI computation |
| CMOPerformanceIndicatorImplementation | `COMON_000008` | Implementation of a PI |
| CMOAlgorithmIterationExecution | `COMON_000011` | One generation/iteration within a run |
| CMOPerformanceIndicatorDatum | `COMON_000013` | A single PI value |
| CMOExperimentExecution | `COMON_000014` | Execution of a full experiment |
| CMOExperimentImplementation | `COMON_000015` | Implementation of an experiment |
| CMOHypervolume | `COMON_000020` | Hypervolume indicator |
| CMOIGDPlus | `COMON_000021` | IGD+ indicator |
| CMOICMOPIndicator | `COMON_000019` | ICMOP indicator |
| CMOTotalConstraintViolation | `COMON_000023` | Constraint violation indicator |

### Reused properties (from imported ontologies)

| Property | Source | Usage |
|----------|--------|-------|
| `OBI:OBI_0000297` | OBI | `is_concretized_as` |
| `OBI:OBI_0000308` | OBI | `realizes` |
| `OBI:OBI_0000293` | OBI | `has_specified_input` |
| `OBI:OBI_0000299` | OBI | `has_specified_output` |
| `BFO:BFO_0000051` | BFO | `has_part` |
| `IAO:IAO_0000136` | IAO | `is_about` |
| `dc:identifier` | Dublin Core | identifier literal |

## Loading in Protégé

Open `COMON.owl` directly — the `catalog-v001.xml` file ensures the local `external/iao.owl` is used instead of fetching it from the network.