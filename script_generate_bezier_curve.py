__author__ = 'latty'

import numpy as np

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
    :return: tuple(list_points=np_array, PC=[x, y])
        np array de la liste des points representant le segment de bezier
        point de controle utilise pour calculer le segment de bezier
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
    return np_segment_bezier, PC

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

# >>> bc.create_bezier_curve(np.array([[0, 0],[1,0],[1,0],[0,0]]))
