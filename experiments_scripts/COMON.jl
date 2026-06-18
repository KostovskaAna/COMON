# run_dmultimads_from_fastapi.jl
#
# Assumes your FastAPI server is running, e.g.:
#   uvicorn service:app --host 127.0.0.1 --port 8000
#
# Usage:
#   julia --project=./../../../DMultiMadsPB run_dmultimads_from_fastapi.jl
#
# Notes:
# - Uses HTTP GET /meta and POST /eval to build a BBProblem for DMultiMadsPB.
# - Saves the DMultiMADS cache to one file per problem per replicate.

import Pkg
Pkg.activate("./../../../DMultiMadsPB")

import DMultiMadsPB

using Random
using HTTP
using JSON3
using Printf
using Dates

# ----------------------------
# Config
# ----------------------------
const BASE_URL = get(ENV, "CMOP_BASE_URL", "http://127.0.0.1:8000")
const PROBLEMS = ["COBI1", "CRE31", "MW1"]

# Replicates / runs per problem (adjust as needed)
const N_RUNS_PER_PROBLEM = 15

# DMultiMADS settings
const SEED = 123
const DISPLAY = true
const MAX_EVALS_MULTIPLIER = 10_000  # neval_bb_max = multiplier * n_var

# Output folder
const OUTDIR = "dmultimads_results"
isdir(OUTDIR) || mkpath(OUTDIR)

# ----------------------------
# HTTP helpers
# ----------------------------
function http_get_json(url::String; retries::Int=3, timeout_s::Int=30)
    for k in 1:retries
        try
            r = HTTP.get(url; readtimeout=timeout_s)
            r.status == 200 || error("GET $url failed with status $(r.status): $(String(r.body))")
            return JSON3.read(String(r.body))
        catch e
            if k == retries
                rethrow(e)
            end
        end
    end
    error("Unreachable")
end

function http_post_json(url::String, body_obj; retries::Int=3, timeout_s::Int=30)
    body = JSON3.write(body_obj)
    headers = ["Content-Type" => "application/json"]
    for k in 1:retries
        try
            r = HTTP.post(url, headers, body; readtimeout=timeout_s)
            r.status == 200 || error("POST $url failed with status $(r.status): $(String(r.body))")
            return JSON3.read(String(r.body))
        catch e
            if k == retries
                rethrow(e)
            end
        end
    end
    error("Unreachable")
end

# ----------------------------
# CMOP client
# ----------------------------
function get_meta(problem::String)
    url = "$(BASE_URL)/meta?problem=$(HTTP.escapeuri(problem))"
    j = http_get_json(url)
    n_var    = Int(j["n_var"])
    n_obj    = Int(j["n_obj"])
    n_constr = Int(j["n_constr"])
    xl       = Vector{Float64}(j["xl"])
    xu       = Vector{Float64}(j["xu"])
    name     = String(j["name"])
    return (name=name, n_var=n_var, n_obj=n_obj, n_constr=n_constr, xl=xl, xu=xu)
end

function eval_one(problem::String, x::Vector{Float64})
    url = "$(BASE_URL)/eval?problem=$(HTTP.escapeuri(problem))"
    j = http_post_json(url, (; x=x))
    F = Vector{Float64}(j["F"])
    G = Vector{Float64}(j["G"])
    return F, G
end

# ----------------------------
# Utilities
# ----------------------------
function random_point(rng::AbstractRNG, xl::Vector{Float64}, xu::Vector{Float64})
    n = length(xl)
    x = Vector{Float64}(undef, n)
    @inbounds for i in 1:n
        x[i] = xl[i] + rand(rng) * (xu[i] - xl[i])
    end
    return x
end

# ----------------------------
# Main loop
# ----------------------------
@info "CMOP base URL: $BASE_URL"
health = http_get_json("$(BASE_URL)/health")
@info "Server health: $(health["status"])"

for prob in PROBLEMS
    meta = get_meta(prob)

    n_var    = meta.n_var
    n_obj    = meta.n_obj
    n_constr = meta.n_constr
    xl       = meta.xl
    xu       = meta.xu
    name     = meta.name

    types = [fill(DMultiMadsPB.OBJ, n_obj); fill(DMultiMadsPB.CSTR, n_constr)]

    @info "Problem $name: n_var=$n_var, n_obj=$n_obj, n_constr=$n_constr"

    for run_id in 1:N_RUNS_PER_PROBLEM
        outfile = joinpath(OUTDIR, @sprintf("dmultimads_run=%03d_%s.txt", run_id, name))

        if isfile(outfile)
            @info "Skipping $outfile (already exists)."
            continue
        end

        # Per-run RNG (deterministic across runs if you keep SEED fixed)
        rng = MersenneTwister(SEED + run_id)

        # Blackbox mapping x -> [f...; g...]
        bb = (x::Vector{Float64}) -> begin
            F, G = eval_one(name, x)
            return vcat(F, G)
        end

        bb_problem = DMultiMadsPB.BBProblem(
            bb,
            n_var,
            n_obj + n_constr,
            types;
            lvar = xl,
            uvar = xu,
            name = name
        )

        model = DMultiMadsPB.MadsModel(bb_problem)
        model.params.seed = SEED + run_id
        model.options.display = DISPLAY
        model.options.neval_bb_max = MAX_EVALS_MULTIPLIER * n_var

        x0 = random_point(rng, xl, xu)
        @info "Running $name (run $run_id). Output: $outfile"
        DMultiMadsPB.solve!(model, [x0])

        DMultiMadsPB.save_cache(model.cache, outfile)
    end
end

@info "Done. Results in: $OUTDIR"
