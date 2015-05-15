__author__ = 'latty'

import numpy as np
import math
import timeit


bc_nbSegments = 32
results = {}
np_array_troncons_pcs = []

# from Scipy.interpolate import interp1d
# urls:
# - http://docs.scipy.org/doc/scipy/reference/tutorial/interpolate.html#d-interpolation-interp1d
# - http://stackoverflow.com/questions/11018433/is-there-any-non-scipy-code-out-there-that-will-create-smooth-interpolations-of


# inspiration pour la generation de la courbe de Bezier
# url : http://www.codeproject.com/Articles/25237/Bezier-Curves-Made-Simple
FactorialLookup = [
    1.0,
    1.0,
    2.0,
    6.0,
    24.0,
    120.0,
    720.0,
    5040.0,
    40320.0,
    362880.0,
    3628800.0,
    39916800.0,
    479001600.0,
    6227020800.0,
    87178291200.0,
    1307674368000.0,
    20922789888000.0,
    355687428096000.0,
    6402373705728000.0,
    121645100408832000.0,
    2432902008176640000.0,
    51090942171709440000.0,
    1124000727777607680000.0,
    25852016738884976640000.0,
    620448401733239439360000.0,
    15511210043330985984000000.0,
    403291461126605635584000000.0,
    10888869450418352160768000000.0,
    304888344611713860501504000000.0,
    8841761993739701954543616000000.0,
    265252859812191058636308480000000.0,
    8222838654177922817725562880000000.0,
    263130836933693530167218012160000000.0
]


def factorial(n):
    """
    just check if n is appropriate, then return the result

    :param n:
    :return: returns the value n! as a SUMORealing point number
    """
    # if (n < 0) { throw new Exception("n is less than 0"); }
    # if (n > 32) { throw new Exception("n is greater than 32"); }

    return FactorialLookup[n]


def Ni(n, i):
    """

    :param n:
    :param i:
    :return:
    """
    a1 = factorial(n)
    a2 = factorial(i)
    a3 = factorial(n - i)
    ni = a1/(a2 * a3)
    return ni


def Bernstein(n, i, t):
    """
    Calculate Bernstein basis

    :param n:
    :param i:
    :param t:
    :return:
    """
    ti = 1.0
    if not (t == 0.0 and i == 0):
        ti = math.pow(t, i)

    tni = 1.0
    if not (n == i and t == 1.0):
        tni = math.pow((1 - t), (n - i))

    # Bernstein basis
    basis = Ni(n, i) * ti * tni
    return basis


# url: http://people.sc.fsu.edu/~jburkardt/cpp_src/bernstein_polynomial/bernstein_polynomial.html
def bernstein_poly_01(n, x):
    """
    ****************************************************************************

      Purpose:

        BERNSTEIN_POLY_01 evaluates the Bernstein polynomials based in [0,1].

      Discussion:

        The Bernstein polynomials are assumed to be based on [0,1].

        The formula is:

          B(N,I)(X) = [N!/(I!*(N-I)!)] * (1-X)^(N-I) * X^I

      First values:

        B(0,0)(X) = 1

        B(1,0)(X) =      1-X
        B(1,1)(X) =                X

        B(2,0)(X) =     (1-X)^2
        B(2,1)(X) = 2 * (1-X)    * X
        B(2,2)(X) =                X^2

        B(3,0)(X) =     (1-X)^3
        B(3,1)(X) = 3 * (1-X)^2 * X
        B(3,2)(X) = 3 * (1-X)   * X^2
        B(3,3)(X) =               X^3

        B(4,0)(X) =     (1-X)^4
        B(4,1)(X) = 4 * (1-X)^3 * X
        B(4,2)(X) = 6 * (1-X)^2 * X^2
        B(4,3)(X) = 4 * (1-X)   * X^3
        B(4,4)(X) =               X^4

      Special values:

        B(N,I)(X) has a unique maximum value at X = I/N.

        B(N,I)(X) has an I-fold zero at 0 and and N-I fold zero at 1.

        B(N,I)(1/2) = C(N,K) / 2^N

        For a fixed X and N, the polynomials add up to 1:

          Sum ( 0 <= I <= N ) B(N,I)(X) = 1

      Licensing:

        This code is distributed under the GNU LGPL license.

      Modified:

        29 July 2011

      Author:

        John Burkardt

      Parameters:

        Input, int N, the degree of the Bernstein polynomials
        to be used.  For any N, there is a set of N+1 Bernstein polynomials,
        each of degree N, which form a basis for polynomials on [0,1].

        Input, double X, the evaluation point.

        Output, double BERNSTEIN_POLY[N+1], the values of the N+1
        Bernstein polynomials at X.
    """
    coefs_bernstein = [0.0]*(n+1)

    # if n == 0:
    # elif 0 < n:
    coefs_bernstein[0] = 1.0 - x
    coefs_bernstein[1] = x

    for i in range(2, n+1):
        coefs_bernstein[i] = x * coefs_bernstein[i-1]
        for j in range(i-1, 0, -1):
            coefs_bernstein[j] = x * coefs_bernstein[j-1] + (1.0 - x) * coefs_bernstein[j]
        coefs_bernstein[0] *= 1.0 - x
    return coefs_bernstein

def build_bezier_curve_from_PCs(list_PCs, nbSegments=30):
    """

    :param list_PCs:
    :param nbSegments:
    :return:
    """
    # print 'nbSegments: ', nbSegments
    npts = len(list_PCs)
    tstep = 1.0/(nbSegments+1)
    list_interpoled_points = [
        reduce(lambda x, y: x+y, [Bernstein(npts-1, i, t) * list_PCs[i] for i in range(0, npts, 1)])
        for t in np.arange(0.0, 1.0+tstep, tstep)
    ]
    return np.array(list_interpoled_points), list_PCs[1:-1]

def build_bezier_curve_from_PCs_with_optim_bernstein(list_PCs, nbSegments=30):
    """

    :param list_PCs:
    :param nbSegments:
    :return:
    """
    npts = len(list_PCs)
    tstep = 1.0/(nbSegments+1)
    list_interpoled_points = [
        sum(coef_bernstein*pc for coef_bernstein, pc in zip(bernstein_poly_01(npts, t), list_PCs))
        for t in np.arange(0.0, 1.0+tstep, tstep)
    ]
    return np.array(list_interpoled_points), list_PCs[1:-1]

def line(p1, p2):
    """

    :param p1:
    :param p2:
    :return:
    """
    A = (p1[1] - p2[1])
    B = (p2[0] - p1[0])
    C = (p1[0]*p2[1] - p2[0]*p1[1])
    return A, B, -C


def intersection(L1, L2):
    """

    :param L1:
    :param L2:
    :return:
    """
    D = L1[0] * L2[1] - L1[1] * L2[0]
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    #
    inv_D = 1 / D   # safe dans notre cas car on teste l'angle entre les lignes avant de calculer l'intersection
    #
    x = Dx * inv_D
    y = Dy * inv_D
    return x, y


def is_parallel_lines(line0, line1, threshold_acos_angle=0.875):
    """

    :param line0:
    :param line1:
    :param threshold_acos_angle:
    :return:
    """
    seg_P0P1 = [line0[1], line0[0]]
    seg_P3P2 = [line1[1], line1[0]]
    #
    vec_dir_P0P1 = seg_P0P1 / np.linalg.norm(seg_P0P1)
    vec_dir_P3P2 = seg_P3P2 / np.linalg.norm(seg_P3P2)
    #
    cos_angle = np.dot(vec_dir_P0P1, vec_dir_P3P2)
    #
    return abs(cos_angle) >= threshold_acos_angle


def create_bezier_curve_from_3points(
        point_start,
        point_end,
        point_control,
        nbSegments=30
):
    """

    :param point_start: [x, y]
    :param point_end: [x, y]
    :param point_control: [x, y]
    :param nbSegments: unsigned int (>0)
    :return: np array des points representant une discretisation du segment de bezier definit
    par le point start, end et le point de control
    """

    tstep = 1.0/nbSegments

    composantes_x = [point_start[0], point_control[0], point_end[0]]
    composantes_y = [point_start[1], point_control[1], point_end[1]]

    # url: http://docs.scipy.org/doc/numpy/reference/generated/numpy.arange.html
    return np.array([
        [
            np.dot(berstein, composantes_x),
            np.dot(berstein, composantes_y)
        ]
        for berstein in [[(1-t)**2, (2*t)*(1-t), t**2] for t in np.arange(0.0, 1.0, tstep)]
    ])


def create_bezier_curve(
        np_array_points,
        threshold_acos_angle=0.875,
        nbSegments=30
):
    """

    :param np_array_points: [P0, P1, P2, P3]
        [P0, P1]: segment du troncon 1 (amont vers aval)
        [P3, P2]: segment du troncon 2 (amont vers aval)
    :param threshold_acos_angle:
        Seuil limite pour qualifier les segments comme etant paralleles.
        On envoie directement le acos de l'angle (optim).
        Par defaut on est sur un angle limite de PI/8 => 1.0 - acos(PI/8) ~= 0.875
    :param nbSegments:
        Indice de discretisation du segment de bezier genere
    :return: tuple(list_points=np_array(2D Point), PC=np_array(2D Point))
        np array de la liste des points representant le segment de bezier
        np array de la liste des points de controle (dans le cas de cette methode: liste d'1 seul PC)
    """
    P0, P1, P2, P3 = np_array_points
    #
    line_P0P1 = line(P0, P1)
    line_P3P2 = line(P3, P2)
    #
    lambdas_compute_PC = [
        lambda: intersection(line_P0P1, line_P3P2),
        lambda: (P1 + P2) * 0.5
    ]
    PC = lambdas_compute_PC[is_parallel_lines(line_P0P1, line_P3P2, threshold_acos_angle)]()

    # Calcul des points intermediaires
    np_segment_bezier = create_bezier_curve_from_3points(P1, P2, PC, nbSegments)

    return np_segment_bezier, np.array([PC])


def create_bezier_curve_with_list_PC(
        np_array_points,
        threshold_acos_angle=0.875
):
    """

    :param np_array_points: [P0, P1, PC0, PC1, ..., PC(n-1), P2, P3]
        [P0, P1]: segment du troncon 1 (amont vers aval)
        [P3, P2]: segment du troncon 2 (amont vers aval)
        PC0, PC1, ..., PC(n-1): liste des points de controles pour la spline (en plus de P1 et P2)
    :param threshold_acos_angle:
        Seuil limite pour qualifier les segments comme etant paralleles.
        On envoie directement le acos de l'angle (optim).
        Par defaut on est sur un angle limite de PI/8 => 1.0 - acos(PI/8) ~= 0.875
    :param nbSegments:
        Indice de discretisation du segment de bezier genere
    :return: tuple(list_points=np_array, PC=[x, y])
        np array de la liste des points representant le segment de bezier
        np array de la liste des points de controle (de 1 a (n-1))
    """
    list_PC = np_array_points[1:-1]
    list_func_generate_spline = [
        (build_bezier_curve_from_PCs, [list_PC, bc_nbSegments]),
        (create_bezier_curve, [np_array_points, threshold_acos_angle, bc_nbSegments])
    ]
    # list_PC.size == 4 <=> list_PC = [P1, P2]
    tuple_func_params = list_func_generate_spline[list_PC.size == 4]
    # on renvoit la liste des points generes par la spline d'interpolation
    # et la liste des points de controles
    return tuple_func_params[0](*tuple_func_params[1])

def build_bezier_curve_from_Troncons_PCs(
        np_array_points
):
    """

    :param np_array_points: [P0, P1, PC0, PC1, ..., PC(n-1), P2, P3]
        [P0, P1]: segment du troncon 1 (amont vers aval)
        [P3, P2]: segment du troncon 2 (amont vers aval)
        PC0, PC1, ..., PC(n-1): liste des points de controles pour la spline (en plus de P1 et P2), n>0
    :param threshold_acos_angle:
        Seuil limite pour qualifier les segments comme etant paralleles.
        On envoie directement le acos de l'angle (optim).
        Par defaut on est sur un angle limite de PI/8 => 1.0 - acos(PI/8) ~= 0.875
    :return: tuple(list_points=np_array, PC=[x, y])
        np array de la liste des points representant le segment de bezier
        np array de la liste des points de controle (de 1 a (n-1))
    """
    return build_bezier_curve_from_PCs(np_array_points[1:-1], bc_nbSegments)

def build_bezier_curves_from_Troncons_PCs(
        np_array_Troncons_PCs
):
    """
    """
    def wrapper_map(np_Troncons_PCs):
        # return build_bezier_curve_from_PCs(np_Troncons_PCs[1:-1], bc_nbSegments)
        return build_bezier_curve_from_PCs_with_optim_bernstein(np_Troncons_PCs[1:-1], bc_nbSegments)

    return [map(wrapper_map, np_array_Troncons_PCs)]

import multiprocessing as mp

def mp_map_build_bezier_curves_from_Troncons_PCs(
        np_array_Troncons_PCs,
        processes=4,
        nbSegments=30
):
    """

    :param np_array_Troncons_PCs: [[P0, P1, PC0, PC1, ..., PC(n-1), P2, P3]+]
        [P0, P1]: segment du troncon 1 (amont vers aval)
        [P3, P2]: segment du troncon 2 (amont vers aval)
        PC0, PC1, ..., PC(n-1): liste des points de controles pour la spline (en plus de P1 et P2), n > 0
    :param nbSegments:
        Indice de discretisation du segment de bezier genere
    :return: tuple(list_points=np_array, PC=[x, y])
        np array de la liste des points representant le segment de bezier
        np array de la liste des points de controle (de 1 a (n-1))
    """
    global bc_nbSegments
    bc_nbSegments = nbSegments

    mp_results = None

    pool = mp.Pool(processes=processes)
    try:
        mp_results = pool.map(build_bezier_curve_from_Troncons_PCs, np_array_Troncons_PCs)
    finally:
        # url: http://stackoverflow.com/questions/20914828/python-multiprocessing-pool-join-not-waiting-to-go-on
        # on termine les calculs, et clean les processus
        pool.close()
        pool.join()

    # on renvoie le resultat
    return mp_results

def mp_map_sliced_build_bezier_curves_from_Troncons_PCs(
        np_array_Troncons_PCs,
        processes=4,
        nbSegments=30
):
    """

    :param np_array_Troncons_PCs: [[P0, P1, PC0, PC1, ..., PC(n-1), P2, P3]+]
        [P0, P1]: segment du troncon 1 (amont vers aval)
        [P3, P2]: segment du troncon 2 (amont vers aval)
        PC0, PC1, ..., PC(n-1): liste des points de controles pour la spline (en plus de P1 et P2), n > 0
    :param nbSegments:
        Indice de discretisation du segment de bezier genere
    :return: tuple(list_points=np_array, PC=[x, y])
        np array de la liste des points representant le segment de bezier
        np array de la liste des points de controle (de 1 a (n-1))
    """
    global bc_nbSegments
    bc_nbSegments = nbSegments

    mp_compact_results = None
    list_slices_on_datas = distribute(len(np_array_Troncons_PCs), processes)
    datas_sliced = []
    for slice in list_slices_on_datas:
        datas_sliced.append(np_array_Troncons_PCs[slice[0]:slice[1]])

    pool = mp.Pool(processes=processes)
    try:
        mp_compact_results = pool.map(build_bezier_curves_from_Troncons_PCs, datas_sliced)
    finally:
        # url: http://stackoverflow.com/questions/20914828/python-multiprocessing-pool-join-not-waiting-to-go-on
        # on termine les calculs, et clean les processus
        pool.close()
        pool.join()

    # flat the results
    # url: http://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python
    # print 'mp_compact_results: ', mp_compact_results
    mp_results = [item for sublist in mp_compact_results for item in sublist[0]]

    # on renvoie le resultat
    return mp_results

def mp_create_bezier_curve_with_list_PC(
        np_array_list_points,
        processes=4,
        nbSegments=30
):
    """

    :param np_array_list_points: [[P0, P1, PC0, PC1, ..., PC(n-1), P2, P3]+]
        [P0, P1]: segment du troncon 1 (amont vers aval)
        [P3, P2]: segment du troncon 2 (amont vers aval)
        PC0, PC1, ..., PC(n-1): liste des points de controles pour la spline (en plus de P1 et P2), n > 0
    :param threshold_acos_angle:
        Seuil limite pour qualifier les segments comme etant paralleles.
        On envoie directement le acos de l'angle (optim).
        Par defaut on est sur un angle limite de PI/8 => 1.0 - acos(PI/8) ~= 0.875
    :param nbSegments:
        Indice de discretisation du segment de bezier genere
    :return: tuple(list_points=np_array, PC=[x, y])
        np array de la liste des points representant le segment de bezier
        np array de la liste des points de controle (de 1 a (n-1))
    """
    global bc_nbSegments
    bc_nbSegments = nbSegments

    mp_results = None
    pool = mp.Pool(processes=processes)
    try:
        mp_results = [
            pool.apply_async(build_bezier_curve_from_Troncons_PCs, args=([np_array_points]))
            for np_array_points in np_array_list_points
        ]
    finally:
        # clean les processus
        # url: http://stackoverflow.com/questions/20914828/python-multiprocessing-pool-join-not-waiting-to-go-on
        pool.close()
        pool.join()
        # on recupere les resultats (pour etre sure de synchroniser les asynch processus)
        mp_results = [p.get() for p in mp_results]

    return mp_results

def serial_create_bezier_curve_with_list_PC(
        np_array_list_points,
        nbSegments=30
):
    """

    :param np_array_list_points: [[P0, P1, PC0, PC1, ..., PC(n-1), P2, P3]+]
        [P0, P1]: segment du troncon 1 (amont vers aval)
        [P3, P2]: segment du troncon 2 (amont vers aval)
        PC0, PC1, ..., PC(n-1): liste des points de controles pour la spline (en plus de P1 et P2), n > 0
    :param threshold_acos_angle:
        Seuil limite pour qualifier les segments comme etant paralleles.
        On envoie directement le acos de l'angle (optim).
        Par defaut on est sur un angle limite de PI/8 => 1.0 - acos(PI/8) ~= 0.875
    :param nbSegments:
        Indice de discretisation du segment de bezier genere
    :return: tuple(list_points=np_array, PC=[x, y])
        np array de la liste des points representant le segment de bezier
        np array de la liste des points de controle (de 1 a (n-1))
    """
    global bc_nbSegments
    bc_nbSegments = nbSegments

    return map(build_bezier_curve_from_Troncons_PCs, np_array_list_points)

# TEST
def benchmark(n=2**12, nbSegments=32, processus=4, b_plot_curves=True):
    """

    :param n:
    :return:
    """
    global results
    global np_array_troncons_pcs

    results = {}
    np_array_troncons_pcs = []

    #url: http://sebastianraschka.com/Articles/2014_multiprocessing_intro.html
    for i in range(0, n):
        np_array_troncons_pcs.append(np.array([[0, 2], [1, 2], [1.5, 2], [2, 1.5], [2, 1], [2, 0]]))

    benchmark_results = [
        timeit.Timer(
            "results['serial'] = serial_create_bezier_curve_with_list_PC(np_array_troncons_pcs, %s)" % nbSegments,
            'from script_generate_bezier_curve import serial_create_bezier_curve_with_list_PC, np_array_troncons_pcs, results'
        ).timeit(number=1),
        timeit.Timer(
            "results['mp'] = mp_create_bezier_curve_with_list_PC(np_array_troncons_pcs, %s, %s)" % (processus, nbSegments),
            'from script_generate_bezier_curve import mp_create_bezier_curve_with_list_PC, np_array_troncons_pcs, results'
        ).timeit(number=1),
        timeit.Timer(
            "results['mp_map'] = mp_map_build_bezier_curves_from_Troncons_PCs(np_array_troncons_pcs, %s, %s)" % (processus, nbSegments),
            'from script_generate_bezier_curve import mp_map_build_bezier_curves_from_Troncons_PCs, np_array_troncons_pcs, results'
        ).timeit(number=1),
    ]

    nb_cpu = mp.cpu_count()

    # url: http://docs.scipy.org/doc/numpy/reference/generated/numpy.array_equal.html
    print "len(results['mp_map']): ", len(results['mp_map'])
    print "len(results['mp']): ", len(results['mp'])
    print 'test results: ', np.array_equal(results['serial'][1][0], results['mp'][1][0])
    print 'test results: ', np.array_equal(results['serial'][1][0], results['mp_map'][1][0])
    print 'benchmark_results: ', benchmark_results
    print 'Perfs: '
    ratio_mp = benchmark_results[0]/benchmark_results[1]
    ratio_mp_map = benchmark_results[0]/benchmark_results[2]
    print '- ratio par rapport au serial: x%.2f x%.2f' % (
        ratio_mp,
        ratio_mp_map
    )
    print '- %% de rendement par rapport au nombre de cpu: %.2f%% %.2f%%' % (
        (ratio_mp/nb_cpu)*100,
        (ratio_mp_map/nb_cpu)*100
    )

    total_points_computed = len(np_array_troncons_pcs) * nbSegments
    print 'speed for serial method: %d point/s' % (total_points_computed/benchmark_results[0])
    print 'speed for mp method: %d points/s' % (total_points_computed/benchmark_results[1])
    print 'speed for mp_map method: %d points/s' % (total_points_computed/benchmark_results[2])

    if b_plot_curves:
        import matplotlib.pyplot as plt
        import random
        random.seed(123)
        indice_curve = int(random.random()*(len(results['mp'])-1))
        print 'indice curve: ', indice_curve
        bezier_curves = [
            results['mp'][indice_curve][0],
            results['mp_map'][indice_curve][0],
            results['serial'][indice_curve][0]
        ]
        plt.plot(
            bezier_curves[0][:, 0], bezier_curves[0][:, 1],
            'bx',
            bezier_curves[0][:, 0], bezier_curves[0][:, 1],
            'bo',
            bezier_curves[1][:, 0], bezier_curves[1][:, 1],
            'gx',
            bezier_curves[1][:, 0], bezier_curves[1][:, 1],
            'go',
            bezier_curves[2][:, 0], bezier_curves[2][:, 1],
            'rx',
            bezier_curves[2][:, 0], bezier_curves[2][:, 1],
            'ro'
        )
        plt.show()

def benchmark_bernstein(n=32, nb_times=10000):
    """

    :param n:
    :param nb_times:
    :return:
    """
    t = timeit.Timer("bc.bernstein_poly_01(%d, 0.5)" % n, "import script_generate_bezier_curve as bc")
    perf_0 = t.timeit(nb_times)
    t = timeit.Timer("[bc.Bernstein(%d, i, 0.5) for i in range(0, %d)]" % (n, n+1), "import script_generate_bezier_curve as bc")
    perf_1 = t.timeit(nb_times)

    # print 'ratio perf: %.2f' % (perf_0/perf_1)
    return perf_0/perf_1

import platform

def print_sysinfo():
    print('\n')
    print('Python version  :', platform.python_version())
    print('compiler        :', platform.python_compiler())
    print('\n')
    print('system     :', platform.system())
    print('release    :', platform.release())
    print('machine    :', platform.machine())
    print('processor  :', platform.processor())
    #url: https://docs.python.org/3/library/multiprocessing.html
    print('CPU count  :', mp.cpu_count())
    print('interpreter:', platform.architecture()[0])
    print('\n\n')

from multiprocessing import cpu_count
default_nprocs = cpu_count()
def distribute(nitems, nprocs=None):
    if nprocs is None:
        nprocs = default_nprocs
    nitems_per_proc = (nitems+nprocs-1)/nprocs
    return [(i, min(nitems, i+nitems_per_proc))
            for i in range(0, nitems, nitems_per_proc)]

# >>> import numpy as np
# >>> import script_generate_bezier_curve as bc
# >>> bc.create_bezier_curve(np.array([[0,2],[1,2],[2,1],[2,0]]))
# (array([[ 1.        ,  2.        ],
#        [ 1.06555556,  1.99888889],
#        [ 1.12888889,  1.99555556],
#        [ 1.19      ,  1.99      ],
#        [ 1.24888889,  1.98222222],
#        [ 1.30555556,  1.97222222],
#        [ 1.36      ,  1.96      ],
#        [ 1.41222222,  1.94555556],
#        [ 1.46222222,  1.92888889],
#        [ 1.51      ,  1.91      ],
#        [ 1.55555556,  1.88888889],
#        [ 1.59888889,  1.86555556],
#        [ 1.64      ,  1.84      ],
#        [ 1.67888889,  1.81222222],
#        [ 1.71555556,  1.78222222],
#        [ 1.75      ,  1.75      ],
#        [ 1.78222222,  1.71555556],
#        [ 1.81222222,  1.67888889],
#        [ 1.84      ,  1.64      ],
#        [ 1.86555556,  1.59888889],
#        [ 1.88888889,  1.55555556],
#        [ 1.91      ,  1.51      ],
#        [ 1.92888889,  1.46222222],
#        [ 1.94555556,  1.41222222],
#        [ 1.96      ,  1.36      ],
#        [ 1.97222222,  1.30555556],
#        [ 1.98222222,  1.24888889],
#        [ 1.99      ,  1.19      ],
#        [ 1.99555556,  1.12888889],
#        [ 1.99888889,  1.06555556],
#        [ 2.        ,  1.        ]]), (2, 2))
#

# >>> bezier.create_bezier_curve_with_list_PC(np.array([[0,2],[1,2],[2,1],[2,0]]))
# (array([[ 1.        ,  2.        ],
#        [ 1.06347555,  1.99895942],
#        [ 1.12486993,  1.99583767],
#        [ 1.18418314,  1.99063476],
#        [ 1.24141519,  1.98335068],
#        [ 1.29656608,  1.97398543],
#        [ 1.3496358 ,  1.96253902],
#        [ 1.40062435,  1.94901145],
#        [ 1.44953174,  1.93340271],
#        [ 1.49635796,  1.9157128 ],
#        [ 1.54110302,  1.89594173],
#        [ 1.58376691,  1.87408949],
#        [ 1.62434964,  1.85015609],
#        [ 1.6628512 ,  1.82414152],
#        [ 1.69927159,  1.79604579],
#        [ 1.73361082,  1.76586889],
#        [ 1.76586889,  1.73361082],
#        [ 1.79604579,  1.69927159],
#        [ 1.82414152,  1.6628512 ],
#        [ 1.85015609,  1.62434964],
#        [ 1.87408949,  1.58376691],
#        [ 1.89594173,  1.54110302],
#        [ 1.9157128 ,  1.49635796],
#        [ 1.93340271,  1.44953174],
#        [ 1.94901145,  1.40062435],
#        [ 1.96253902,  1.3496358 ],
#        [ 1.97398543,  1.29656608],
#        [ 1.98335068,  1.24141519],
#        [ 1.99063476,  1.18418314],
#        [ 1.99583767,  1.12486993],
#        [ 1.99895942,  1.06347555],
#        [ 2.        ,  1.        ]]), array([[2, 2]]))

# np_array_points =  np.array([[ 0. ,  2. ],
#                                  [ 1. ,  2. ],
#                                  [ 1.5,  2. ],
#                                  [ 2. ,  1.5],
#                                  [ 2. ,  1. ],
#                                  [ 2. ,  0. ]])
# >>> bezier.create_bezier_curve_with_list_PC(np.array([[0,2], [1,2], [1.5,2], [2,1.5], [2,1], [2,0]]))
#  (array([[ 1.        ,  2.        ],
#        [ 1.04837031,  1.99845591],
#        [ 1.09663992,  1.99389077],
#        [ 1.14470813,  1.98640529],
#        [ 1.19247424,  1.97610016],
#        [ 1.23983753,  1.9630761 ],
#        [ 1.28669732,  1.94743379],
#        [ 1.33295291,  1.92927394],
#        [ 1.37850357,  1.90869726],
#        [ 1.42324863,  1.88580444],
#        [ 1.46708738,  1.86069618],
#        [ 1.5099191 ,  1.8334732 ],
#        [ 1.55164311,  1.80423618],
#        [ 1.59215871,  1.77308583],
#        [ 1.63136518,  1.74012286],
#        [ 1.66916183,  1.70544795],
#        [ 1.70544795,  1.66916183],
#        [ 1.74012286,  1.63136518],
#        [ 1.77308583,  1.59215871],
#        [ 1.80423618,  1.55164311],
#        [ 1.8334732 ,  1.5099191 ],
#        [ 1.86069618,  1.46708738],
#        [ 1.88580444,  1.42324863],
#        [ 1.90869726,  1.37850357],
#        [ 1.92927394,  1.33295291],
#        [ 1.94743379,  1.28669732],
#        [ 1.9630761 ,  1.23983753],
#        [ 1.97610016,  1.19247424],
#        [ 1.98640529,  1.14470813],
#        [ 1.99389077,  1.09663992],
#        [ 1.99845591,  1.04837031],
#        [ 2.        ,  1.        ]]), array([[ 1.5,  2. ],
#        [ 2. ,  1.5]]))

# # dessiner les points de l'interpolation spline
# # url: http://matplotlib.org/users/pyplot_tutorial.html
# import script_generate_bezier_curve as bc
# import matplotlib.pyplot as plt
# bezier_curves = [
#     bc.create_bezier_curve_with_list_PC(np.array([[0, 2], [1, 2], [2, 1], [2, 0]])),
#     bc.create_bezier_curve_with_list_PC(np.array([[0, 2], [1, 2], [1.5, 2], [2, 1.5], [2, 1], [2, 0]]))
# ]
# plt.plot(
#     bezier_curves[0][0][:, 0], bezier_curves[0][0][:, 1],
#     'bx',
#     bezier_curves[0][1][:, 0], bezier_curves[0][1][:, 1],
#     'bo',
#     bezier_curves[1][0][:, 0], bezier_curves[1][0][:, 1],
#     'gx',
#     bezier_curves[1][1][:, 0], bezier_curves[1][1][:, 1],
#     'go'
# )
# plt.show()

# import script_generate_bezier_curve as bc
# >>> bc.benchmark(2**12, 2**7, 8, True)

# >>> t = timeit.Timer("bc.bernstein_poly_01(3, 0.5)", "import script_generate_bezier_curve as bc")
# >>> t.timeit()
# 1.8391380310058594
# >>> t = timeit.Timer("[bc.Bernstein(3, i, 0.5) for i in range(0, 3+1)]", "import script_generate_bezier_curve as bc")
# >>> t.timeit()
# 4.111564874649048
