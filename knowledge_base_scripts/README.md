# knowledge_base_scripts/

Contains Jupyter notebooks for ontology inference, metadata validation and conversion, and experiment data annotation.

## Files

| File | Description |
|------|-------------|
| `generate_inferred_ontology_versions.ipynb` | Runs OWL RL reasoning over `COMON.owl` and serialises the materialised ontology to `COMON-inferred.owl` |
| `convert_jsonld_to_rdf.ipynb` | Validates JSON-LD metadata files against SHACL shapes and converts conforming files to RDF/XML (`.owl`) |
| `experiment_data_annotation.ipynb` | Converts raw experiment CSV files into RDF graphs using COMON vocabulary and writes the output as RDF/XML |

---

## `generate_inferred_ontology_versions.ipynb`

Loads `COMON.owl` with rdflib, applies OWL RL reasoning via `owlrl.DeductiveClosure`, and writes the result to `ontology/COMON-inferred.owl`.

**Dependencies:** `rdflib`, `owlrl`

---

## `convert_jsonld_to_rdf.ipynb`

Processes three categories of metadata — problems, algorithms, and experiments — stored as JSON-LD files under `data/raw_data/metadata/`. For each file it:

1. Validates the graph against the corresponding SHACL shapes file in `shapes/`.
2. Skips the file and prints validation errors if SHACL conformance fails.
3. Parses the JSON-LD and serialises it to RDF/XML in the matching subfolder under `data/annotations/RDFannotations/`.

| Metadata category | Input folder | SHACL shapes file | Output folder |
|-------------------|-------------|-------------------|---------------|
| Problem | `metadata/problem_metadata/` | `COMON_problem_shapes.ttl` | `RDFannotations/problem_metadata/` |
| Algorithm | `metadata/algorithm_metadata/` | `COMON_algorithm_shapes.ttl` | `RDFannotations/algorithm_metadata/` |
| Experiment | `metadata/experiment_metadata/` | `COMON_experiment_shapes.ttl` | `RDFannotations/experiment_metadata/` |

**Dependencies:** `rdflib`, `pyshacl`

---

## `experiment_data_annotation.ipynb`

Reads raw experiment result CSV files from `data/raw_data/experiment_data/` and converts each one into an RDF graph conforming to the COMON ontology. 

URIs for algorithm implementations and performance indicator implementations are resolved from the corresponding experiment metadata JSON-LD file. Individual URIs are generated deterministically using MD5 hashes of their labels. Large graphs are split into multiple parts at a configurable triple threshold (default 5 000 000) before serialisation.

Output files are written as RDF/XML to `data/annotations/RDFannotations/experiment_data/`, named `experiment_data_<csv_basename>_part<n>.rdf`.

**Dependencies:** `rdflib`
