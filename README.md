# COMON — Constrained Multi-Objective Optimization ONtology

This repository contains the COMON ontology, the COMON knowledge base (KB), and the querying infrastructure.

## Repository structure

```
COMON/
├── ontology/                  Core OWL ontology
│   ├── COMON.owl              Ontology in RDF/XML format
│   ├── COMON-inferred.owl     Inferred version
│   └── external/
│       └── iao.owl            Local copy of the IAO dependency
│
├── shapes/                    SHACL validation shapes
│   ├── COMON_algorithm_shapes.ttl
│   ├── COMON_experiment_shapes.ttl
│   └── COMON_problem_shapes.ttl
│
├── data/
│   ├── raw_data/
│   │   ├── metadata/          Source metadata in JSON-LD
│   │   │   ├── algorithm_metadata/
│   │   │   ├── experiment_metadata/
│   │   │   └── problem_metadata/
│   │   ├── experiment_data/   Raw experiment result CSV files
│   │   └── pf/                Pareto front reference data
│   └── annotations/
│       └── RDFannotations/    Validated and converted RDF/XML files
│           ├── algorithm_metadata/
│           ├── experiment_metadata/
│           ├── problem_metadata/
│           └── experiment_data/
│
├── experiments_scripts/        Scripts for implementing algorithms and running experiments
│
├── knowledge_base_scripts/            Jupyter notebooks generating inferred version of the ontology and scripts for data annotation
│   ├── generate_inferred_ontology_versions.ipynb
│   ├── convert_jsonld_to_rdf.ipynb
│   └── experiment_data_annotation.ipynb
│
├── querying/                  Querying infrastructure
│   ├── README.md              SPARQL endpoint descriptions and query examples
│   ├── openapi.yaml           REST API specification
│   └── index.html             REST API documentation (OpenAPI)
│
├── use_cases/                 Use cases
│   ├── UseCaseA.ipynb         Automatic Data Integration
│   └── UseCaseB.ipynb         Comparison of an algorithm across different implementations
│
└── figures/                   Figures and diagrams
```

## Components

**Ontology (`ontology/`)** — The COMON OWL ontology defines the shared vocabulary for CMO algorithms, problems, experiments, and performance indicators. It imports IAO from OBO Foundry and reuses properties from OBI, BFO, Dublin Core, and DCAT. See [ontology/README.md](ontology/README.md).

**SHACL shapes (`shapes/`)** — Validation constraints for the three main metadata categories (algorithms, experiments, problems). All JSON-LD metadata files are validated against these shapes before being converted to RDF.

**Data (`data/`)** — Raw metadata authored in JSON-LD and raw experiment results stored as CSV, together with their validated RDF/XML annotations comprising the COMON KB.

**Experiment scripts (`experiments_scripts/`)** — Scripts for implementing CMO algorithms and running experiments to generate the raw data stored in `data/raw_data/`.

**Knowledge base scripts (`knowledge_base_scripts/`)** — Jupyter notebooks that build the KB: ontology inference, JSON-LD validation and conversion, and experiment data annotation. See [knowledge_base_scripts/README.md](knowledge_base_scripts/README.md).

**Querying infrastructure (`querying/`)** — The COMON KB is hosted on three SPARQL endpoints and exposed through a REST API for users who do not need to write SPARQL. See [querying/README.md](querying/README.md).

**Use cases (`use_cases/`)** — Two notebooks showcasing the usability of the ontology: Use Case A (Automatic Data Integration) and Use Case B (Comparison of an algorithm across different implementations).
