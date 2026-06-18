package com.org.runner;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.uma.jmetal.component.algorithm.EvolutionaryAlgorithm;
import org.uma.jmetal.component.algorithm.multiobjective.NSGAIIBuilder;
import org.uma.jmetal.component.catalogue.common.termination.impl.TerminationByEvaluations;
import org.uma.jmetal.operator.crossover.CrossoverOperator;
import org.uma.jmetal.operator.crossover.impl.SBXCrossover;
import org.uma.jmetal.operator.mutation.MutationOperator;
import org.uma.jmetal.operator.mutation.impl.PolynomialMutation;
import org.uma.jmetal.problem.doubleproblem.impl.AbstractDoubleProblem;
import org.uma.jmetal.solution.doublesolution.DoubleSolution;
import org.uma.jmetal.util.JMetalLogger;
import org.uma.jmetal.util.observable.Observable;
import org.uma.jmetal.util.observer.Observer;
import org.uma.jmetal.util.comparator.dominanceComparator.impl.DominanceWithConstraintsComparator;
import org.uma.jmetal.util.ranking.impl.FastNonDominatedSortRanking;

import java.io.BufferedWriter;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Duration;
import java.util.*;


/**
 * Runs constrained NSGA-II on Python/PyMOO-backed problems:
 *
 *   COBI1, CRE31, MW1
 *
 * Important constraint convention:
 *
 *   PyMOO:
 *      feasible if G <= 0
 *
 *   jMetal:
 *      feasible if solution.constraints()[i] >= 0
 *      violation if solution.constraints()[i] < 0
 *
 * Therefore:
 *
 *   jMetal constraint = -PyMOO G
 *
 * The CSV still stores the original PyMOO-style G values, so downstream
 * feasibility filtering should use:
 *
 *   g_i <= 0
 */
public class NSGAIIOnPyMooCMOPRunner {

    private static final int RUNS = 15;
    private static final int POPULATION_SIZE = 100;
    private static final int EVALS_PER_DIM = 10_000;

    private static final String PY_SERVER_BASE_URL = "http://127.0.0.1:8000";

    private static final List<String> PROBLEMS = List.of("COBI1", "CRE31", "MW1");

    private static final Path OUTPUT_DIR = Path.of(".");

    private static final boolean CHECK_CONSTRAINT_SIGN = false;


    public static final class PopulationCsvObserver implements Observer<Map<String, Object>> {
        private final BufferedWriter writer;
        private final int populationSize;
        private final int runNumber;
        private final int numberOfObjectives;
        private final int numberOfConstraints;

        private int lastGenerationWritten = Integer.MIN_VALUE;

        public PopulationCsvObserver(
                BufferedWriter writer,
                int populationSize,
                int runNumber,
                int numberOfObjectives,
                int numberOfConstraints
        ) {
            this.writer = Objects.requireNonNull(writer, "writer");
            this.populationSize = populationSize;
            this.runNumber = runNumber;
            this.numberOfObjectives = Math.max(0, numberOfObjectives);
            this.numberOfConstraints = Math.max(0, numberOfConstraints);
        }

        @Override
        @SuppressWarnings("unchecked")
        public void update(Observable<Map<String, Object>> observable, Map<String, Object> data) {
            Integer evaluations = (Integer) data.get("EVALUATIONS");
            List<DoubleSolution> population = (List<DoubleSolution>) data.get("POPULATION");

            if (evaluations == null || population == null || population.isEmpty()) {
                return;
            }

            if (population.size() != populationSize) {
                return;
            }

            int generation = computeGeneration(evaluations, populationSize);

            if (generation == lastGenerationWritten) {
                return;
            }

            lastGenerationWritten = generation;

            try {
                for (DoubleSolution s : population) {
                    writeSolutionRow(s, evaluations, generation);
                }
                writer.flush();
            } catch (IOException e) {
                throw new RuntimeException("Failed writing CSV snapshot.", e);
            }
        }

        private static int computeGeneration(int evaluations, int populationSize) {
            int gen = (evaluations - populationSize) / populationSize;
            return Math.max(gen, 0);
        }

        private void writeSolutionRow(DoubleSolution s, int evaluations, int generation) throws IOException {
            StringBuilder sb = new StringBuilder(256);

            double[] objs = s.objectives();

            for (int i = 0; i < numberOfObjectives; i++) {
                double v = (objs != null && i < objs.length) ? objs[i] : Double.NaN;
                sb.append(v).append(',');
            }

            for (int i = 0; i < numberOfConstraints; i++) {
                Object value = s.attributes().get("pymoo_g" + i);
                double v = value instanceof Number ? ((Number) value).doubleValue() : Double.NaN;
                sb.append(v).append(',');
            }

            sb.append(evaluations).append(',');
            sb.append(generation).append(',');
            sb.append(runNumber);

            writer.write(sb.toString());
            writer.newLine();
        }
    }


    private static String buildHeader(int numberOfObjectives, int numberOfConstraints) {
        StringBuilder sb = new StringBuilder(256);

        for (int i = 1; i <= Math.max(0, numberOfObjectives); i++) {
            sb.append("f").append(i).append(',');
        }

        for (int i = 1; i <= Math.max(0, numberOfConstraints); i++) {
            sb.append("g").append(i).append(',');
        }

        sb.append("evaluations,");
        sb.append("generation,");
        sb.append("run");

        return sb.toString();
    }


    public static final class PythonBackedDoubleProblem extends AbstractDoubleProblem {
        private final String problemName;
        private final URI baseUri;

        private final HttpClient http;
        private final ObjectMapper mapper;

        private final int nVar;
        private final int nObj;
        private final int nCon;

        public PythonBackedDoubleProblem(String baseUrl, String problemName) {
            this.problemName = Objects.requireNonNull(problemName, "problemName");

            String cleanBaseUrl = Objects.requireNonNull(baseUrl, "baseUrl");
            if (cleanBaseUrl.endsWith("/")) {
                cleanBaseUrl = cleanBaseUrl.substring(0, cleanBaseUrl.length() - 1);
            }

            this.baseUri = URI.create(cleanBaseUrl);

            this.http = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(5))
                    .build();

            this.mapper = new ObjectMapper();

            JsonNode meta = getJson("/meta?problem=" + urlEncode(problemName));

            this.nVar = requiredInt(meta, "n_var");
            this.nObj = requiredInt(meta, "n_obj");
            this.nCon = requiredInt(meta, "n_constr");

            numberOfObjectives(nObj);
            numberOfConstraints(nCon);

            JsonNode xl = meta.get("xl");
            JsonNode xu = meta.get("xu");

            if (
                    xl == null ||
                            xu == null ||
                            !xl.isArray() ||
                            !xu.isArray() ||
                            xl.size() != nVar ||
                            xu.size() != nVar
            ) {
                throw new IllegalStateException(
                        "Invalid bounds from /meta for problem=" + problemName + ", meta=" + meta
                );
            }

            List<Double> lb = new ArrayList<>(nVar);
            List<Double> ub = new ArrayList<>(nVar);

            for (int i = 0; i < nVar; i++) {
                lb.add(xl.get(i).asDouble());
                ub.add(xu.get(i).asDouble());
            }

            variableBounds(lb, ub);
        }

        @Override
        public DoubleSolution evaluate(DoubleSolution solution) {
            List<Double> vars = solution.variables();
            double[] x = new double[vars.size()];

            for (int i = 0; i < vars.size(); i++) {
                x[i] = vars.get(i);
            }

            String path = "/eval?problem=" + urlEncode(problemName);
            JsonNode resp = postJson(path, Map.of("x", x));

            JsonNode F = resp.get("F");
            JsonNode G = resp.get("G");

            if (F == null || !F.isArray() || F.size() < nObj) {
                throw new IllegalStateException(
                        "Invalid F from Python for problem=" + problemName + ", resp=" + resp
                );
            }

            for (int i = 0; i < nObj; i++) {
                solution.objectives()[i] = F.get(i).asDouble();
            }

            if (nCon > 0) {
                if (G == null || !G.isArray() || G.size() < nCon) {
                    throw new IllegalStateException(
                            "Invalid G from Python for problem=" + problemName + ", resp=" + resp
                    );
                }

                boolean pymooFeasible = true;
                boolean jMetalFeasible = true;

                for (int i = 0; i < nCon; i++) {
                    double pymooG = G.get(i).asDouble();

                    /*
                     * Keep original PyMOO constraint for CSV:
                     *
                     *   feasible if pymooG <= 0
                     */
                    solution.attributes().put("pymoo_g" + i, pymooG);

                    /*
                     * Convert to jMetal convention:
                     *
                     *   feasible if constraint >= 0
                     *   violated if constraint < 0
                     */
                    double jMetalConstraint = -pymooG;
                    solution.constraints()[i] = jMetalConstraint;

                    if (pymooG > 0.0) {
                        pymooFeasible = false;
                    }

                    if (jMetalConstraint < 0.0) {
                        jMetalFeasible = false;
                    }
                }

                if (CHECK_CONSTRAINT_SIGN && pymooFeasible != jMetalFeasible) {
                    throw new IllegalStateException(
                            "Constraint sign conversion failed for problem=" + problemName +
                                    ", PyMOO G=" + G +
                                    ", jMetal constraints=" + Arrays.toString(solution.constraints())
                    );
                }
            }

            return solution;
        }

        @Override
        public String name() {
            return "PyMOO(" + problemName + ")";
        }

        public int objectivesCount() {
            return nObj;
        }

        public int constraintsCount() {
            return nCon;
        }

        private JsonNode getJson(String path) {
            try {
                HttpRequest req = HttpRequest.newBuilder(baseUri.resolve(path))
                        .GET()
                        .timeout(Duration.ofSeconds(10))
                        .build();

                HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());

                if (res.statusCode() != 200) {
                    throw new RuntimeException(
                            "GET " + path + " failed: status=" + res.statusCode() + ", body=" + res.body()
                    );
                }

                return mapper.readTree(res.body());

            } catch (IOException e) {
                throw new RuntimeException("GET " + path + " failed", e);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new RuntimeException("GET " + path + " interrupted", e);
            }
        }

        private JsonNode postJson(String path, Object body) {
            try {
                String json = mapper.writeValueAsString(body);

                HttpRequest req = HttpRequest.newBuilder(baseUri.resolve(path))
                        .POST(HttpRequest.BodyPublishers.ofString(json))
                        .header("Content-Type", "application/json")
                        .timeout(Duration.ofSeconds(30))
                        .build();

                HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());

                if (res.statusCode() != 200) {
                    throw new RuntimeException(
                            "POST " + path + " failed: status=" + res.statusCode() + ", body=" + res.body()
                    );
                }

                return mapper.readTree(res.body());

            } catch (IOException e) {
                throw new RuntimeException("POST " + path + " failed", e);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new RuntimeException("POST " + path + " interrupted", e);
            }
        }

        private static int requiredInt(JsonNode node, String field) {
            JsonNode v = node.get(field);

            if (v == null || !v.canConvertToInt()) {
                throw new IllegalStateException("Missing/invalid field '" + field + "' in: " + node);
            }

            return v.asInt();
        }

        private static String urlEncode(String s) {
            return URLEncoder.encode(s, StandardCharsets.UTF_8);
        }
    }


    public static void main(String[] args) throws IOException {
        CrossoverOperator<DoubleSolution> crossover = new SBXCrossover(0.9, 20.0);

        for (String problemName : PROBLEMS) {
            runProblem(problemName, crossover);
        }

        System.out.println(
                "Done. Wrote CSVs into: " + OUTPUT_DIR.toAbsolutePath()
        );
    }


    private static void runProblem(
            String problemName,
            CrossoverOperator<DoubleSolution> crossover
    ) throws IOException {
        PythonBackedDoubleProblem problem =
                new PythonBackedDoubleProblem(PY_SERVER_BASE_URL, problemName);

        double mutationProbability = 1.0 / problem.numberOfVariables();

        MutationOperator<DoubleSolution> mutation =
                new PolynomialMutation(mutationProbability, 20.0);

        int targetEvaluations = EVALS_PER_DIM * problem.numberOfVariables();

        /*
         * Keep evaluation count aligned to whole generations.
         *
         * jMetal component NSGA-II initializes EVALUATIONS as populationSize,
         * then adds offspringPopulationSize each generation.
         */
        int maxEvaluations =
                ((targetEvaluations + POPULATION_SIZE - 1) / POPULATION_SIZE) * POPULATION_SIZE
                        + POPULATION_SIZE;

        int impliedGenerations =
                Math.max(0, (maxEvaluations - POPULATION_SIZE) / POPULATION_SIZE);

        Path outFile =
                OUTPUT_DIR.resolve("NSGA2_" + problemName + "_population_log.csv");

        try (
                BufferedWriter writer = Files.newBufferedWriter(
                        outFile,
                        StandardOpenOption.CREATE,
                        StandardOpenOption.TRUNCATE_EXISTING,
                        StandardOpenOption.WRITE
                )
        ) {
            writer.write(buildHeader(problem.objectivesCount(), problem.constraintsCount()));
            writer.newLine();
            writer.flush();

            JMetalLogger.logger.info(String.format(
                    Locale.US,
                    "Starting problem=%s runs=%d pop=%d maxEvals=%d generations=%d objectives=%d constraints=%d vars=%d",
                    problemName,
                    RUNS,
                    POPULATION_SIZE,
                    maxEvaluations,
                    impliedGenerations,
                    problem.objectivesCount(),
                    problem.constraintsCount(),
                    problem.numberOfVariables()
            ));

            for (int run = 1; run <= RUNS; run++) {
                EvolutionaryAlgorithm<DoubleSolution> algorithm =
                        new NSGAIIBuilder<>(
                                problem,
                                POPULATION_SIZE,
                                POPULATION_SIZE,
                                crossover,
                                mutation
                        )

                                /*
                                 * Critical fix:
                                 *
                                 * Default FastNonDominatedSortRanking uses DefaultDominanceComparator,
                                 * which is objective-only.
                                 *
                                 * This makes NSGA-II rank solutions using:
                                 *
                                 *   1. constraint violation
                                 *   2. objective dominance
                                 */
                                .setRanking(
                                        new FastNonDominatedSortRanking<>(
                                                new DominanceWithConstraintsComparator<>()
                                        )
                                )

                                .setTermination(new TerminationByEvaluations(maxEvaluations))
                                .build();

                algorithm.observable().register(
                        new PopulationCsvObserver(
                                writer,
                                POPULATION_SIZE,
                                run,
                                problem.objectivesCount(),
                                problem.constraintsCount()
                        )
                );

                long startMs = System.currentTimeMillis();

                algorithm.run();

                long elapsedMs = System.currentTimeMillis() - startMs;

                JMetalLogger.logger.info(String.format(
                        Locale.US,
                        "Problem=%s run=%d/%d complete pop=%d maxEvals=%d timeMs=%d",
                        problemName,
                        run,
                        RUNS,
                        POPULATION_SIZE,
                        maxEvaluations,
                        elapsedMs
                ));
            }
        }

        System.out.println(
                "Wrote CSV for " + problemName + ": " + outFile.toAbsolutePath()
        );
    }
}