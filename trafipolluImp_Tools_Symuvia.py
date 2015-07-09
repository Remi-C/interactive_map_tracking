__author__ = 'atty'

import parser_symuvia_xsd_2_04_pyxb as symuvia_parser
import operator
from shapely.geometry import MultiPoint

import matplotlib.pyplot as plt
from numpy import asarray

def extract_convexhull_from_symuvia_network(
        xml_filename="/home/atty/Prog/reseau_symuvia/reseau_paris6_v11_new.xml"
):
    """

    :param xml_filename:
    :return:

    """
    list_extremites = []
    list_convex_hull = []
    try:
        xml = open(xml_filename).read()
        symu_ROOT = symuvia_parser.CreateFromDocument(xml)
    except Exception, e:
        print 'extract_convexhull_from_symuvia_network - Exception: ', e
    else:
        # On utilise les extremites amont/aval des TRONCONS
        # pour calculer le convex hull du reseau
        # On pourrait (peut etre) n'utiliser que les EXTREMITES definit dans le XML
        # pour recuperer une enveloppe (convex hull) exploitable ...  A VOIR !
        symu_ROOT_RESEAU_TRONCONS = symu_ROOT.RESEAUX.RESEAU[0].TRONCONS
        list_TRONCONS = symu_ROOT_RESEAU_TRONCONS.TRONCON
        # url: http://stackoverflow.com/a/952943 (Making a flat list out of list of lists in Python)
        list_extremites = reduce(
            operator.add,
            [(TRONCON.extremite_amont, TRONCON.extremite_aval) for TRONCON in list_TRONCONS]
        )
        # url: http://toblerity.org/shapely/manual.html
        convex_hull = MultiPoint(list_extremites).convex_hull
        list_convex_hull = list(convex_hull.exterior.coords)
    finally:
        return list_convex_hull, list_extremites


# appel: debub_draw(extract_convexhull_from_symuvia_network())
def debug_draw(
        result_from_ecfsn
):
    """

    :param result_from_ecfsn:
    :return:
    """
    convex_hull = result_from_ecfsn[0]
    points_cloud = result_from_ecfsn[1]

    #url: http://docs.scipy.org/doc/scipy-dev/reference/generated/scipy.spatial.ConvexHull.html
    #url: http://matplotlib.org/users/pyplot_tutorial.html
    np_convex_hull = asarray(convex_hull)
    np_points_cloud = asarray(points_cloud)

    plt.plot(np_convex_hull[:, 0], np_convex_hull[:, 1], '--b', lw=2)
    plt.plot(np_points_cloud[:, 0], np_points_cloud[:, 1], 'ro')

    plt.show()
