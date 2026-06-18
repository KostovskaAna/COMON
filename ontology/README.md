# ontology/

Contains the core OWL ontology that defines the COMON vocabulary.

## Files

| File | Description |
|------|-------------|
| `COMON.owl` | Main ontology in RDF/XML format |
| `COMON-inferred.owl` | Inferred version of the ontology with materialised axioms |
| `external/iao.owl` | Local copy of the Information Artifact Ontology (IAO) dependency |

## Loading in Protégé

Open `COMON.owl` directly — the local `external/iao.owl` is used instead of fetching it from the network.

## COMON.owl

**IRI:** `http://w3id.org/COMON/`  
**Version:** 1.0.0

The ontology imports [IAO](http://purl.obolibrary.org/obo/iao.owl) from OBO Foundry and reuses properties from OBI, BFO, Dublin Core, and DCAT.

### Vocabulary

| Local ID | Label | Type | Definition | URI |
|----------|-------|------|------------|-----|
| COMON_000001 | CMO algorithm | Class | An algorithm that is designed to solve constrained multi-objective optimization (CMO) problems by simultaneously optimizing two or more conflicting objective functions subject to one or more constraints, producing a set of feasible trade-off solutions that approximate the constrained Pareto front.| http://w3id.org/COMON/COMON_000001 |
| COMON_000002 | CMO experiment | Class | A planned study in which a CMO algorithm is applied to a multi-objective optimization problem under specified conditions in order to assess, compare, or analyze their behavior and performance.| http://w3id.org/COMON/COMON_000002 |
| COMON_000003 | CMO performance indicator | Class | A measure used to quantify some aspect of the performance of a CMO algorithm or of the quality of the solutions it produces when solving constrained multi-objective optimization problems.| http://w3id.org/COMON/COMON_000003 |
| COMON_000004 | CMO algorithm implementation | Class | A software entity that implements a specific CMO algorithm in a concrete programming language or computational framework.| http://w3id.org/COMON/COMON_000004 |
| COMON_000006 | CMO algorithm execution | Class | A concrete run of a CMO algorithm implementation on a given CMO problem implementation under specified parameter settings and computational conditions.| http://w3id.org/COMON/COMON_000006 |
| COMON_000007 | CMO performance indicator execution | Class | A concrete computation in which a CMO performance indicator implementation is applied to one or more solution sets or execution results in order to produce a performance indicator value.| http://w3id.org/COMON/COMON_000007 |
| COMON_000008 | CMO performance indicator implementation | Class | A software entity that implements a specific CMO performance indicator in a concrete programming language or computational framework.| http://w3id.org/COMON/COMON_000008 |
| COMON_000009 | Up-to-point CMO performance indicator implementation | Class | A CMO performance indicator implementation that computes an indicator value using the full set of solutions accumulated up to a given point during an algorithm execution (e.g., an archive of all evaluated solutions).| http://w3id.org/COMON/COMON_000009 |
| COMON_000010 | Current-only CMO performance indicator implementation | Class | A CMO performance indicator implementation that computes an indicator value using only the current solution set (e.g., the current population) available at a given point during an algorithm execution.| http://w3id.org/COMON/COMON_000010 |
| COMON_000011 | CMO algorithm iteration execution | Class | A single iteration, generation, or step within the execution of a CMO algorithm.| http://w3id.org/COMON/COMON_000011 |
| COMON_000012 | CMO solution evaluation | Class | The act of computing the objective function values and constraint-related values for a candidate solution of a constrained multi-objective optimization problem.| http://w3id.org/COMON/COMON_000012 |
| COMON_000013 | CMO performance indicator datum | Class | A data item representing the value produced by a CMO performance indicator execution.| http://w3id.org/COMON/COMON_000013 |
| COMON_000014 | CMO experiment execution | Class | A concrete enactment of a CMO experiment implementation in which the specified algorithms, problems, indicators, and settings are actually run.| http://w3id.org/COMON/COMON_000014 |
| COMON_000015 | CMO experiment implementation | Class | A software or workflow entity that specifies and operationalizes how a CMO experiment is to be executed.| http://w3id.org/COMON/COMON_000015 |
| COMON_000016 | Optimization problem | Class | A problem in which one seeks values for decision variables that optimize one or more objective functions, possibly subject to constraints.| http://w3id.org/COMON/COMON_000016 |
| COMON_000017 | Multi-objective optimization problem | Class | An optimization problem that involves two or more objective functions to be optimized simultaneously.| http://w3id.org/COMON/COMON_000017 |
| COMON_000018 | CMO problem | Class | A multi-objective optimization problem that includes one or more constraints restricting the feasible decision space.| http://w3id.org/COMON/COMON_000018 |
| COMON_000019 | ICMOP | Class | A CMO performance indicator that measures solution quality over three separate states: infeasible, feasible but within a region of interest, and feasible within the region of interest.| http://w3id.org/COMON/COMON_000019 |
| COMON_000020 | Hypervolume | Class | A CMO performance indicator that measures the size of the objective-space region dominated by a solution set and bounded by a reference point.| http://w3id.org/COMON/COMON_000020 |
| COMON_000021 | IGD+ | Class | A CMO performance indicator that measures the average distance from points in a reference set to the nearest solution in an approximation set using the IGD+ distance formulation.| http://w3id.org/COMON/COMON_000021 |
| COMON_000022 | Mixed CMO performance indicator | Class | A CMO performance indicator that captures both objective-space quality and constraint-related aspects of a solution set or algorithm outcome.| http://w3id.org/COMON/COMON_000022 |
| COMON_000023 | Total constraint violation | Class | A measure of the overall amount by which a solution violates the constraints of a constrained optimization problem.| http://w3id.org/COMON/COMON_000023 |
| COMON_000024 | Objective-specific CMO performance indicator specification | Class | A CMO performance indicator specification that defines how the performance indicator is to be computed for a particular optimization objective.| http://w3id.org/COMON/COMON_000024 |
| COMON_000025 | Constraint-specific CMO performance indicator specification | Class | A CMO performance indicator specification that defines how the performance indicator is to be computed for a particular optimization constraint.| http://w3id.org/COMON/COMON_000025 |
| COMON_000026 | Optimization objective | Class | A function or criterion whose value is to be minimized or maximized in an optimization problem.| http://w3id.org/ontoopt/COMON_000026 |
| COMON_000027 | Optimization constraint | Class | A function-defined condition that candidate solutions of an optimization problem must satisfy in order to be considered feasible.| http://w3id.org/COMON/COMON_000027 |
| COMON_000028 | normalization_min | DataProperty | A data property that specifies the minimum value used to normalize an objective or constraint.| http://w3id.org/COMON/COMON_000028 |
| COMON_000029 | normalization_max | DataProperty | A data property that specifies the maximum value used to normalize an objective or constraint.| http://w3id.org/COMON/COMON_000029 |
| COMON_000030 | weight | DataProperty | A data property that specifies the relative importance assigned to an objective or constraint.| http://w3id.org/COMON/COMON_000030 |
| COMON_000031 | algorithm_iteration_number | AnnotationProperty | An annotation property that records the number identifying a particular iteration, generation, or step within an algorithm execution.| http://w3id.org/COMON/COMON_000031 |
| COMON_000032 | gradientAvailability | DataProperty | A data property that indicates whether gradient information is available for an optimization problem.| http://w3id.org/COMON/COMON_000032 |
| COMON_000033 | numberOfFidelityLevels | DataProperty | A data property that specifies how many fidelity levels are available in a multi-fidelity optimization problem.| http://w3id.org/COMON/COMON_000033 |
| COMON_000034 | noise | DataProperty | A data property that indicates whether an optimization problem is affected by stochastic noise.| http://w3id.org/COMON/COMON_000034 |
| COMON_000035 | paretoFrontApproximation | DataProperty | A data property that specifies an approximation of the Pareto front associated with a problem or solution set.| http://w3id.org/COMON/COMON_000035 |
| COMON_000036 | paretoSetApproximation | DataProperty | A data property that specifies an approximation of the Pareto set associated with a problem or solution set.| http://w3id.org/COMON/COMON_000036 |
| COMON_000037 | nadir | DataProperty | A data property that specifies the nadir point, namely the vector of worst objective values among the Pareto-optimal solutions under consideration.| http://w3id.org/COMON/COMON_000037 |
| COMON_000038 | ideal | DataProperty | A data property that specifies the ideal point, namely the vector of best objective values attainable for each objective under consideration.| http://w3id.org/COMON/COMON_000038 |
| COMON_000039 | Problem variable | Class | A decision variable whose value is to be determined in order to define a candidate solution to an optimization problem.| http://w3id.org/COMON/COMON_000039 |
| COMON_000040 | Continuous problem variable | Class | A problem variable that can take values from a continuous domain.| http://w3id.org/COMON/COMON_000040 |
| COMON_000041 | Ordered problem variable | Class | A problem variable whose possible values are discrete but possess a natural ordering.| http://w3id.org/COMON/COMON_000041 |
| COMON_000042 | Categorical problem variable | Class | A problem variable whose possible values are chosen from a set of categories without an inherent numerical ordering.| http://w3id.org/COMON/COMON_000042 |
| COMON_000043 | Problem family | Class | A collection of optimization problems that share common structural characteristics, generation rules, or intended use.| http://w3id.org/COMON/COMON_000043 |
| COMON_000044 | isMemberOfProblemFamily | ObjectProperty | An object property relating an optimization problem to a problem family of which it is a member.| http://w3id.org/COMON/COMON_000044 |
| COMON_000046 | ConstraintForm | Class | A class characterizing the mathematical form of an optimization constraint (e.g., equality or inequality).| http://w3id.org/COMON/COMON_000046 |
| COMON_000047 | ConstraintStrictness | Class | A class of categories that characterize how strictly an optimization constraint must be satisfied.| http://w3id.org/COMON/COMON_000047 |
| COMON_000048 | equality | NamedIndividual | An individual of the ConstraintForm class representing the constraint form in which the constrained expression must equal a specified value.| http://w3id.org/COMON/COMON_000048 |
| COMON_000049 | inequality | NamedIndividual | An individual of the ConstraintForm class representing the constraint form in which the constrained expression must be less than, greater than, or bounded relative to a specified value.| http://w3id.org/COMON/COMON_000049 |
| COMON_000050 | soft | NamedIndividual | An individual of the ConstraintStrictness class representing a constraint strictness in which violations may be tolerated or penalized rather than absolutely forbidden.| http://w3id.org/COMON/COMON_000050 |
| COMON_000051 | hard | NamedIndividual | An individual of the ConstraintStrictness class representing a constraint strictness in which violations are not allowed and infeasible solutions are excluded or strictly disfavored.| http://w3id.org/COMON/COMON_000051 |
| COMON_000052 | isMemberOfProblemSuite | ObjectProperty | An object property relating an optimization problem to a problem suite of which it is a member.| http://w3id.org/COMON/COMON_000052 |
| COMON_000053 | Problem suite | Class | A class representing a collection of optimization problems assembled and maintained as a benchmark set for experimentation, evaluation, or comparison.| http://w3id.org/COMON/COMON_000053 |
| COMON_000054 | hasConstraintForm | ObjectProperty | An object property relating an optimization constraint to the constraint form that characterizes it.| http://w3id.org/COMON/COMON_000054 |
| COMON_000055 | hasConstraintStrictness | ObjectProperty | An object property relating an optimization constraint to the constraint strictness that characterizes it.| http://w3id.org/COMON/COMON_000055 |
| COMON_000057 | Single-point CMO algorithm | Class | A CMO algorithm that maintains and updates a single candidate solution at a time during its search process.| http://w3id.org/COMON/COMON_000057 |
| COMON_000058 | Single-point CMO algorithm that solves multiple CSOPs | Class | A single-point CMO algorithm that addresses a constrained multi-objective optimization problem by solving multiple constrained single-objective optimization problems.| http://w3id.org/COMON/COMON_000058 |
| COMON_000059 | Single-point CMO algorithm that solves the original CMOP | Class | A single-point CMO algorithm that directly searches on the original constrained multi-objective optimization problem rather than decomposing it into multiple constrained single-objective problems.| http://w3id.org/COMON/COMON_000059 |
| COMON_000060 | Population-based CMO algorithm | Class | A CMO algorithm that maintains and evolves a population of candidate solutions during its search process.| http://w3id.org/COMON/COMON_000060 |
| COMON_000061 | Population CMO algorithm that solves multiple CSOPs | Class | A population-based CMO algorithm that addresses a constrained multi-objective optimization problem by solving multiple constrained single-objective optimization problems.| http://w3id.org/COMON/COMON_000061 |
| COMON_000062 | Population CMO algorithm that solves the original CMOP | Class | A population-based CMO algorithm that directly searches on the original constrained multi-objective optimization problem.| http://w3id.org/COMON/COMON_000062 |
| COMON_000063 | Population algorithm that solves the original CMOP sequentially | Class | A population-based CMO algorithm that solves the original constrained multi-objective optimization problem using a sequential search or update strategy.| http://w3id.org/COMON/COMON_000063 |
| COMON_000064 | Population algorithms that solve the original CMOP in parallel (using subpopulations) | Class | A population-based CMO algorithm that solves the original constrained multi-objective optimization problem in parallel by dividing the search among multiple subpopulations.| http://w3id.org/COMON/COMON_000064 |
| COMON_000065 | Algorithm family | Class | A class representing collection of algorithms that share common design principles, operators, or methodological characteristics.| http://w3id.org/COMON/COMON_000065 |
| COMON_000066 | isMemberOfAlgorithmFamily | ObjectProperty | An object property relating an algorithm to an algorithm family of which it is a member.| http://w3id.org/COMON/COMON_000066 |
| COMON_000067 | isRelatedToAlgorithm | ObjectProperty | An object property relating an entity to an algorithm with which it is associated or conceptually connected.| http://w3id.org/COMON/COMON_000067 |
| COMON_000068 | implementedInLanguage | ObjectProperty | An object property relating a software implementation to the programming language in which it is implemented.| http://w3id.org/COMON/COMON_000068 |
| COMON_000069 | maxNumberOfSolutionEvaluations | DataProperty | A data property that specifies the maximum number of solution evaluations allowed during an experiment execution.| http://w3id.org/COMON/COMON_000069 |
| COMON_000070 | maxTimePerRun | DataProperty | A data property that specifies the maximum execution time allowed for a single run of an experiment.| http://w3id.org/COMON/COMON_000070 |
| COMON_000071 | costModel | DataProperty | A data property that specifies the model or convention used to quantify computational cost in an experiment execution.| http://w3id.org/COMON/COMON_000071 |
| COMON_000072 | stoppingCriteria | DataProperty | A data property that specifies the condition or set of conditions under which an algorithm execution is terminated.| http://w3id.org/COMON/COMON_000072 |
| COMON_000073 | algorithmParameterSettings | DataProperty | A data property that specifies the parameter values used for the particular algorithm specified in the experiment.| http://w3id.org/COMON/COMON_000073 |
| COMON_000074 | Reference set | Class | A set of solutions, points, or vectors used as a standard of comparison in computing one or more performance indicators.| http://w3id.org/COMON/COMON_000074 |
| COMON_000075 | Reference point | Class | A point in objective space used as a parameter or bound in the computation of a performance indicator.| http://w3id.org/COMON/COMON_000075 |
| COMON_000076 | Tau constant | Class | A constant parameter, denoted tau, used in the definition or computation of a the ICMOP performance indicator.| http://w3id.org/COMON/COMON_000076 |
| COMON_000077 | CMO problem implementation | Class | A software entity that implements a specific constrained multi-objective optimization problem in a concrete programming language or computational framework.| http://w3id.org/COMON/COMON_000077 |
| COMON_000078 | uses | ObjectProperty | An object property relating an entity to another entity that it employs, depends on, or makes use of.| http://w3id.org/COMON/COMON_000078 |
| COMON_000080 | CMO experiment log level | Class | A class of levels that characterize the amount or granularity of information recorded during a CMO experiment or execution.| http://w3id.org/COMON/COMON_000080 |
| COMON_000081 | hasLogLevel | ObjectProperty | An object property relating a CMO experiment, execution, or logger to the log level it has.| http://w3id.org/COMON/COMON_000081 |
| COMON_000082 | final | NamedIndividual | An individual of the 'CMO experiment log level' class representing the log level at which information is recorded only at the final stage or outcome of an execution.| http://w3id.org/COMON/COMON_000082 |
| COMON_000083 | generation | NamedIndividual | An individual of the 'CMO experiment log level' class representing the log level at which information is recorded at the end of each generation or iteration group during an execution.| http://w3id.org/COMON/COMON_000083 |
| COMON_000084 | evaluation | NamedIndividual | An individual of the 'CMO experiment log level' class representing the log level at which information is recorded for each solution evaluation during an execution.| http://w3id.org/COMON/COMON_000084 |


