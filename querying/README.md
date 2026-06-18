# Querying the COMON Knowledge Base

The COMON KB consists of **3 separate datasets**, each hosted on its own SPARQL endpoint. Because all three are built on the same COMON ontology vocabulary, they are fully interoperable — the same query runs against any of them and results can be seamlessly integrated.

| Dataset | SPARQL Endpoint | Contents |
|---------|----------------|----------|
| COMON | `http://semanticannotations.ijs.si:3030/COMON/sparql` | All metadata and experiment data for 14 algorithms across 3 problem instances |
| COMON_gde3 | `http://semanticannotations.ijs.si:3030/COMON_gde3/sparql` | Experiment data for GDE3 on 3 problem instances (3 experiments) |
| COMON_dmulti-mads | `http://semanticannotations.ijs.si:3030/COMON_dmulti-mads/sparql` | Experiment data for DMulti-MADS on 3 problem instances (3 experiments) |

> When querying experiment data, send the same query to each endpoint and merge the results. The COMON REST API does this automatically.


## REST API

The COMON KB is accessible through a REST API via simple HTTP GET requests. While the approach above offers full flexibility to express any custom query over the SPARQL endpoints, the REST API provides a set of predefined, structured endpoints designed for users who are not proficient in SPARQL — no knowledge of RDF or query languages is required.

Full API documentation: [https://kostovskaana.github.io/COMON/querying/index.html](https://kostovskaana.github.io/COMON/querying/index.html)


## How to run SPARQL queries directly

1. Go to [YASGUI](https://yasgui.triply.cc/)
2. Set the endpoint URL — see which endpoint to use below
3. Paste and run a query from the examples below

**Which endpoint to use:**
- For all metadata queries (problems, algorithms, experiments, provenance) — use the **COMON** endpoint, as it contains the complete metadata.
- For experiment execution data — run the same query against **all three endpoints** separately and integrate the results, since execution data is split across three datasets.

---

## Example queries

### List all CMO problems

```sparql
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX COMON:   <http://w3id.org/COMON/>

SELECT ?problem ?label
WHERE {
  ?problem rdf:type COMON:COMON_000018 ;
           rdfs:label ?label .
}
ORDER BY ?label
```

---

### List all CMO algorithms

Returns each algorithm instance along with its specific algorithm class.

```sparql
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl:   <http://www.w3.org/2002/07/owl#>
PREFIX COMON: <http://w3id.org/COMON/>

SELECT ?algorithm ?label ?algorithm_class
WHERE {
  ?subClass rdfs:subClassOf* COMON:COMON_000001 .

  ?algorithm rdf:type ?subClass ;
             rdfs:label ?label .

  FILTER(isIRI(?algorithm))
  OPTIONAL { ?subClass rdfs:label ?algorithm_class . }
}
ORDER BY ?label
```

---

### List all CMO experiments

```sparql
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl:   <http://www.w3.org/2002/07/owl#>
PREFIX COMON: <http://w3id.org/COMON/>

SELECT ?experiment ?label
WHERE {
  ?experiment rdf:type COMON:COMON_000002 ;
              rdfs:label ?label .
}
ORDER BY ?label
```

---

### Get all details for a specific problem

Replace `"cobi1_problem"` with the label of the problem you want to query (e.g. `"cre31_problem"`, `"mw1_problem"`).

```sparql
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX COMON:  <http://w3id.org/COMON/>
PREFIX OBO:    <http://purl.obolibrary.org/obo/>
PREFIX OPTION: <http://w3id.org/ontoopt/>
PREFIX dc:     <http://purl.org/dc/elements/1.1/>
PREFIX dcat:   <http://www.w3.org/ns/dcat#>

SELECT ?identifier
       ?numObjectives ?numConstraints ?dimensionality
       ?gradientAvailability ?numFidelityLevels ?noise
       ?paretoFront ?nadir ?ideal
       (GROUP_CONCAT(DISTINCT ?keyword; SEPARATOR="; ") AS ?keywords)
       (GROUP_CONCAT(DISTINCT CONCAT(?variableLabel, " (", ?variableTypeLabel, ")"); SEPARATOR="; ") AS ?variables)
       ?familyLabel ?suiteLabel
WHERE {
  ?problem rdfs:label "cobi1_problem" .

  OPTIONAL { ?problem dc:identifier                ?identifier           . }
  OPTIONAL { ?problem dcat:keyword                 ?keyword              . }
  OPTIONAL { ?problem OPTION:number_of_objectives  ?numObjectives        . }
  OPTIONAL { ?problem OPTION:number_of_constraints ?numConstraints       . }
  OPTIONAL { ?problem OPTION:has_dimensionality    ?dimensionality       . }
  OPTIONAL { ?problem COMON:COMON_000032           ?gradientAvailability . }
  OPTIONAL { ?problem COMON:COMON_000033           ?numFidelityLevels    . }
  OPTIONAL { ?problem COMON:COMON_000034           ?noise                . }
  OPTIONAL { ?problem COMON:COMON_000035           ?paretoFront          . }
  OPTIONAL { ?problem COMON:COMON_000037           ?nadir                . }
  OPTIONAL { ?problem COMON:COMON_000038           ?ideal                . }

  OPTIONAL {
    ?problem OBO:BFO_0000051 ?variable .
    ?variable rdf:type ?variableClass .
    ?variableClass rdfs:subClassOf* COMON:COMON_000039 .
    FILTER(?variableClass != COMON:COMON_000039)
    ?variable rdfs:label ?variableLabel .
    ?variableClass rdfs:label ?variableTypeLabel .
  }

  OPTIONAL { ?problem COMON:COMON_000044 ?family . ?family rdfs:label ?familyLabel . }
  OPTIONAL { ?problem COMON:COMON_000052 ?suite  . ?suite  rdfs:label ?suiteLabel  . }
}
GROUP BY ?identifier ?numObjectives ?numConstraints ?dimensionality
         ?gradientAvailability ?numFidelityLevels ?noise
         ?paretoFront ?nadir ?ideal ?familyLabel ?suiteLabel
```

---

### Get objective details for a specific problem

Returns label, normalization bounds, and weight for each objective of the problem. Replace `"cobi1_problem"` with the label of the problem you want to query (e.g. `"cre31_problem"`, `"mw1_problem"`).

```sparql
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX COMON:  <http://w3id.org/COMON/>
PREFIX OBO:    <http://purl.obolibrary.org/obo/>
PREFIX OPTION: <http://w3id.org/ontoopt/>
PREFIX dc:     <http://purl.org/dc/elements/1.1/>
PREFIX dcat:   <http://www.w3.org/ns/dcat#>

SELECT ?objectiveLabel ?normalization_min ?normalization_max ?weight
WHERE {
  ?problem rdfs:label "cobi1_problem" .
  ?problem OBO:BFO_0000051 ?objective .
  ?objective rdf:type COMON:COMON_000026 .
  ?objective rdfs:label ?objectiveLabel .

  OPTIONAL { ?objective COMON:COMON_000028 ?normalization_min    . }  
  OPTIONAL { ?objective COMON:COMON_000029 ?normalization_max    . }  
  OPTIONAL { ?objective COMON:COMON_000030 ?weight . } 
}
ORDER BY ?objectiveLabel
```

---

### Get constraint details for a specific problem

Returns label, normalization bounds, weight, form (equality/inequality), and strictness (hard/soft) for each constraint. Replace `"cobi1_problem"` with the label of the problem you want to query (e.g. `"cre31_problem"`, `"mw1_problem"`).

```sparql
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX COMON:  <http://w3id.org/COMON/>
PREFIX OBO:    <http://purl.obolibrary.org/obo/>
PREFIX OPTION: <http://w3id.org/ontoopt/>
PREFIX dc:     <http://purl.org/dc/elements/1.1/>
PREFIX dcat:   <http://www.w3.org/ns/dcat#>

SELECT ?constraintLabel ?normalization_max ?weight ?form ?strictness
WHERE {
  ?problem rdfs:label "cobi1_problem" .
  ?problem OBO:BFO_0000051 ?constraint .
  ?constraint rdf:type COMON:COMON_000027 .
  ?constraint rdfs:label ?constraintLabel .

  OPTIONAL { ?constraint COMON:COMON_000029 ?normalization_max    . }  
  OPTIONAL { ?constraint COMON:COMON_000030 ?weight . }  

  OPTIONAL {
    ?constraint COMON:COMON_000054 ?formInd .
    ?formInd rdfs:label ?form .                          # equality / inequality
  }
  OPTIONAL {
    ?constraint COMON:COMON_000055 ?strictnessInd .
    ?strictnessInd rdfs:label ?strictness .              # hard / soft
  }
}
ORDER BY ?constraintLabel
```

---

### List all performance indicators for a specific problem

Groups indicator inputs and their values by indicator type. Replace `"cobi1_problem"` with the label of the problem you want to query (e.g. `"cre31_problem"`, `"mw1_problem"`).

```sparql
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX COMON:  <http://w3id.org/COMON/>
PREFIX OBO:    <http://purl.obolibrary.org/obo/>
PREFIX OPTION: <http://w3id.org/ontoopt/>

SELECT ?indicator
       ?indicatorType
       (GROUP_CONCAT(DISTINCT CONCAT(?inputTypeLabel, ": ", STR(?inputValue)); SEPARATOR=" | ") AS ?description)
WHERE {
  ?problem rdfs:label "cobi1_problem" .

  ?indicator OBO:IAO_0000136 ?problem .

  ?indicator rdf:type ?indicatorClass .
  ?indicatorClass rdfs:label ?indicatorType .
  FILTER(?indicatorClass != owl:NamedIndividual)

  OPTIONAL { ?indicator rdfs:label ?indicatorLabel . }

  OPTIONAL {
    ?indicator OBO:OBI_0000293 ?input .
    ?input rdf:type ?inputClass .
    ?inputClass rdfs:label ?inputTypeLabel .
    FILTER(?inputClass != owl:NamedIndividual)
    OPTIONAL { ?input OPTION:has_value ?inputValue . }
  }
}
GROUP BY ?indicator ?indicatorLabel ?indicatorType
ORDER BY ?indicatorType
```

---

### Get details for a specific algorithm

Returns the algorithm type, implementation platform, programming language, algorithm family, and related algorithms. Replace `"Bico algorithm"` with the label of the algorithm you want.

```sparql
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX COMON:  <http://w3id.org/COMON/>
PREFIX OBO:    <http://purl.obolibrary.org/obo/>

SELECT ?algorithmLabel
       ?algorithmType
       ?platformLabel
       ?programmingLanguageLabel
       ?familyLabel
       ?relatedAlgorithmLabel
WHERE {
  # Anchor: algorithm by label
  ?algorithm rdfs:label "Bico algorithm" .

  # Algorithm type (walk up subclass hierarchy to get the label)
  ?algorithm rdf:type ?algorithmClass .
  ?algorithmClass rdfs:subClassOf* COMON:COMON_000001 .   # subclass of CMO algorithm
  FILTER(?algorithmClass != COMON:COMON_000001)
  ?algorithmClass rdfs:label ?algorithmType .

  OPTIONAL { ?algorithm rdfs:label ?algorithmLabel . }

  # Implementation (has-specified-output OBI_0000297)
  OPTIONAL {
    ?algorithm OBO:OBI_0000297 ?implementation .
    ?implementation rdfs:label ?implementationLabel .

    # Platform that is-about this implementation (IAO_0000136)
    OPTIONAL {
      ?platform OBO:IAO_0000136 ?implementation .
      ?platform rdfs:label ?platformLabel .

      # Programming language used by the platform
      OPTIONAL {
        ?platform COMON:COMON_000068 ?language .
        ?language rdfs:label ?programmingLanguageLabel .
      }
    }
  }

  # Algorithm family (isMemberOfAlgorithmFamily)
  OPTIONAL {
    ?algorithm COMON:COMON_000066 ?family .
    ?family rdfs:label ?familyLabel .
  }

  # Related algorithm (isRelatedToAlgorithm)
  OPTIONAL {
    ?algorithm COMON:COMON_000067 ?relatedAlgorithm .
    ?relatedAlgorithm rdfs:label ?relatedAlgorithmLabel .
  }
}
```

---

### Get provenance information for a specific experiment dataset

Replace `"bico_cobi1_final_platemo_experiment"` with the label of the experiment you want.

```sparql
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX COMON:   <http://w3id.org/COMON/>
PREFIX OBO:     <http://purl.obolibrary.org/obo/>
PREFIX dcat:    <http://www.w3.org/ns/dcat#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX adms:    <http://www.w3.org/ns/adms#>
PREFIX foaf:    <http://xmlns.com/foaf/0.1/>
PREFIX vcard:   <http://www.w3.org/2006/vcard/ns#>

SELECT ?dataset ?version 
       (GROUP_CONCAT(DISTINCT ?keyword;     SEPARATOR="; ") AS ?keywords)
       (GROUP_CONCAT(DISTINCT ?creatorName; SEPARATOR="; ") AS ?creators)
       (GROUP_CONCAT(DISTINCT ?contactName; SEPARATOR="; ") AS ?contacts)
       ?versionNotes
WHERE {
  ?experiment rdfs:label "bico_cobi1_final_platemo_experiment" .

  ?execution OBO:OBI_0000308 ?implementation .
  ?experiment OBO:OBI_0000297 ?implementation .
  ?execution OBO:OBI_0000299 ?dataset .

  OPTIONAL { ?dataset dcat:version      ?version      . }
  OPTIONAL { ?dataset dcat:keyword      ?keyword      . }
  OPTIONAL { ?dataset adms:versionNotes ?versionNotes . }

  OPTIONAL {
    ?dataset dcterms:creator ?creator .
    ?creator foaf:name ?creatorName .
  }
  OPTIONAL {
    ?dataset dcat:contactPoint ?contact .
    ?contact vcard:fn ?contactName .
  }
}
GROUP BY ?dataset ?version ?versionNotes
```

---

### Query experiment execution data

Retrieves per-run, per-iteration, per-evaluation performance indicator values. Adjust the `FILTER` values and indicator type to narrow the results.

- Valid indicator types: `"HV"`, `"IGDPlus"`, `"CV"`, `"ICMOP"`
- Experiment data is distributed across all three endpoints — send the same query to each and merge the results.

```sparql
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX COMON:  <http://w3id.org/COMON/>
PREFIX OBO:    <http://purl.obolibrary.org/obo/>
PREFIX OPTION: <http://w3id.org/ontoopt/>
PREFIX dc:     <http://purl.org/dc/elements/1.1/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>

SELECT ?experimentExecution
       ?runId
       ?iterationId
       ?evalId
       ?indicator
       ?indicatorValue
WHERE {
  # ── Anchor: experiment execution ──────────────────────────────────────────
  ?experimentExecution OBO:BFO_0000051     ?algorithmExecution .
  ?algorithmExecution  rdf:type            COMON:COMON_000006 .
  ?algorithmExecution  dc:identifier       ?runId .
  FILTER(?runId = 1)                                            #  filter by run

  # ── Iteration ─────────────────────────────────────────────────────────────
  ?algorithmExecution  OBO:BFO_0000051     ?iterationExecution .
  ?iterationExecution  rdf:type            COMON:COMON_000011 .
  ?iterationExecution  COMON:COMON_000031  ?iterationId .
  FILTER(?iterationId = 1)                                    #  filter by iteration

  # ── Solution evaluation ───────────────────────────────────────────────────
  ?iterationExecution  OBO:BFO_0000051     ?solutionEvaluation .
  ?solutionEvaluation  rdf:type            COMON:COMON_000012 .

  # ── Performance indicator execution ───────────────────────────────────────
  ?solutionEvaluation  OBO:BFO_0000051     ?piExecution .
  ?piExecution         rdf:type            COMON:COMON_000007 .
  ?piExecution         rdfs:label          ?piExecutionLabel .
  FILTER(CONTAINS(?piExecutionLabel, "HV"))                  #  filter by indicator type: "IGDPlus", "HV", "CV", "ICMOP"

  BIND(xsd:integer(REPLACE(?piExecutionLabel, "^.*_eval-([0-9]+)\\.0_.*$", "$1")) AS ?evalId)
  FILTER(?evalId = 1)                                       #  filter by eval

  BIND(REPLACE(?piExecutionLabel, "^.*_eval-[0-9]+\\.0_(.+)-performance-indicator-execution$", "$1") AS ?indicator)

  # ── Datum value ───────────────────────────────────────────────────────────
  ?piExecution OBO:OBI_0000299  ?datum .
  ?datum       OPTION:has_value ?indicatorValue .
  FILTER(?indicatorValue >= 0.01)                                #  filter by value

}
ORDER BY ?experimentExecution ?runId ?iterationId ?evalId
LIMIT 100
```

---


