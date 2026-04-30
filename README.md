# COMON — Constrained Multi-Objective Optimization ONtology

COMON is a knowledge graph framework for representing and querying constrained multi-objective optimization experiments using semantic web technologies (OWL, RDF, SHACL).

## What it does

COMON provides a shared vocabulary and data model for describing:
- **Algorithms** — their implementations, platforms, and family relationships
- **Optimization problems** — objectives, constraints, variables, reference sets
- **Experiments** — configurations, execution parameters, stopping criteria
- **Results** — per-run performance indicator values (HV, IGD+, ICMOP, CV)

Raw metadata is authored in JSON-LD, validated with SHACL, and converted to RDF/XML for use in Protégé or any OWL/SPARQL toolchain.

## Repository structure

```
COMON/
├── ontology/            Core OWL ontology (COMON.owl)
├── data/
│   ├── raw_data/        Source metadata (JSON-LD) and experiment results (CSV)
│   └── annotations/     Converted RDF/OWL files ready for Protégé / SPARQL
├── shapes/              SHACL validation schemas
├── python_scripts/      Jupyter notebooks for conversion and annotation
└── figures/             Diagrams and logos
```

## Problems covered

| Problem | Objectives | Constraints | Variables |
|---------|-----------|-------------|-----------|
| COBI1   | 2         | 2           | 2         |
| CRE31   | 2         | 2           | 3         |
| MW1     | 2         | 1           | 30        |

## Algorithms

16 algorithm implementations across platforms PlatEMO, pymoo, jMetal, jMetalPy, CMA, pyMOODE, and custom author implementations:
BiCo, CCMO, COMO-CMA, CSOP-RS, DMulti-MADS, GDE3, ILS, MCCMO, MOEADD, MO-CMA, MO-COBYLA, NSGA-II, RS, SMS-EMOA, SPEA2.

## Quick start

1. Open `python_scripts/convert_jsonld_to_rdf.ipynb` to convert JSON-LD metadata to RDF/OWL.
2. Open `python_scripts/experiment_data_annotation.ipynb` to annotate CSV experiment results.
3. Load generated `.owl` / `.rdf` files from `data/annotations/` into Protégé together with `ontology/COMON.owl`.

## Key documents

- `Algorithm_taxonomy_COMON_2025-10-14.pdf` — algorithm taxonomy overview
- `COMON_Definitions.xlsx` — term and concept definitions
