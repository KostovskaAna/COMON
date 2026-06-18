from pymoo.core.problem import ElementwiseProblem
import numpy as np
import itertools
from moarchiving import get_mo_archive
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from qpsolvers import solve_qp
import pickle
import cvxpy as cp
import sympy as sp
import copy
import scipy
from sklearn.cluster import AgglomerativeClustering
from .utils import CMAP, get_grid, plot_linear_constraints, plot_quadratic_constraints, plot_multi_constraints
from queue import PriorityQueue


def create_random_hessian(n_var):
    """ Returns a random positive definite Hessian matrix of shape (n_var, n_var). """
    A = np.random.randn(n_var, n_var)
    symmetric_matrix = np.dot(A, A.T)
    positive_definite_matrix = symmetric_matrix + n_var * np.eye(n_var)
    return positive_definite_matrix


def create_random_hessian_with_condition_number(n_var, cond):
    """ Returns a random Hessian matrix of shape (n_var, n_var) with a condition number in the specified range. """
    low, high = cond
    cond = np.exp(np.random.uniform(np.log(low), np.log(high)))
    lambda_min = 1
    lambda_max = lambda_min * cond
    middle_eigenvalues = np.exp(np.random.uniform(np.log(lambda_min), np.log(lambda_max), n_var - 2))
    eigenvalues = np.concatenate([[lambda_max], middle_eigenvalues, [lambda_min]])
    np.random.shuffle(eigenvalues)
    Q, _ = np.linalg.qr(np.random.randn(n_var, n_var))
    D = np.diag(eigenvalues)
    A = Q @ D @ Q.T
    return A


def choose_number(val: {int, tuple}, name, min_value):
    """
    Validates the input val:
    - If val is a number greater than or equal to min, returns it.
    - If val is a tuple (a, b) where min <= a <= b, returns a random integer v such that a <= v <= b.
    - Otherwise, raises a ValueError.
    """
    if isinstance(val, int) and min_value <= val:
        return val
    elif (isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], int) and isinstance(val[1], int) and
          min_value <= val[0] <= val[1]):
        return np.random.randint(val[0], val[1] + 1)
    else:
        raise ValueError(
            f'Unsupported input for {name}: {val}. Expected an integer greater than or equal to {min_value} or a tuple '
            f'of two integers (a, b), where min <= a <= b.')


def get_shift(val: {int, float, tuple}):
    """
    Validates the input for peaks_value_shift and returns a proper range.
    """
    if isinstance(val, int) or isinstance(val, float):
        return (-val, val)
    elif isinstance(val, tuple) and len(val) == 2 and (isinstance(val[0], int) or isinstance(val[0], float)) and (
            isinstance(val[1], int) or isinstance(val[1], float)) and val[0] <= val[1]:
        return val
    else:
        raise ValueError(
            f'Unsupported input for peaks_value_shift: {val}. Expected a float or a tuple of two floats (min, max).')


def get_size(val: {int, float, tuple}, min, name):
    """
    Validates the input for name and returns a proper range.
    """
    if (isinstance(val, int) or isinstance(val, float)):
        if val < min:
            return (min, min)
        else:
            return (min, val)
    elif isinstance(val, tuple) and len(val) == 2 and (isinstance(val[0], int) or isinstance(val[0], float)) and (
            isinstance(val[1], int) or isinstance(val[1], float)) and val[0] <= val[1]:
        return val
    else:
        raise ValueError(
            f'Unsupported input for {name}: {val}. Expected a positive float or a tuple of two '
            f'positive floats (min, max).')


def get_alpha(val: {int, float, tuple}):
    """
    Validates the input for alpha and returns a proper vector.
    """
    if (isinstance(val, int) or isinstance(val, float)) and 0 < val:
        return np.array([val, val])
    elif isinstance(val, tuple) and len(val) == 2 and (isinstance(val[0], int) or isinstance(val[0], float)) and (
            isinstance(val[1], int) or isinstance(val[1], float)) and 0 < val[0] and 0 < val[1]:
        return np.array(val)
    else:
        raise ValueError(
            f'Unsupported input for alpha: {val}. Expected a positive float or a tuple of two positive floats.')


def peak_function(x, x_star, H):
    """ Evaluates a single peak function at the point x. """
    x_diff = x - x_star
    return 0.5 * np.dot(x_diff.T, np.dot(H, x_diff))


def multi_peak_function(x, centers, Hessians):
    """ Evaluates the multi-peak function at the point x. """
    values = [peak_function(x, centers[i], Hessians[i]) for i in range(len(centers))]
    return np.min(values)


def evaluate_linear_constraint(x, linear_constraint):
    """ Evaluates the given linear constraint at the point x. """
    return np.dot(x - linear_constraint['P'], linear_constraint['n'])


def evaluate_quadratic_constraint(x, quadratic_constraint):
    """ Evaluates the given quadratic constraint at the point x. """
    H, c, b = quadratic_constraint['H'], quadratic_constraint['c'], quadratic_constraint['b']
    return (x - c).T @ H @ (x - c) - b


def evaluate_linear_quadratic_constraints(x, linear_constraints, quadratic_constraints):
    """ Evaluates the given linear and quadratic constraints at the point x. """
    all_constraints = []
    for constraint in linear_constraints:
        all_constraints.append(evaluate_linear_constraint(x, constraint))
    for constraint in quadratic_constraints:
        all_constraints.append(evaluate_quadratic_constraint(x, constraint))
    return all_constraints


def evaluate_multi_constraint(x, multi_constraint):
    """ Evaluates the given multi-constraint at the point x. """
    all_multi_constraint_sets = []
    for constraints_set in multi_constraint:
        all_multi_constraint_set = []
        if 'Linear' in constraints_set:
            for constraint in constraints_set['Linear']:
                all_multi_constraint_set.append(np.dot(x - constraint['P'], constraint['n']))
        if 'Quadratic' in constraints_set:
            for constraint in constraints_set['Quadratic']:
                H, c, b = constraint['H'], constraint['c'], constraint['b']
                all_multi_constraint_set.append((x - c).T @ H @ (x - c) - b)
        max_val = max(all_multi_constraint_set)
        all_multi_constraint_sets.append(max_val)
    multi_constraint_val = min(all_multi_constraint_sets)
    return multi_constraint_val


def check_linear_quadratic_constraints(x, linear_constraints, quadratic_constraints):
    """ Checks if the point x is feasible with respect to given linear and quadratic constraints. """
    violations = np.maximum(evaluate_linear_quadratic_constraints(x, linear_constraints, quadratic_constraints), 0)
    return np.all(violations == 0)


def create_linear_constraint(n_var, feasible_pt=None, perpendicular=False):
    """
    Creates a random linear constraint. If feasible_pt is set, ensures that this point is feasible. If perpendicular is
    True, the constraint is perpendicular to the x1-x2 plane.
    """
    p = np.random.uniform(-5, 5, n_var)
    if perpendicular:
        n = np.concatenate([np.random.uniform(-1, 1, 2), np.zeros(n_var - 2)])
    else:
        n = np.random.uniform(-1, 1, n_var)
    if feasible_pt is not None and np.dot(feasible_pt - p, n) > 0:
        n *= -1
    return {'P': p, 'n': n}


def create_quadratic_constraint(n_var, quadratic_constraints_size, quadratic_constraints_condition_number,
                                feasible_pt=None):
    """
    Creates a random quadratic constraint. If feasible_pt is set, ensures that this point is feasible.
    """
    if quadratic_constraints_condition_number is None:
        H = create_random_hessian(n_var)
    else:
        H = create_random_hessian_with_condition_number(n_var, quadratic_constraints_condition_number)

    low, high = quadratic_constraints_size
    b = np.exp(np.random.uniform(np.log(low), np.log(high)))

    if feasible_pt is not None:
        direction = np.random.randn(n_var)
        direction /= np.linalg.norm(direction)
        max_distance = np.sqrt(b / (direction.T @ H @ direction))
        distance = np.random.uniform(0, max_distance)
        c = feasible_pt + distance * direction
    else:
        c = np.random.uniform(-5, 5, n_var)

    return {'H': H, 'c': c, 'b': b}


def set_n_digits(x, n_digits):
    """
    Rounds all numbers in x to n_digits digits.
    """
    if isinstance(x, np.ndarray):
        return np.round(x, n_digits)
    elif isinstance(x, list):
        return [set_n_digits(e, n_digits) for e in x]
    elif isinstance(x, tuple):
        return tuple(set_n_digits(e, n_digits) for e in x)
    elif isinstance(x, dict):
        return {k: set_n_digits(v, n_digits) for k, v in x.items()}
    elif isinstance(x, (int, float)):
        return round(x, n_digits)
    else:
        return x


def create_random_problem(n_var=2, seed=None, domain=(-5, 5),
                          n_peaks=((2, 5), (2, 5)), peaks_value_shift=10, peaks_condition_number=None, alpha=1,
                          n_constraints=None,
                          quadratic_constraints_size=10, quadratic_constraints_condition_number=None,
                          n_multi_constraints_groups=2, n_multi_constraints_group_linear=(0, 1),
                          n_multi_constraints_group_quadratic=(2, 3),
                          constraints_feasible=True, perpendicular_linear_constraints=False,
                          n_digits=None, print_seed=True):
    """
    Generates a random problem for constrained multi-objective minimization:
        min_x (min_i [0.5 (x - c1_i)^T H1_i (x - c1_i) + v1_i], min_j [0.5 (x - c2_j)^T H2_j (x - c2_j) + v2_j])
        subject to <x - p_k, n_k> <= 0 and (x - c3_k)^T H3_k (x - c3_k) <= b_k.
    Where:
    - H1_i, H2_j, H3_k are positive definite matrices of shape (n_var, n_var),
    - c1_i, c2_j, c3_k, p_k, and n_k are vectors of shape (n_var,),
    - v1_i, v2_j, b_k are scalar values.

    Parameters:
    - n_var (int or tuple): Number of variables in the decision space. If a tuple (min, max), the actual number will be
    chosen randomly in the range [min, max].
    - seed (int): Random seed used for reproducibility.
    - n_peaks (tuple of ints or tuples): Number of peaks for objective functions. If provided as a tuple (min, max),
    a random integer will be chosen uniformly from the range [min, max].
    - Peaks_value_shift (number or tuple): Specifies the range from which the peak f-value shifts v1_i and v2_j are
    sampled. If provided as a tuple (min, max), the shifts are sampled uniformly at random from the interval [min, max].
      If provided as a single number x, the shifts are sampled uniformly at random from the interval [-x, x].
    - peaks_condition_number (int or tuple or None): Condition number for Hessian matrices of objective functions.
    If a number x, the actual condition number will be chosen uniformly at random on a logarithmic scale from the interval [1, x].
    If a tuple (min, max), the actual condition number will be chosen uniformly at random on a logarithmic scale from the interval [min, max].
    If None, random Hessian matrices are generated.
    - Alpha (float or tuple): Exponent(s) used to transform the objective functions. The objective function f_i is
    transformed as (f_i - f_i_min) ** alpha_i + f_i_min.
      If provided as a single number x, then alpha_1 = alpha_2 = x.
    - n_constraints (tuple of ints or tuples): Number of linear, quadratic and multi constraints. If a tuple (min, max), the actual number will
    be chosen randomly in the range [min, max].
    - Quadratic_constraints_size (int or tuple): Specifies the range from which the sizes of the quadratic constraints
    are sampled. If a number x, the actual size will be chosen uniformly at random on a logarithmic scale from the interval [0.1, x].
    If provided as a tuple (min, max), the sizes are sampled uniformly at random on a logarithmic scale from the interval [min, max].
    - Quadratic_constraints_condition_number (int or tuple or None): Condition number for Hessian matrices of quadratic
    constraints. If a number x, the actual condition number will be chosen uniformly at random on a logarithmic scale from the interval [1, x].
    If a tuple (min, max), the actual condition number will be chosen uniformly at random on a logarithmic scale from the interval [min, max].
    If None, random Hessian matrices are generated.
    - n_multi_constraints_groups (int or tuple): Number of groups for each multi constraint. If a tuple (min, max), the actual number will be
    chosen randomly in the range [min, max].
    - n_multi_constraints_group_linear (int or tuple): Number of linear constraints in each group of multi constraint. If a tuple (min, max), the actual number will be
    chosen randomly in the range [min, max].
    - n_multi_constraints_group_linear (int or tuple): Number of quadratic constraints in each group of multi constraint. If a tuple (min, max), the actual number will be
    chosen randomly in the range [min, max].
    - constraints_feasible (bool): If True, a point with coordinates randomly sampled uniformly from [-4, 4] is chosen,
    and all added constraints are constructed so that this point is feasible.
      Additionally, each intersection of constraints within a multipeak constraint contains at least one point, which
      may not be feasible for the problem if other constraints are also present.
    - Perpendicular_linear_constraints (bool): If True, generates linear constraints that are perpendicular to the
    x1-x2 plane.
    - n_digits (int or None): If not None, all generated numbers are rounded to n_digits digits.
    - print_seed (bool): Whether to print the seed used for generating the problem.

    Returns a randomly generated MultiPeakProblem instance.
    """
    if n_constraints is None:
        n_constraints = {'Linear': 1, 'Quadratic': 1, 'Multi': 1}
    if not seed:
        seed = np.random.randint(1, 1000)

    np.random.seed(seed)
    if print_seed:
        print(f'Random seed: {seed}')

    n_var = choose_number(n_var, 'n_var', 1)

    n_peaks_f1 = choose_number(n_peaks[0], 'n_peaks_f1', 1)
    n_peaks_f2 = choose_number(n_peaks[1], 'n_peaks_f2', 1)

    peaks_value_shift = get_shift(peaks_value_shift)

    if peaks_condition_number is not None:
        peaks_condition_number = get_size(peaks_condition_number, 1, 'peaks_condition_number')

    centers_f1 = np.random.uniform(domain[0], domain[1], (n_peaks_f1, n_var))
    v_shifts_f1 = np.random.uniform(peaks_value_shift[0], peaks_value_shift[1], n_peaks_f1)
    Hessians_f1 = [create_random_hessian(n_var) if peaks_condition_number is None
                   else create_random_hessian_with_condition_number(n_var, peaks_condition_number) for _ in range(n_peaks_f1)]

    centers_f2 = np.random.uniform(domain[0], domain[1], (n_peaks_f2, n_var))
    v_shifts_f2 = np.random.uniform(peaks_value_shift[0], peaks_value_shift[1], n_peaks_f2)
    Hessians_f2 = [create_random_hessian(n_var) if peaks_condition_number is None
                   else create_random_hessian_with_condition_number(n_var, peaks_condition_number) for _ in range(n_peaks_f2)]

    feasible_pt = np.random.uniform(-4, 4, n_var) if constraints_feasible else None

    n_linear_constraints = n_constraints['Linear']
    n_quadratic_constraints = n_constraints['Quadratic']
    n_multi_constraints = n_constraints['Multi']

    n_linear_constraints = choose_number(n_linear_constraints, 'n_linear_constraints', 0)
    linear_constraints = []
    for _ in range(n_linear_constraints):
        linear_constraint = create_linear_constraint(n_var, feasible_pt=feasible_pt,
                                                     perpendicular=perpendicular_linear_constraints)
        linear_constraints.append(linear_constraint)

    quadratic_constraints_size = get_size(quadratic_constraints_size, 0.1, 'quadratic_constraints_size')
    if quadratic_constraints_condition_number is not None:
        quadratic_constraints_condition_number = get_size(quadratic_constraints_condition_number, 1, 'quadratic_constraints_condition_number')
    n_quadratic_constraints = choose_number(n_quadratic_constraints, 'n_quadratic_constraints', 0)
    quadratic_constraints = []
    for _ in range(n_quadratic_constraints):
        quadratic_constraint = create_quadratic_constraint(n_var, quadratic_constraints_size,
                                                           quadratic_constraints_condition_number,
                                                           feasible_pt=feasible_pt)
        quadratic_constraints.append(quadratic_constraint)

    n_multi_constraints = choose_number(n_multi_constraints, 'n_multi_constraints', 0)
    multi_constraints = []
    for _ in range(n_multi_constraints):
        multi_constraint = []
        n_groups = choose_number(n_multi_constraints_groups, 'n_multi_constraints_groups', 0)
        for i in range(n_groups):
            feasible_pt_group = feasible_pt if i == 0 else (
                np.random.uniform(-4, 4, n_var) if constraints_feasible else None)
            group = {'Linear': [], 'Quadratic': []}
            n_group_linear = choose_number(n_multi_constraints_group_linear, 'n_multi_constraints_group_linear', 0)
            for _ in range(n_group_linear):
                linear_constraint = create_linear_constraint(n_var, feasible_pt=feasible_pt_group,
                                                             perpendicular=perpendicular_linear_constraints)
                group['Linear'].append(linear_constraint)
            n_group_quadratic = choose_number(n_multi_constraints_group_quadratic,
                                              'n_multi_constraints_group_quadratic', 0)
            for _ in range(n_group_quadratic):
                quadratic_constraint = create_quadratic_constraint(n_var, quadratic_constraints_size,
                                                                   quadratic_constraints_condition_number,
                                                                   feasible_pt=feasible_pt_group)
                group['Quadratic'].append(quadratic_constraint)
            multi_constraint.append(group)
        multi_constraints.append(multi_constraint)

    alpha = get_alpha(alpha)
    objectives = ({'H': Hessians_f1, 'c': centers_f1, 'b': v_shifts_f1}, {'H': Hessians_f2, 'c': centers_f2, 'b': v_shifts_f2})
    constraints = {'Linear': linear_constraints, 'Quadratic': quadratic_constraints, 'Multi': multi_constraints}

    if n_digits is not None:
        objectives = set_n_digits(objectives, n_digits)
        constraints = set_n_digits(constraints, n_digits)

    problem = CobiProblem(n_var, objectives, constraints, domain, alpha)
    return problem


def get_rational_function_vector(H1, H2, c1, c2, t):
    """ Returns the curve between the peaks defined by (H1, c1) and (H2, c2) as a vector of rational functions of the
    variable t. """
    H1_sp = sp.Matrix(H1)
    H2_sp = sp.Matrix(H2)
    c1_sp = sp.Matrix(c1)
    c2_sp = sp.Matrix(c2)
    H_combined_inv = (t * H1_sp + (1 - t) * H2_sp).inv()
    return sp.Matrix(H_combined_inv * (t * H1_sp * c1_sp + (1 - t) * H2_sp * c2_sp))


def curve_length(rational_function_vector, t, tol_length):
    """ Returns the length of the curve defined by rational_function_vector(t) for t in [0, 1]. """
    derivatives = [sp.diff(rf, t) for rf in rational_function_vector]
    integrand = sp.sqrt(sum(d ** 2 for d in derivatives))
    f_num = sp.lambdify(t, integrand, 'scipy')
    length, _ = scipy.integrate.quad(f_num, 0, 1, epsabs=tol_length)
    return length


def get_next_t(coeff_funcs, t_val, direction, tol_zero):
    """
    If "direction" is 1, finds the smallest positive value s_val such that
    norm_squared_diff(t_val, s_val) == distance ** 2.
    If "direction" is -1, finds the largest negative value s_val such that
    norm_squared_diff(t_val, s_val) == distance ** 2.
    """
    coeffs = np.array([f(t_val) for f in coeff_funcs], dtype=float)
    roots = np.roots(coeffs)
    roots_numeric = [r.real for r in roots if abs(r.imag) < tol_zero and direction * r.real > 0]
    solution = min(roots_numeric, key=abs) if len(
        roots_numeric) > 0 else direction * 0.5  # Terminate if no valid solutions
    return t_val + solution


def get_unconstrained_pareto_set_equidistant_points(rational_function_vector, t, distance, tol_zero):
    """ Samples points along the curve defined by rational_function_vector(t) for t in [0, 1]. The next point is
    distance away from the last sampled point on the curve. """
    s = sp.Symbol('s', real=True)

    rational_funcs_fun = sp.lambdify(t, rational_function_vector, 'numpy')

    rational_function_vector_move = rational_function_vector.subs(t, t + s)
    diff = rational_function_vector - rational_function_vector_move
    norm_squared_diff = diff.dot(diff)
    norm_squared_diff_minus_distance = norm_squared_diff - distance ** 2
    numer = sp.together(norm_squared_diff_minus_distance).as_numer_denom()[0]
    poly = sp.Poly(numer, s)
    coeff_exprs = poly.all_coeffs()
    coeff_funcs = [sp.lambdify(t, c, 'numpy') for c in coeff_exprs]

    points = []
    ts = []
    current_t = 0
    current_point = rational_function_vector.subs(t, current_t)
    while current_t < 0.5:
        points.append(np.array(current_point, dtype=float).flatten())
        ts.append(current_t)
        current_t = get_next_t(coeff_funcs, current_t, 1, tol_zero)
        current_point = rational_funcs_fun(current_t)
    last_point_first_part = points[-1]

    current_t = 1
    current_point = rational_function_vector.subs(t, current_t)
    while current_t > 0.5:
        points.append(np.array(current_point, dtype=float).flatten())
        ts.append(current_t)
        current_t = get_next_t(coeff_funcs, current_t, -1, tol_zero)
        current_point = rational_funcs_fun(current_t)
    last_point_second_part = points[-1]

    if np.linalg.norm(last_point_first_part - last_point_second_part) >= distance:
        points.append(np.array(current_point, dtype=float).flatten())
        ts.append(current_t)

    return np.array(points, dtype=float), ts


def get_unconstrained_pareto_set_equidistant_local_points(rational_function_vector, t, n_points, tol_length, tol_zero):
    """ Samples approximately n_points points from the unconstrained Pareto set between the peaks defined by (H1, c1)
    and (H2, c2). Sampled points are equidistant. """
    length = curve_length(rational_function_vector, t, tol_length)
    distance = length / (n_points - 1)
    return get_unconstrained_pareto_set_equidistant_points(rational_function_vector, t, distance, tol_zero)


def compute_point(H1, H2, c1, c2, t):
    """ Samples a point from the unconstrained Pareto set between the peaks defined by (H1, c1) and (H2, c2). """
    H_combined_inv = np.linalg.inv(t * H1 + (1 - t) * H2)
    return H_combined_inv @ (t * (H1 @ c1) + (1 - t) * (H2 @ c2))


def get_unconstrained_pareto_set_linspace_weights(H1, H2, c1, c2, n_points):
    """ Samples n_points points from the unconstrained Pareto set between the peaks defined by (H1, c1) and (H2, c2).
    Weights are sampled from linspace. """
    ts = np.linspace(0, 1, n_points)
    points = []
    for t in ts:
        x_t = compute_point(H1, H2, c1, c2, t)
        points.append(x_t)
    return np.array(points, dtype=float), ts


def get_current_point(current_t, compute_point_fun, tol_jump):
    """ Computes the point using compute_point_fun. If unsuccessful, increment current_t by tol_jump and retry until a
    valid point is computed. If no valid point is found, returns None as the point. """
    current_point = compute_point_fun(current_t)
    while current_point is None:
        current_t += tol_jump
        if 0 <= current_t <= 1:
            current_point = compute_point_fun(current_t)
        else:
            break
    return current_point, current_t


def get_next_t_bisection(current_point, current_t, direction, tol_distance, tol_jump, max_iter, distance,
                         compute_point_fun, distance_fun, force_equidistant):
    """
    Finds the next t such that the point at t is approximately distance away from the current_point, using bisection.
    If "direction" is 1, finds t > current_t.
    If "direction" is -1, finds t < current_t.
    """
    if direction == 1:
        t_low = current_t
        t_high = 1.0
    elif direction == -1:
        t_low = 0.0
        t_high = current_t
    else:
        raise ValueError("Direction must be 1 (forward) or -1 (backward).")

    t_next = None

    for _ in range(max_iter):
        t_mid = (t_low + t_high) / 2.0
        x_mid, t_mid = get_current_point(t_mid, compute_point_fun, direction * tol_jump)
        if x_mid is None:
            break
        dist = distance_fun(x_mid, current_point)

        if (force_equidistant and abs(dist - distance) < tol_distance) or ((not force_equidistant) and dist < distance):
            t_next = t_mid
            break

        if dist < distance:
            if direction == 1:
                t_low = t_mid
            else:
                t_high = t_mid
        else:
            if direction == 1:
                t_high = t_mid
            else:
                t_low = t_mid

    if t_next is None:
        t_next = (t_low + t_high) / 2.0

    return t_next


def get_pareto_set_bisection_weights(distance, compute_point_fun, distance_fun, tol_distance=1e-5, tol_jump=1e-3,
                                     max_iter=100, force_equidistant=False):
    """ Samples points such that the next point is approximately distance away from the last sampled point. Points are
    computed with compute_point_fun. The distance between points is computed using distance_fun. """
    points = []
    ts = []
    current_t = 0
    current_point, current_t = get_current_point(current_t, compute_point_fun, tol_jump)
    if current_point is None:
        return np.array([]), np.array([])
    while current_t < 0.5:
        points.append(current_point)
        ts.append(current_t)
        current_t = get_next_t_bisection(current_point, current_t, 1, tol_distance, tol_jump, max_iter, distance,
                                         compute_point_fun, distance_fun, force_equidistant)
        current_point, current_t = get_current_point(current_t, compute_point_fun, tol_jump)
    last_point_first_part = points[-1] if len(points) > 0 else None

    current_t = 1
    current_point, current_t = get_current_point(current_t, compute_point_fun, -tol_jump)
    if current_point is None:
        return np.array([]), np.array([])
    while current_t > 0.5:
        points.append(current_point)
        ts.append(current_t)
        current_t = get_next_t_bisection(current_point, current_t, -1, tol_distance, tol_jump, max_iter, distance,
                                         compute_point_fun, distance_fun, force_equidistant)
        current_point, current_t = get_current_point(current_t, compute_point_fun, -tol_jump)
    last_point_second_part = points[-1] if len(points) > 0 else None

    if last_point_first_part is not None and last_point_second_part is not None and distance_fun(
            last_point_first_part, last_point_second_part) >= distance:
        points.append(current_point)
        ts.append(current_t)

    return np.array(points, dtype=float), np.array(ts)


def project_point(H1, H2, c1, c2, w, C, d, feasibility_tolerance=1e-8, lambda_tolerance=1e-8):
    """
    Solves the quadratic program:
        min_x w*(x - c1)^T H1 (x - c1) + (1 - w)*(x - c2)^T H2 (x - c2)
        subject to Cx <= d
    using the KKT conditions without iterations.

    Parameters:
    - H1, H2: (n x n) positive-definite matrices
    - c1, c2: (n,) vectors
    - w: scalar in [0, 1]
    - C: (m x n) constraint matrix
    - d: (m,) constraint vector

    Returns:
    - x_opt: Optimal solution vector
    - lambda_opt: Lagrange multipliers for active constraints
    """
    n = H1.shape[0]
    m = C.shape[0]

    # Compute H and h as defined
    H = 2 * w * H1 + 2 * (1 - w) * H2
    h = 2 * w * H1 @ c1 + 2 * (1 - w) * H2 @ c2

    # Objective function for comparison
    def objective(x):
        return w * (x - c1).T @ H1 @ (x - c1) + (1 - w) * (x - c2).T @ H2 @ (x - c2)

    # Initialize the best solution
    best_x = None
    best_obj = np.inf

    # Iterate over all possible active sets (combinations of constraints)
    for k in range(m + 1):
        for active_indices in itertools.combinations(range(m), k):
            # The number of active constraints should not exceed n
            if len(active_indices) > n or len(active_indices) == 0:
                continue

            C_A = C[list(active_indices), :]  # Active constraint matrix
            d_A = d[list(active_indices)]
            try:
                # Form KKT matrix
                KKT_matrix = np.block([
                    [H, C_A.T],
                    [C_A, np.zeros((len(active_indices), len(active_indices)))]
                ])
                # Form the right-hand side
                KKT_rhs = np.hstack([h, d_A])

                # Solve the KKT system
                solution = np.linalg.solve(KKT_matrix, KKT_rhs)
                x_star = solution[:n]
                lambda_star = solution[n:]

                # Check primal feasibility: Cx <= d
                if np.all(C @ x_star - d <= feasibility_tolerance):  # Allow small numerical tolerance
                    # Check dual feasibility: lambda >= 0 for active constraints
                    if np.all(lambda_star >= -lambda_tolerance):  # Allow small numerical tolerance
                        # Compute objective
                        obj_val = objective(x_star)
                        if obj_val < best_obj:
                            best_obj = obj_val
                            best_x = x_star
                            # Initialize full lambda vector
                            lambda_full = np.zeros(m)
                            lambda_full[list(active_indices)] = lambda_star

            except np.linalg.LinAlgError:
                # Singular matrix, skip this active set
                continue

    return best_x


def transform(x, alpha, f_min):
    """
    Returns (x - f_min)^alpha + f_min.
    """
    return (x - f_min) ** alpha + f_min


def check_binding(constraint, evaluate_constraint, pareto_set, tol):
    """
    Check if a constraint is binding based on the Pareto set of the problem with this constraint removed.
    The constraint is evaluated at point x using evaluate_constraint(x, constraint), and the binding condition is
    checked with the tolerance tol.
    """
    for pt in pareto_set:
        if evaluate_constraint(pt, constraint) > tol:
            return True
    return False


def count_curves_agglomerative(points, distance_threshold=0.05):
    """ Counts the number of connected curves using agglomerative clustering. """
    clustering = AgglomerativeClustering(n_clusters=None, linkage='single', distance_threshold=distance_threshold)
    labels = clustering.fit_predict(points)
    num_clusters = len(set(labels))
    return num_clusters


def load_problem(filename):
    """ Loads the saved MultiPeakProblem with computed results from the specified file. """
    with open(filename, 'rb') as f:
        problem = pickle.load(f)
    return problem


def get_linear_constraints(constraints):
    Ps, ns = [], []
    for constraints in constraints:
        Ps.append(constraints['P'])
        ns.append(constraints['n'])
    return Ps, ns


def get_quadratic_constraints(constraints):
    cs, Hs, bs = [], [], []
    for constraints in constraints:
        cs.append(constraints['c'])
        Hs.append(constraints['H'])
        bs.append(constraints['b'])
    return cs, Hs, bs


class CobiProblem(ElementwiseProblem):
    def __init__(self, n_var, objectives, constraints, domain=(-5, 5), alpha=(1, 1)):
        self.objectives = objectives
        self.constraints = constraints

        for multi_constraint in constraints['Multi']:
            for constraints_set in multi_constraint:
                if 'Linear' not in constraints_set:
                    constraints_set['Linear'] = []
                if 'Quadratic' not in constraints_set:
                    constraints_set['Quadratic'] = []
        n_constr = len(constraints['Linear']) + len(constraints['Quadratic']) + len(constraints['Multi'])
        super().__init__(n_var=n_var, n_obj=2, n_constr=n_constr, xl=domain[0], xu=domain[1])

        self.transformation_alpha = (alpha, alpha) if (type(alpha) is float) or (type(alpha) is int) else alpha
        self.f_min = np.array([np.min(self.objectives[0]['b']), np.min(self.objectives[1]['b'])])
        self.pareto_set = None
        self.pareto_front = None
        self.uncon_pareto_set = None
        self.uncon_pareto_front = None
        self.num_solver_failed = None  # The number of points not projected to a feasible solution by the solver.
        self.active_constraints = None
        self.local_unconstrained_pareto_sets = None
        self.local_unconstrained_pareto_fronts = None
        self.local_pareto_sets = None
        self.local_pareto_fronts = None
        self.sampling_options = None
        self._hypervolume = None
        self._normalized_hypervolume = None

    def __call__(self, x):
        """Evaluate x."""
        return self.evaluate_objectives(x)

    def evaluate_objectives(self, x):
        f1 = np.min([v + peak_function(x, c, H) for c, v, H in zip(self.objectives[0]['c'],
                                                                   self.objectives[0]['b'],
                                                                   self.objectives[0]['H'])], axis=0)
        f2 = np.min([v + peak_function(x, c, H) for c, v, H in zip(self.objectives[1]['c'],
                                                                   self.objectives[1]['b'],
                                                                   self.objectives[1]['H'])], axis=0)
        return np.array([f1, f2])

    def evaluate_constraints(self, x):
        all_constraints = evaluate_linear_quadratic_constraints(x, self.constraints['Linear'], self.constraints['Quadratic'])
        for multi_constraint in self.constraints['Multi']:
            all_constraints.append(evaluate_multi_constraint(x, multi_constraint))
        return all_constraints

    def _evaluate(self, x, out, *args, **kwargs):
        out["F"] = np.column_stack(transform(self.evaluate_objectives(x), self.transformation_alpha, self.f_min))
        out["G"] = np.column_stack(self.evaluate_constraints(x)) if self.n_constr > 0 else np.array([])

    def choose_solver(self):
        """ Choose an appropriate solver. """
        if self.constraints['Quadratic'] == 0:
            for multi_constraint in self.constraints['Multi']:
                for constraints_set in multi_constraint:
                    if len(constraints_set['Quadratic']) > 0:
                        return 'cvxpy_SCS'
            return 'daqp'
        return 'cvxpy_SCS'

    def peak_pair_function(self, i, j, x):
        """ Evaluates a pair of single peak functions at the point x. """
        return np.array([self.objectives[0]['b'][i] + peak_function(x, self.objectives[0]['c'][i], self.objectives[0]['H'][i]),
                         self.objectives[1]['b'][j] + peak_function(x, self.objectives[1]['c'][j], self.objectives[1]['H'][j])])

    def check_all_feasible(self, x):
        """ Checks if the point x is feasible. """
        violations = np.maximum(self.evaluate_constraints(x), 0)
        return np.all(violations == 0)

    def violation_point(self, x):
        """ Computes the total constraint violation at point x. """
        return np.sum(np.maximum(self.evaluate_constraints(x), 0))

    def split_active_constraints(self, active_constraints):
        """ Splits active_constraints into sets of linear, quadratic, and multi active constraints. """
        linear_num = len(self.constraints['Linear'])
        quadratic_num = len(self.constraints['Quadratic'])

        linear_set = set()
        quadratic_set = set()
        multi_set = set()

        for idx in active_constraints:
            if idx < linear_num:
                linear_set.add(idx + 1)  # Add 1 to make the indices in the output start at 1
            elif idx < linear_num + quadratic_num:
                quadratic_set.add(idx - linear_num + 1)
            else:
                multi_set.add(idx - linear_num - quadratic_num + 1)
        return linear_set, quadratic_set, multi_set

    def get_active_constraints(self, x, tol_active):
        """ Computes the set of active constraints for point x. The constraint g is considered active at the point x if
        abs(g(x)) is less than tol_active. """
        active_constraints = {int(i) for i in np.where(np.abs(self.evaluate_constraints(x)) < tol_active)[0]}
        return self.split_active_constraints(active_constraints)

    def join_multi_constraints(self):
        """ Joins self.constraints['Multi']s into one equivalent multi-constraint. """
        joint_multi_constraint = []
        for combination in itertools.product(*self.constraints['Multi']):
            joint_linear = []
            joint_quadratic = []
            for constraints_set in combination:
                if 'Linear' in constraints_set:
                    joint_linear.extend(constraints_set['Linear'])
                if 'Quadratic' in constraints_set:
                    joint_quadratic.extend(constraints_set['Quadratic'])

            joint_multi_constraint.append({
                'Linear': joint_linear,
                'Quadratic': joint_quadratic
            })
        return joint_multi_constraint

    def project_point_solver(self, H1, H2, c1, c2, linear_constraints, quadratic_constraints, w, tol_feasible, solver):
        """
        Solves the quadratic program:
            min_x w * (x - c1)^T H1 (x - c1) + (1 - w) * (x - c2)^T H2 (x - c2)
            subject to Cx <= d and (x - c_i)^T H_i (x - c_i) <= b_i for i=1,...,k
        using the solver.

        The kkt solver uses the KKT conditions without iterations.
        Only cvxpy solvers can handle quadratic constraints.

        Parameters:
        - H1, H2: (n x n) positive-definite matrices
        - c1, c2: (n,) vectors
        - linear_constraints: a list of linear constraints
        - quadratic_constraints: a list of quadratic constraints
        - w: scalar in [0, 1]
        - tol_feasible: the solution is considered feasible if its total violation does not exceed this tolerance
        - solver: a solver that will be used for projection of the unconstrained Pareto set onto the feasible

        Returns:
            None: if no feasible optimal solution is found.
            Otherwise, returns:
                - x_opt: the solution vector returned by the solver
        """
        Ps, ns = get_linear_constraints(linear_constraints)
        cs, Hs, bs = get_quadratic_constraints(quadratic_constraints)

        C = np.array(ns)
        if len(ns) > 0:
            d = np.sum(np.array(ns) * np.array(Ps), axis=1)
        else:
            d = np.array([])

        if solver == 'cvxpy_SCS':
            x = cp.Variable(H1.shape[0])
            objective = cp.Minimize(w * cp.quad_form(x - c1, H1) + (1 - w) * cp.quad_form(x - c2, H2))

            if len(C) > 0:
                constraints = [C @ x <= d]
            else:
                constraints = []
            constraints += [cp.quad_form(x - cs[i], Hs[i]) <= bs[i] for i in range(len(Hs))]
            problem = cp.Problem(objective, constraints)

            problem.solve(solver=cp.SCS, eps_abs=1e-12, eps_rel=1e-12, eps_infeas=1e-12, max_iters=1000000)
            x_opt = x.value

        elif 0 < len(Hs):
            raise ValueError(
                f'The problem contains quadratic constraints, which are not supported by the solver {solver}. '
                f'The cvxpy_SCS solver can handle quadratic constraints.')

        elif solver == 'kkt':
            x_opt = project_point(H1, H2, c1, c2, w, C, d)

        else:
            P = 2 * (w * H1 + (1 - w) * H2)
            q = -2 * (w * H1 @ c1 + (1 - w) * H2 @ c2)

            x_opt = solve_qp(P, q, C, d, solver=solver)

        if x_opt is None:
            return x_opt
        else:
            # Check primal feasibility
            violation = self.violation_point(x_opt)
            if violation > tol_feasible:
                return None
            return x_opt

    def compute_and_project_point(self, H1, H2, c1, c2, linear_constraints, quadratic_constraints, t, tol_feasible, solver):
        """ Computes the point and projects it if needed. """
        pt = compute_point(H1, H2, c1, c2, t)
        feas = check_linear_quadratic_constraints(pt, linear_constraints, quadratic_constraints)
        projected_pt = pt if feas else self.project_point_solver(H1, H2, c1, c2, linear_constraints,
                                                                 quadratic_constraints, t, tol_feasible, solver)
        if projected_pt is None:
            self.num_solver_failed += 1
        return projected_pt

    def get_active_constraints_ps(self, ps, tol_active):
        """ Computes the active constraints for each point in ps, using the tolerance tol_active. """
        return [self.get_active_constraints(pt, tol_active) for pt in ps]

    def project_unconstrained_pareto_set(
            self, H1, H2, c1, c2,
            linear_constraints, quadratic_constraints,
            uncon_pareto_set, uncon_pareto_set_w, tol_feasible, solver):
        """
        Projects points from the local unconstrained Pareto set between peaks specified by (c1, H1) and (c2, H2) onto
        the feasible region defined by: Cx <= d and (x - c_i)^T H_i (x - c_i) <= b_i for i=1,...,k.

        Parameters:
        - H1, H2: (n x n) positive-definite matrices
        - c1, c2: (n,) vectors
        - linear_constraints
        - quadratic_constraints
        - uncon_pareto_set: the unconstrained Pareto set
        - uncon_pareto_set_w: the values w such that w * (x - c1)^T H1 (x - c1) + (1 - w) * (x - c2)^T H2 (x - c2) is
        the corresponding point in the Pareto set
        - tol_feasible: the projected point is considered feasible if its total violation does not exceed this tolerance

        Returns:
        - ps: projected points
        - num_solver_failed: the number of points not projected to a feasible solution by the solver
        """
        ps = []
        num_solver_failed = 0
        for pt, w in zip(uncon_pareto_set, uncon_pareto_set_w):
            feas = check_linear_quadratic_constraints(pt, linear_constraints, quadratic_constraints)

            if feas:
                ps.append(pt)

            else:
                projected_pt = self.project_point_solver(
                    H1, H2, c1, c2,
                    linear_constraints, quadratic_constraints,
                    w, tol_feasible, solver)
                if projected_pt is not None:
                    ps.append(projected_pt)
                else:
                    num_solver_failed += 1

        return ps, num_solver_failed

    def calculate_pareto_set_and_front(self, sampling_options=None,
                                       tol_feasible=1e-8, compute_active=False, tol_active=1e-8,
                                       skip_dominated=True, solver=None, print_error=False):
        """
        Sets the self.local_unconstrained_pareto_fronts, self.local_unconstrained_pareto_sets, self.uncon_pareto_front,
        self.uncon_pareto_set, self.local_pareto_fronts, self.local_pareto_sets, self.pareto_fronts, self.pareto_set,
        and self.active_constraints attributes.

        For every peak from f1 and every peak from f2, the unconstrained Pareto set between these individual peaks is
        formed, and n_points are sampled from it.
        The set of sampled points is added to self.local_sets.
        The sampled points are added to self.uncon_pareto_set. Only nondominated points are kept.
        The sampled points are then projected onto the feasible region and added to self.pareto_set. Only nondominated
        points are kept.
        The variable self.num_solver_failed stores the number of points the solver failed to project to a feasible
        solution.
        The variable self.sampling_options stores the used sampling_options.

        Parameters:
        - sampling_options:
            A dictionary with the chosen sampling:
                - weights: sample n_points points along each curve with equidistant weights
                - curve-points: sample n_points equidistant points along each curve
                - curve-dist: the Euclidean distance between consecutive sampled points is equal to the chosen distance
                (uses bisection)
                - curve-dist-rf: the Euclidean distance between consecutive sampled points is equal to the chosen distance
                (same as curve-dist but uses rational functions)
                - projection: the Euclidean distance between consecutive projected points is equal to the chosen distance
                (uses bisection)
                - front: the Euclidean distance between consecutive points on the Pareto front is equal to the chosen
                distance (uses bisection)
                - error: sample points until error is smaller than max_error
                - edge: sample only edge points (useful for computing nadir and ideal points)
            and parameters:
                - n_points: The number of points to sample from each Pareto set between two individual peaks (used when
                sampling is curve-points or weights)
                - distance: The Euclidean distance between two consecutive sampled points (used when sampling is curve-dist,
                curve-dist-rf, projection, front)
                - max_error: maximal hypervolume error
                - tol_feasible: the projected point is considered feasible if its total violation does not exceed this tolerance
                - tol_length: the tolerance used when computing the length of the curve describing the Pareto set between two
                individual peaks (used when sampling is curve-points)
                - tol_zero: imaginary values with magnitudes smaller than this tolerance are considered 0 (used when sampling is
                curve-points or curve-dist-rf)
                - tol_distance: the tolerance used when computing the next point that should be distance away from the current
                point (used when sampling is curve-dist, projection, front)
                - tol_jump: the amount to move the parameter by when point computation fails, retried until a point is computed
                (used when sampling is curve-dist, projection, front)
                - max_iter: the maximum number of iterations for the bisection (used when sampling is curve-dist, projection,
                front)
                - force_equidistant: if true, the next point must be exactly the chosen distance from the previous point,
                otherwise, it is sufficient for the distance to be less than the chosen distance (used when sampling is
                curve-dist, projection, front)
                - always_compute_unconstrained: if true, compute unconstrained Pareto set and front, even when not required
                (used when sampling is projection or front)
                - print_error: if true, prints estimated maximal error during computation (used when sampling is error)
        - compute_active: if true, computes which constraints are active at each point
        - tol_active: the constraint g is considered active at point x if abs(g(x)) is less than this tolerance (used
        when compute-active is true)
        - skip_dominated: if true, skips points that are already dominated by some projected point
        - solver (str or None): A solver that will be used for projection of the unconstrained Pareto set onto the feasible
        region. The kkt solver uses the KKT conditions without iterations. If None, an appropriate solver is automatically selected

        Returns nothing.
        """
        if sampling_options is None:
            sampling_options = {'sampling': 'weights', 'n_points': 100}
        default_values = {
            'sampling': 'weights',
            'n_points': 100,
            'distance': 0.1,
            'max_error': 0.001,
            'tol_length': 1e-10,
            'tol_zero': 1e-10,
            'tol_distance': 1e-8,
            'tol_jump': 1e-3,
            'max_iter': 100,
            'force_equidistant': False,
            'always_compute_unconstrained': False,
            'print_error': False
        }
        required_keys = {
            'weights':            ['n_points'],
            'curve-points':       ['n_points', 'tol_length', 'tol_zero'],
            'curve-dist':         ['distance', 'tol_distance', 'tol_jump', 'max_iter', 'force_equidistant'],
            'curve-dist-rf':      ['distance', 'tol_distance', 'tol_jump', 'max_iter', 'tol_zero', 'force_equidistant'],
            'projection':         ['distance', 'tol_distance', 'tol_jump', 'max_iter', 'force_equidistant', 'always_compute_unconstrained'],
            'front':              ['distance', 'tol_distance', 'tol_jump', 'max_iter', 'force_equidistant', 'always_compute_unconstrained'],
            'error':              ['max_error', 'print_error'],
            'edge':               []
        }
        sampling = sampling_options.get('sampling', default_values['sampling'])
        needed = required_keys.get(sampling, [])

        params = {}
        for key in needed:
            params[key] = sampling_options.get(key, default_values[key])
        
        n_points = params.get('n_points', None)
        distance = params.get('distance', None)
        max_error = params.get('max_error', None)
        tol_length = params.get('tol_length', None)
        tol_zero = params.get('tol_zero', None)
        tol_distance = params.get('tol_distance', None)
        tol_jump = params.get('tol_jump', None)
        max_iter = params.get('max_iter', None)
        force_equidistant = params.get('force_equidistant', None)
        always_compute_unconstrained = params.get('always_compute_unconstrained', None)
        print_error = params.get('print_error', None)

        self.local_unconstrained_pareto_sets = {}
        self.local_unconstrained_pareto_fronts = {}
        uncon_pareto_set_and_front = get_mo_archive()
        self.local_pareto_sets = {}
        self.local_pareto_fronts = {}
        pareto_set_and_front = get_mo_archive()
        self.num_solver_failed = 0
        self.sampling_options = sampling_options
        
        if solver == None:
            solver = self.choose_solver()

        joint_multi_constraint = self.join_multi_constraints()

        n_var = self.n_var
        boundary_linear_constraints = []
        for i in range(n_var):
            P_upper = np.zeros(n_var)
            n_upper = np.zeros(n_var)
            n_upper[i] = 1
            P_upper[i] = self.xu[i]
            boundary_linear_constraints.append({'P': P_upper, 'n': n_upper})
            
            P_lower = np.zeros(n_var)
            n_lower = np.zeros(n_var)
            n_lower[i] = -1
            P_lower[i] = self.xl[i]
            boundary_linear_constraints.append({'P': P_lower, 'n': n_lower})

        t = None
        if sampling == 'curve-dist-rf' or sampling == 'curve-points':
            t = sp.Symbol('t', real=True)
        elif sampling == 'error':
            queue = PriorityQueue()
            counter = 0
            total_error = 0

        for i, (center_f1, Hessian_f1) in enumerate(zip(self.objectives[0]['c'], self.objectives[0]['H'])):
            for j, (center_f2, Hessian_f2) in enumerate(zip(self.objectives[1]['c'], self.objectives[1]['H'])):
                if skip_dominated:
                    ideal_point = np.array([self.objectives[0]['b'][i], self.objectives[1]['b'][j]])
                    if pareto_set_and_front.dominates(ideal_point):
                        continue

                if sampling == 'curve-dist-rf':
                    rational_function_vector = get_rational_function_vector(Hessian_f1, Hessian_f2, center_f1,
                                                                            center_f2, t)
                    unconstrained_pareto_points, unconstrained_pareto_points_w = get_unconstrained_pareto_set_equidistant_points(
                        rational_function_vector, t, distance, tol_zero)
                elif sampling == 'curve-points':
                    rational_function_vector = get_rational_function_vector(Hessian_f1, Hessian_f2, center_f1,
                                                                            center_f2, t)
                    unconstrained_pareto_points, unconstrained_pareto_points_w = get_unconstrained_pareto_set_equidistant_local_points(
                        rational_function_vector, t, n_points, tol_length, tol_zero)
                elif sampling == 'weights':
                    unconstrained_pareto_points, unconstrained_pareto_points_w = get_unconstrained_pareto_set_linspace_weights(
                        Hessian_f1, Hessian_f2, center_f1, center_f2, n_points)
                elif sampling == 'curve-dist' or (sampling in ['projection', 'front'] and always_compute_unconstrained):
                    compute_point_fun = lambda l: compute_point(Hessian_f1, Hessian_f2, center_f1, center_f2, l)
                    distance_fun = lambda x, y: np.linalg.norm(x - y)
                    unconstrained_pareto_points, unconstrained_pareto_points_w = get_pareto_set_bisection_weights(
                        distance, compute_point_fun, distance_fun, tol_distance, tol_jump, max_iter, force_equidistant)
                elif sampling in ['projection', 'front']:
                    unconstrained_pareto_points, unconstrained_pareto_points_w = [], []
                elif sampling in ['error', 'edge']:
                    unconstrained_pareto_points, unconstrained_pareto_points_w = np.array([center_f1, center_f2]), np.array([1, 0])
                else:
                    raise ValueError('Undefined sampling.')
                self.local_unconstrained_pareto_sets.update({f'{i}-{j}': np.array(unconstrained_pareto_points)})
                unconstrained_pareto_front = np.array(
                    [self.evaluate_objectives(x) for x in unconstrained_pareto_points])
                self.local_unconstrained_pareto_fronts.update({f'{i}-{j}': np.array(unconstrained_pareto_front)})
                for x, f in zip(unconstrained_pareto_points, unconstrained_pareto_front):
                    uncon_pareto_set_and_front.add(f, info={'x': x})

                if skip_dominated:
                    filtered_unconstrained_pareto_points = []
                    filtered_unconstrained_pareto_points_w = []
                    for x, w, f in zip(unconstrained_pareto_points, unconstrained_pareto_points_w,
                                       unconstrained_pareto_front):
                        if not pareto_set_and_front.dominates(f):
                            filtered_unconstrained_pareto_points.append(x)
                            filtered_unconstrained_pareto_points_w.append(w)
                else:
                    filtered_unconstrained_pareto_points = unconstrained_pareto_points
                    filtered_unconstrained_pareto_points_w = unconstrained_pareto_points_w

                for k, constraints in enumerate(joint_multi_constraint):
                    if sampling in ['projection', 'front']:
                        if sampling == 'projection':
                            distance_fun = lambda x, y: np.linalg.norm(x - y)
                        else:
                            distance_fun = lambda x, y: np.linalg.norm(
                                self.evaluate_objectives(x) - self.evaluate_objectives(y))
                        compute_and_project_point = lambda l: self.compute_and_project_point(
                            Hessian_f1, Hessian_f2, center_f1, center_f2,
                            self.constraints['Linear'] + constraints['Linear'] + boundary_linear_constraints,
                            self.constraints['Quadratic'] + constraints['Quadratic'],
                            l, tol_feasible, solver)
                        pareto_points, _ = get_pareto_set_bisection_weights(
                            distance, compute_and_project_point, distance_fun, tol_distance, tol_jump, max_iter,
                            force_equidistant)
                    else:
                        pareto_points, num_failed = self.project_unconstrained_pareto_set(
                            Hessian_f1, Hessian_f2, center_f1, center_f2,
                            self.constraints['Linear'] + constraints['Linear'] + boundary_linear_constraints,
                            self.constraints['Quadratic'] + constraints['Quadratic'],
                            filtered_unconstrained_pareto_points, filtered_unconstrained_pareto_points_w,
                            tol_feasible, solver)
                        self.num_solver_failed += num_failed
                        if sampling == 'error':
                            if len(pareto_points) > 1:
                                y_left = self.peak_pair_function(i, j, pareto_points[0])
                                y_right = self.peak_pair_function(i, j, pareto_points[1])
                                error = abs(y_right[0] - y_left[0]) * abs(y_left[1] - y_right[1])
                                queue.put((-error, counter, (i, j, k, 1, 0, y_left, y_right)))
                                counter += 1
                                total_error += error
                                pareto_set_and_front.add(self.evaluate_objectives(pareto_points[0]), info={'x': pareto_points[0]})
                                pareto_set_and_front.add(self.evaluate_objectives(pareto_points[1]), info={'x': pareto_points[1]})
                            elif len(pareto_points) == 1:
                                y = self.peak_pair_function(i, j, pareto_points[0])
                                pareto_set_and_front.add(y, info={'x': pareto_points[0]})
                    if sampling != 'error':
                        self.local_pareto_sets.update({f'{k}:{i}-{j}': np.array(pareto_points)})
                        pareto_front = np.array([self.evaluate_objectives(x) for x in pareto_points])
                        self.local_pareto_fronts.update({f'{k}:{i}-{j}': np.array(pareto_front)})
                        if compute_active:
                            active_constraints = self.get_active_constraints_ps(pareto_points, tol_active)
                            for x, ac, f in zip(pareto_points, active_constraints, pareto_front):
                                pareto_set_and_front.add(f, info={'x': x, 'active_constraints': ac})
                        else:
                            for x, f in zip(pareto_points, pareto_front):
                                pareto_set_and_front.add(f, info={'x': x})

        if sampling == 'error':
            while total_error > max_error:
                if print_error:
                    print('estimated_maximal_error:', total_error)
                neg_error, _, (i, j, k, weight_left, weight_right, y_left, y_right) = queue.get()
                Hessian_f1, Hessian_f2, center_f1, center_f2 = self.objectives[0]['H'][i], self.objectives[1]['H'][j], self.objectives[0]['c'][i], self.objectives[1]['c'][j]
                weight_middle = (weight_left + weight_right) / 2
                uncon_point_middle = compute_point(Hessian_f1, Hessian_f2, center_f1, center_f2, weight_middle)
                feas = check_linear_quadratic_constraints(uncon_point_middle, self.constraints['Linear'] + joint_multi_constraint[k]['Linear'] + boundary_linear_constraints,
                                                          self.constraints['Quadratic'] + joint_multi_constraint[k]['Quadratic'])
                if feas:
                    point_middle = uncon_point_middle
                else:
                    pareto_points, num_failed = self.project_unconstrained_pareto_set(
                        Hessian_f1, Hessian_f2, center_f1, center_f2,
                        self.constraints['Linear'] + joint_multi_constraint[k]['Linear'] + boundary_linear_constraints,
                        self.constraints['Quadratic'] + joint_multi_constraint[k]['Quadratic'],
                        [uncon_point_middle], [weight_middle],
                        tol_feasible, solver)
                    self.num_solver_failed += num_failed
                    point_middle = pareto_points[0]
                y_middle = self.peak_pair_function(i, j, point_middle)
                pareto_set_and_front.add(y_middle, info={'x': point_middle})
                error = -neg_error
                total_error -= error

                ideal_point1 = np.min(np.array([y_left, y_middle]), axis=0)
                if not pareto_set_and_front.dominates(ideal_point1):
                    error1 = abs(y_middle[0] - y_left[0]) * abs(y_left[1] - y_middle[1])
                    total_error += error1
                    queue.put((-error1, counter, (i, j, k, weight_left, weight_middle, y_left, y_middle)))
                    counter += 1
                else:
                    error1 = 0

                ideal_point2 = np.min(np.array([y_middle, y_right]), axis=0)
                if not pareto_set_and_front.dominates(ideal_point2):
                    error2 = abs(y_right[0] - y_middle[0]) * abs(y_middle[1] - y_right[1])
                    total_error += error2
                    queue.put((-error2, counter, (i, j, k, weight_middle, weight_right, y_middle, y_right)))
                    counter += 1
                else:
                    error2 = 0

        self.uncon_pareto_front = np.array(uncon_pareto_set_and_front)
        self.uncon_pareto_set = np.array([list(d['x']) for d in uncon_pareto_set_and_front.infos]) \
            if len(uncon_pareto_set_and_front) > 0 else np.empty((0, 2))

        self.pareto_front = np.array(pareto_set_and_front)
        self.pareto_set = np.array([list(d['x']) for d in pareto_set_and_front.infos])

        if compute_active:
            self.active_constraints = list([d['active_constraints'] for d in pareto_set_and_front.infos])
        else:
            self.active_constraints = None

        self.uncon_pareto_front = np.array(
            [transform(x, self.transformation_alpha, self.f_min) for x in self.uncon_pareto_front]) \
            if len(self.uncon_pareto_front) > 0 else np.empty((0, 2))
        self.pareto_front = np.array([transform(x, self.transformation_alpha, self.f_min) for x in self.pareto_front])

    def nadir_point(self, *args, **kwargs):
        if self.pareto_front is None:
            self.calculate_pareto_set_and_front(sampling_options={'sampling': 'edge'})
        return np.max(self.pareto_front, axis=0)

    def ideal_point(self, *args, **kwargs):
        if self.pareto_front is None:
            self.calculate_pareto_set_and_front(sampling_options={'sampling': 'edge'})
        return np.min(self.pareto_front, axis=0)

    @property
    def name(self):
        return (f"COBI problem with ({len(self.objectives[0]['c'])}, {len(self.objectives[1]['c'])}) peaks and "
                f"{len(self.constraints['Linear']) + len(self.constraints['Quadratic']) + len(self.constraints['Multi'])} "
                f'constraints')

    def _compute_hypervolume(self):
        """
        Computes the non-normalized and normalized hypervolumes. If the Pareto set has not been computed yet, it is
        computed first.
        """
        if self.pareto_set is None:
            self.calculate_pareto_set_and_front()
        ideal = self.ideal_point()
        nadir = self.nadir_point()
        # Compute the regular hypervolume first
        hv_archive = get_mo_archive(reference_point=nadir)
        hv_archive.add_list(self.pareto_front)
        self._hypervolume = float(hv_archive.hypervolume)
        # Then compute the normalized hypervolume
        self._normalized_hypervolume = self._hypervolume / np.prod(nadir - ideal)

    @property
    def hypervolume(self):
        """ Returns the approximated hypervolume of the Pareto front. """
        if self._hypervolume is None:
            self._compute_hypervolume()
        return self._hypervolume

    @property
    def normalized_hypervolume(self):
        """ Returns the approximated normalized hypervolume of the Pareto front. """
        if self._normalized_hypervolume is None:
            self._compute_hypervolume()
        return self._normalized_hypervolume

    def reduce_Pareto_set_size(self, size):
        """
        Iteratively removes the point with the least contribution to the overall hypervolume until the desired number
        of points is reached.
        """
        if self.pareto_set is None:
            raise ValueError("Could not evaluate reduce_Pareto_set_size. Compute Pareto set first.")
        else:
            nadir = self.nadir_point()
            pareto_set_and_front = get_mo_archive(reference_point=nadir)
            for x, f in zip(self.pareto_set, self.pareto_front):
                pareto_set_and_front.add(f, info={'x': x})
            while len(pareto_set_and_front) > size:
                hv_contributions = pareto_set_and_front.contributing_hypervolumes
                min_contributing_point = pareto_set_and_front[np.argmin(hv_contributions)]
                pareto_set_and_front.remove(min_contributing_point)
            self.pareto_front = np.array(pareto_set_and_front)
            self.pareto_set = np.array([list(d['x']) for d in pareto_set_and_front.infos])

    def is_feasible(self):
        """
        Returns true if the problem is feasible and false otherwise. Pareto set must be computed before calling this
        function.
        """
        if self.pareto_set is None:
            raise ValueError("Could not evaluate is_feasible. Compute Pareto set first.")
        else:
            return len(self.pareto_set) > 0

    def calculate_active_constraints(self):
        """
        Calculates which constraints are active, meaning they have at least one point lying on them.

        Returns indices of active linear, quadratic, and multi constraints (each returned as a separate set).
        """
        if self.active_constraints is None:
            raise ValueError(
                "Could not evaluate calculate_active_constraints. Compute Pareto set with compute_active=True first.")
        else:
            linear_set = set()
            quadratic_set = set()
            multi_set = set()
            for ac_l, ac_c, ac_m in self.active_constraints:
                linear_set |= ac_l
                quadratic_set |= ac_c
                multi_set |= ac_m
            return linear_set, quadratic_set, multi_set

    def calculate_binding_constraints(self, tol=1e-8, **params):
        """
        Calculates which constraints are binding, meaning that the Pareto set changes when they are removed.
        The argument params contain the parameters that are passed to calculate_pareto_set_and_front function.
        
        Parameters:
        - tol: the solution to the subproblem is considered new if it violates the original problem's constraint by
        more than this tolerance
        - params: parameters used by the calculate_pareto_set_and_front function to compute the Pareto set of the
        subproblem

        Returns indices of binding linear, quadratic, and multi constraints (each returned as a separate set).
        """
        binding_linear_constraints = set()
        binding_quadratic_constraints = set()
        binding_multi_constraints = set()
        for i in range(len(self.constraints['Linear'])):
            subproblem = copy.deepcopy(self)
            sub_constr_i = subproblem.linear_constraints[i]
            del subproblem.linear_constraints[i]
            subproblem.calculate_pareto_set_and_front(**params)
            if check_binding(sub_constr_i, evaluate_linear_constraint, subproblem.pareto_set, tol):
                binding_linear_constraints.add(i)
        for i in range(len(self.constraints['Quadratic'])):
            subproblem = copy.deepcopy(self)
            sub_constr_i = subproblem.quadratic_constraints[i]
            del subproblem.quadratic_constraints[i]
            subproblem.calculate_pareto_set_and_front(**params)
            if check_binding(sub_constr_i, evaluate_quadratic_constraint, subproblem.pareto_set, tol):
                binding_quadratic_constraints.add(i)
        for i in range(len(self.constraints['Multi'])):
            subproblem = copy.deepcopy(self)
            sub_constr_i = subproblem.multi_constraints[i]
            del subproblem.multi_constraints[i]
            subproblem.calculate_pareto_set_and_front(**params)
            if check_binding(sub_constr_i, evaluate_multi_constraint, subproblem.pareto_set, tol):
                binding_multi_constraints.add(i)
        return ({x + 1 for x in binding_linear_constraints},
                {x + 1 for x in binding_quadratic_constraints},
                {x + 1 for x in binding_multi_constraints})  # Add 1 to make the indices in the output start at 1

    def calculate_ps_pf_parts(self):
        """
        Calculates how many parts Pareto set and front consist of.
        """
        if self.pareto_set is None:
            raise ValueError("Could not evaluate calculate_ps_pf_parts. Compute Pareto set first.")
        elif len(self.pareto_set) == 0:
            return 0, 0
        else:
            sampling = self.sampling_options['sampling']
            if sampling == 'error':
                parameter = self.sampling_options['max_error']
            elif sampling in ['curve-dist', 'curve-dist-rf', 'projection', 'front']:
                parameter = self.sampling_options['distance']
            else:
                parameter = self.sampling_options['n_points']
            if sampling == 'Equidistant':
                dist_thresh = parameter * 3
            else:
                dist_thresh = 10 * np.sqrt(self.n_var) / parameter * 10
            if len(self.pareto_set) > 1:
                ps_parts = count_curves_agglomerative(self.pareto_set, distance_threshold=dist_thresh)
            else:
                ps_parts = 0
            min_x, min_y = np.min(self.pareto_front, axis=0)
            max_x, max_y = np.max(self.pareto_front, axis=0)
            dist = np.linalg.norm(np.array([min_x, max_y]) - np.array([max_x, min_y]))
            if len(self.pareto_front) > 1:
                pf_parts = count_curves_agglomerative(self.pareto_front,
                                                    distance_threshold=dist / len(self.pareto_front) * 10)
            else:
                pf_parts = 0
            return ps_parts, pf_parts

    def characterise_problem(self):
        if self.pareto_set is None or len(self.pareto_set) == 0:
            print('Could not characterise problem. Please compute Pareto set first.')
            return None, None, None

        ps_parts, pf_parts = self.calculate_ps_pf_parts()
        in_bounds = all(-5 < d < 5 for pt in self.pareto_set for d in pt)
        return ps_parts, pf_parts, in_bounds

    def save_problem(self, filename):
        """ Saves the problem with computed results to the specified file. """
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    def get_figure(self, algorithm_X=None, algorithm_F=None, algorithm_name='Algorithm', ax0=0, ax1=1,
                   plot_objective_space=True, plot_search_space=True, plot_unconstrained_pareto=True,
                   plot_constrained_pareto=True, plot_normalized=False, shade_infeasible=True,
                   color_peaks=False, plot_large_peak_centers=True,
                   shade_infeasible_multi_constraints=True, multi_constraint_single_label=False,
                   plot_local_constrained_pareto_sets=False, plot_local_unconstrained_pareto_sets=False,
                   rasterized=True, fig_width=3.5, cmap=CMAP):

        num_plots = 2 if plot_objective_space and plot_search_space else 1

        _, axes = plt.subplots(1, num_plots, figsize=(fig_width * num_plots, fig_width))

        ax = axes if num_plots == 1 else axes[0]
        peak_color1 = peak_color2 = 'black'
        levels_color1 = levels_color2 = 'gray'
        linewidths = 0.5
        if color_peaks:
            peak_color1 = cm.get_cmap('Set1')(0)
            peak_color2 = cm.get_cmap('Accent')(4)
            levels_color1 = [peak_color1]
            levels_color2 = [peak_color2]
            linewidths = 1

        if plot_search_space:
            if self.n_var == 2:
                # Define the grid for contour plotting
                x_range = np.linspace(self.xl[ax0], self.xu[ax0], 100)
                y_range = np.linspace(self.xl[ax1], self.xu[ax1], 100)
                X, Y = np.meshgrid(x_range, y_range)
                grid = np.stack([X, Y], axis=-1)

                # Calculate function values for contour plots
                Z1 = np.apply_along_axis(lambda x: multi_peak_function(x, self.objectives[0]['c'], self.objectives[0]['H']), -1, grid)
                Z2 = np.apply_along_axis(lambda x: multi_peak_function(x, self.objectives[1]['c'], self.objectives[1]['H']), -1, grid)

                ax.contour(X, Y, Z1, levels=25, colors=levels_color1, alpha=0.3, linewidths=linewidths)
                ax.contour(X, Y, Z2, levels=25, colors=levels_color2, alpha=0.3, linewidths=linewidths)

            # Plot the peak centers for f1 and f2
            if plot_large_peak_centers:
                ax.scatter(self.objectives[0]['c'][:, ax0], self.objectives[0]['c'][:, ax1],
                           color=peak_color1, marker='x', s=100, rasterized=rasterized)
                ax.scatter(self.objectives[1]['c'][:, ax0], self.objectives[1]['c'][:, ax1],
                           color=peak_color2, marker='+', s=100 * 1.4, rasterized=rasterized)
                for i in range(len(self.objectives[0]['c'])):
                    point_name = f'$c_{{1,{i + 1}}}$' if len(self.objectives[0]['c']) > 1 else '$c_1$'
                    ax.text(self.objectives[0]['c'][i, ax0] + 0.3, self.objectives[0]['c'][i, ax1] - 0.5, point_name,
                            fontsize=16, color=peak_color1, zorder=4)
                for i in range(len(self.objectives[1]['c'])):
                    point_name = f'$c_{{2,{i + 1}}}$' if len(self.objectives[1]['c']) > 1 else '$c_2$'
                    ax.text(self.objectives[1]['c'][i, ax0] + 0.3, self.objectives[1]['c'][i, ax1] - 0.5, point_name,
                            fontsize=16, color=peak_color2, zorder=4)
            else:
                ax.scatter(self.objectives[0]['c'][:, ax0], self.objectives[0]['c'][:, ax1],
                           color=peak_color1, marker='x', s=40, rasterized=rasterized)
                ax.scatter(self.objectives[1]['c'][:, ax0], self.objectives[1]['c'][:, ax1],
                           color=peak_color2, marker='+', s=40 * 1.4, rasterized=rasterized)

            # Plot all constraints
            grid = get_grid()
            plot_linear_constraints(ax, self.constraints['Linear'], ax0, ax1, cmap, shade=shade_infeasible, grid=grid)
            start_index = len(self.constraints['Linear'])
            plot_quadratic_constraints(ax, self.constraints['Quadratic'], ax0, ax1, cmap, shade=shade_infeasible,
                                       grid=grid, base_index=start_index)
            start_index = len(self.constraints['Linear']) + len(self.constraints['Quadratic'])
            plot_multi_constraints(ax, self.constraints['Multi'], ax0, ax1, cmap,
                                   shade=shade_infeasible_multi_constraints, grid=grid,
                                   single_label=multi_constraint_single_label,
                                   start_index=start_index)

            # Plot the constrained Pareto set and algorithm results
            if self.pareto_set is not None and len(self.pareto_set) > 0 and plot_constrained_pareto:
                ax.scatter(self.pareto_set[:, ax0], self.pareto_set[:, ax1], label='Pareto set',
                           color='black', zorder=2, s=10, rasterized=rasterized)

            # Plot local unconstrained Pareto sets
            if self.local_unconstrained_pareto_sets is not None and plot_local_unconstrained_pareto_sets:
                for i, (_, local_pareto_set) in enumerate(self.local_unconstrained_pareto_sets.items()):
                    if len(local_pareto_set) > 0:
                        color = cm.get_cmap('Set2')(2 * i + 1)
                        ax.scatter(local_pareto_set[:, ax0], local_pareto_set[:, ax1],
                                   label='Local Unconstrained Pareto set',
                                   color=color, zorder=2, s=10, rasterized=rasterized)

            # Plot local constrained Pareto sets
            if self.local_pareto_sets is not None and plot_local_constrained_pareto_sets:
                for i, (_, local_pareto_set) in enumerate(self.local_pareto_sets.items()):
                    if len(local_pareto_set) > 0:
                        color = cm.get_cmap('Set2')(2 * i)
                        ax.scatter(local_pareto_set[:, ax0], local_pareto_set[:, ax1], label='Local Pareto set',
                                   color=color, zorder=2, s=10, rasterized=rasterized)

            # Plot the unconstrained Pareto set
            if self.uncon_pareto_set is not None and plot_unconstrained_pareto:
                ax.scatter(self.uncon_pareto_set[:, ax0], self.uncon_pareto_set[:, ax1], label='Uncon. Pareto set',
                           color='grey', s=3, alpha=1, rasterized=rasterized)

            # Plot the algorithm results
            if algorithm_X is not None:
                ax.scatter([x[ax0] for x in algorithm_X], [x[ax1] for x in algorithm_X], label=algorithm_name,
                           color='green', s=2, zorder=5, rasterized=rasterized)

            ax.set_title(f'Search space ($n={self.n_var}$)')
            ax.set_xlabel(f'$x_{ax0 + 1}$', size='larger')
            ax.set_ylabel(f'$x_{ax1 + 1}$', size='larger', rotation=0, labelpad=5)
            ax.legend(fontsize='small')
            ax.set_xlim(self.xl[ax0], self.xu[ax0])
            ax.set_ylim(self.xl[ax1], self.xu[ax1])
            ax.set_aspect('equal', adjustable='box')

        if plot_objective_space:
            ax = axes[1] if plot_search_space else axes
            # Evaluate and plot the Pareto front in the objective space
            if self.pareto_front is not None and 0 < len(self.pareto_front) and plot_constrained_pareto:
                if plot_normalized:
                    ideal = self.ideal_point()
                    nadir = self.nadir_point()
                    normalized_pf = (self.pareto_front - ideal) / (nadir - ideal)
                    ax.scatter(normalized_pf[:, 0], normalized_pf[:, 1],
                               color='black', s=10, zorder=2, label='Pareto front', rasterized=rasterized)
                else:
                    ax.scatter(self.pareto_front[:, 0], self.pareto_front[:, 1],
                               s=10, zorder=2, c='black', label='Pareto front', rasterized=rasterized)

                    # Plot local unconstrained Pareto fronts
                    if self.local_unconstrained_pareto_fronts is not None and plot_local_unconstrained_pareto_sets:
                        for i, (_, local_pareto_front) in enumerate(self.local_unconstrained_pareto_fronts.items()):
                            if len(local_pareto_front) > 0:
                                color = cm.get_cmap('Set2')(2 * i + 1)
                                ax.scatter(local_pareto_front[:, ax0], local_pareto_front[:, ax1],
                                           label='Local Unconstrained Pareto front',
                                           color=color, zorder=2, s=10, rasterized=rasterized)

                    # Plot local constrained Pareto fronts
                    if self.local_pareto_fronts is not None and plot_local_constrained_pareto_sets:
                        for i, (_, local_pareto_front) in enumerate(self.local_pareto_fronts.items()):
                            if len(local_pareto_front) > 0:
                                color = cm.get_cmap('Set2')(2 * i)
                                ax.scatter(local_pareto_front[:, ax0], local_pareto_front[:, ax1],
                                           label='Local Pareto front',
                                           color=color, zorder=2, s=10, rasterized=rasterized)

            if self.uncon_pareto_front is not None and plot_unconstrained_pareto:
                if plot_normalized:
                    ideal = self.ideal_point()
                    nadir = self.nadir_point()
                    normalized_upf = (self.uncon_pareto_front - ideal) / (nadir - ideal)
                    ax.scatter(normalized_upf[:, 0], normalized_upf[:, 1],
                               c='grey', s=3, label='Uncon. Pareto front', rasterized=rasterized)
                else:
                    ax.scatter(self.uncon_pareto_front[:, 0], self.uncon_pareto_front[:, 1],
                               c='grey', s=3, label='Uncon. Pareto front', rasterized=rasterized)

            if algorithm_F is not None and len(algorithm_F) > 0:
                ax.scatter(algorithm_F[:, 0], algorithm_F[:, 1], c='green', s=1, label=algorithm_name, zorder=5,
                           rasterized=rasterized)

            str_alpha = str(self.transformation_alpha[0]) + ', ' + str(self.transformation_alpha[1])
            if str_alpha == '1, 1':
                str_alpha = ''
            else:
                str_alpha = f' ($\\alpha=({str_alpha})$)'
            ax.set_title("Objective space ($m=2$)" + str_alpha)
            ax.set_xlabel(f'$f_1$', size='larger')
            ax.set_ylabel(f'$f_2$', size='larger', rotation=0, labelpad=5)
            ax.grid(True, which='both', linestyle='--')
            ax.legend(fontsize='small')

            if plot_normalized:
                ax.set_xlim(-0.1, 1.1)
                ax.set_ylim(-0.1, 1.1)
                ax.set_title('Norm. objective space ($m=2$)' + str_alpha)

        return axes

    def save_figure(self, algorithm_X=None, algorithm_name='Algorithm', show=False, save=False,
                    folder='plots', extension='png', dpi=300, plot_name=None, **kwargs):

        # Save or show the plot
        plt.tight_layout()
        if save:
            if plot_name is None:
                plot_name = f'problem_{self.name}_dim_{self.n_var}'
            if algorithm_X is not None:
                plt.savefig(f'{folder}/{plot_name}-{algorithm_name}.{extension}', dpi=dpi)
            else:
                plt.savefig(f'{folder}/{plot_name}.{extension}', dpi=dpi)
        if show:
            plt.show()
        plt.close()

    def visualize(self, algorithm_X=None, algorithm_F=None, algorithm_name='Algorithm', show=False, save=False,
                  folder='plots', extension='png', dpi=300, plot_name=None, ax0=0, ax1=1,
                  plot_objective_space=True, plot_search_space=True, plot_unconstrained_pareto=True,
                  plot_constrained_pareto=True,
                  plot_normalized=False, shade_infeasible=True, color_peaks=False, plot_large_peak_centers=True,
                  shade_infeasible_multi_constraints=True, multi_constraint_single_label=False,
                  plot_local_constrained_pareto_sets=False, plot_local_unconstrained_pareto_sets=False, rasterized=True,
                  fig_width=3.5, cmap=CMAP):

        self.get_figure(algorithm_X=algorithm_X, algorithm_F=algorithm_F, algorithm_name=algorithm_name,
                        ax0=ax0, ax1=ax1, plot_objective_space=plot_objective_space,
                        plot_search_space=plot_search_space,
                        plot_unconstrained_pareto=plot_unconstrained_pareto,
                        plot_constrained_pareto=plot_constrained_pareto,
                        plot_normalized=plot_normalized, shade_infeasible=shade_infeasible,
                        color_peaks=color_peaks, plot_large_peak_centers=plot_large_peak_centers,
                        shade_infeasible_multi_constraints=shade_infeasible_multi_constraints,
                        multi_constraint_single_label=multi_constraint_single_label,
                        plot_local_constrained_pareto_sets=plot_local_constrained_pareto_sets,
                        plot_local_unconstrained_pareto_sets=plot_local_unconstrained_pareto_sets,
                        rasterized=rasterized, fig_width=fig_width, cmap=cmap)

        self.save_figure(algorithm_X=algorithm_X, algorithm_name=algorithm_name, show=show, save=save, folder=folder,
                         extension=extension, dpi=dpi, plot_name=plot_name)
        
    def to_string(self, n_digits=4):
        out = []
        out.append("=== Problem Data ===")
        out.append(f"Num constraints: {self.n_constr}")
        out.append(f"Peaks F1 / F2: {len(self.objectives[0]['c'])} / {len(self.objectives[1]['c'])}")
        for i, obj in enumerate(self.objectives):
            out.append(f"\n-- Objective F{i+1} --")
            out.append("Centers:")
            out.append(np.array2string(np.array(obj['c']), separator=', ', precision=n_digits))
            out.append("V-Shifts:")
            out.append(np.array2string(np.array(obj['b']), separator=', ', precision=n_digits))
            out.append("Hessians:")
            for H in obj['H']:
                out.append(np.array2string(H, separator=', ', precision=n_digits))
        out.append("\n-- Constraints --")
        for key in ['Linear', 'Quadratic', 'Multi']:
            out.append(f"{key}:")
            data = self.constraints.get(key, [])
            if key == 'Multi':
                for i, group in enumerate(data):
                    out.append(f" Group {i+1}:")
                    for j, sub in enumerate(group):
                        out.append(f"  Subgroup {j+1}:")
                        for subkey in ['Linear', 'Quadratic']:
                            if subkey in sub:
                                out.append(f"   {subkey}:")
                                for item in sub[subkey]:
                                    for k, v in item.items():
                                        if isinstance(v, np.ndarray):
                                            out.append(f"    {k}:")
                                            s = np.array2string(np.array(v), separator=', ', precision=n_digits)
                                            indent_str = ' ' * 6
                                            out.append('\n'.join(indent_str + line for line in s.splitlines()))
                                        else:
                                            out.append(f"    {k}: {v}")
            else:
                for item in data:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if isinstance(v, np.ndarray):
                                v_str = np.array2string(v, separator=', ', precision=n_digits)
                            else:
                                v_str = str(v)
                            out.append(f" {k}: {v_str}")
                    else:
                        out.append(f" {item}")
        return "\n".join(out)

    def __str__(self):
        return self.to_string(n_digits=4)