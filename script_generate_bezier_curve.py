__author__ = 'latty'

import numpy as np
import math

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


def create_bezier_curve_from_list_PC(list_PC, nbSegments=30):
    """

    :param list_PC:
    :param nbSegments:
    :return:
    """
    npts = len(list_PC)
    tstep = 1.0/(nbSegments+1)
    np_points_bezier = [list_PC[0]]
    list_interpoled_points = [
        reduce(lambda x, y: x+y, [Bernstein(npts-1, i, t) * list_PC[i] for i in range(0, npts, 1)])
        for t in np.arange(0.0, 1.0+tstep, tstep)
    ]
    return np.array(list_interpoled_points), list_PC[1:-1]


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
        threshold_acos_angle=0.875,
        nbSegments=30
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
        (create_bezier_curve_from_list_PC, [list_PC, nbSegments]),
        (create_bezier_curve, [np_array_points, threshold_acos_angle, nbSegments])
    ]
    # list_PC.size == 4 <=> list_PC = [P1, P2]
    tuple_func_params = list_func_generate_spline[list_PC.size == 4]
    # on renvoit la liste des points generes par la spline d'interpolation
    # et la liste des points de controles
    return tuple_func_params[0](*tuple_func_params[1])

# TEST
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
