#!/usr/bin/env python
# matador modules
from matador.hull import QueryConvexHull
from matador.scrapers.castep_scrapers import res2dict
# external libraries
import numpy as np
# standard library
import sys
import os
import json
from os.path import realpath
from glob import glob
import unittest

# grab abs path for accessing test data
REAL_PATH = '/'.join(realpath(__file__).split('/')[:-1]) + '/'


class HullTest(unittest.TestCase):
    """ Test Convex hull functionality. """
    def testHullFromFile(self):
        res_list = glob(REAL_PATH + 'data/hull-KPSn-KP/*.res')
        self.assertEqual(len(res_list), 87, 'Could not find test res files, please check installation...')
        cursor = [res2dict(res)[0] for res in res_list]
        hull = QueryConvexHull(cursor=cursor, elements=['K', 'Sn', 'P'], no_plot=True, quiet=True)
        self.assertEqual(len(hull.hull_cursor), 16)

    def testHullFromFileWithExtraneousElements(self):
        res_list = glob(REAL_PATH + 'data/hull-KPSn-KP/*.res')
        cursor = [res2dict(res)[0] for res in res_list]
        hull = QueryConvexHull(cursor=cursor, elements=['K', 'Sn'], no_plot=True, quiet=True)
        self.assertEqual(len(hull.hull_cursor), 5)

    def testBinaryHullDistances(self):
        res_list = glob(REAL_PATH + 'data/hull-KP-KSnP_pub/*.res')
        self.assertEqual(len(res_list), 295, 'Could not find test res files, please check installation...')
        cursor = [res2dict(res)[0] for res in res_list]
        hull = QueryConvexHull(cursor=cursor, elements=['K', 'P'], no_plot=True, quiet=True)

        hull_dist_test = np.loadtxt(REAL_PATH + 'data/test_KP_hull_dist.dat')
        np.testing.assert_array_almost_equal(np.sort(hull_dist_test), np.sort(hull.hull_dist), decimal=3)

    def testTernaryHullDistances(self):
        res_list = glob(REAL_PATH + 'data/hull-KPSn-KP/*.res')
        self.assertEqual(len(res_list), 87, 'Could not find test res files, please check installation...')
        cursor = [res2dict(res)[0] for res in res_list]
        hull = QueryConvexHull(cursor=cursor, elements=['K', 'Sn', 'P'], no_plot=True, quiet=True)
        self.assertEqual(len(hull.hull_cursor), 16)
        self.assertEqual(len(hull.cursor), 87)
        for ind, doc in enumerate(hull.cursor):
            hull.cursor[ind]['filename'] = doc['source'][0].split('/')[-1]

        structures = np.loadtxt(REAL_PATH + 'data/test_KSnP.dat')
        hull_dist_test = np.loadtxt(REAL_PATH + 'data/test_KSnP_hull_dist.dat')
        precomp_hull_dist, energies, comps = hull.get_hull_distances(structures, precompute=True)
        np.testing.assert_array_almost_equal(np.sort(hull_dist_test), np.sort(hull.hull_dist), decimal=3)
        np.testing.assert_array_almost_equal(np.sort(hull.hull_dist), np.sort(precomp_hull_dist), decimal=3)


class VoltageTest(unittest.TestCase):
    """ Test voltage curve functionality. """
    def testBinaryVoltage(self):
        with open(os.devnull, 'w') as sys.stdout:
            match, hull_cursor = [], []
            test_x = np.loadtxt(REAL_PATH + 'data/LiAs_x.dat')
            test_Q = np.loadtxt(REAL_PATH + 'data/LiAs_Q.dat')
            test_V = np.loadtxt(REAL_PATH + 'data/LiAs_V.dat')
            for i in range(5):
                with open(REAL_PATH + 'data/hull_data' + str(i) + '.json') as f:
                    hull_cursor.append(json.load(f))
            for i in range(2):
                with open(REAL_PATH + 'data/mu' + str(i) + '.json') as f:
                    match.append(json.load(f))
            with open(REAL_PATH + 'data/elements.json') as f:
                elements = json.load(f)
            bare_hull = QueryConvexHull.__new__(QueryConvexHull)
            bare_hull.args = {'debug': True, 'quiet': True}
            bare_hull.cursor = list(hull_cursor)
            bare_hull.ternary = False
            bare_hull.elements = list(elements)
            bare_hull.hull_cursor = list(hull_cursor)
            bare_hull.match = list(match)
            bare_hull.voltage_curve(bare_hull.hull_cursor)
        sys.stdout = sys.__stdout__
        self.assertTrue(len(bare_hull.voltages) == 1)
        np.testing.assert_array_equal(bare_hull.voltages[0], test_V, verbose=True)
        np.testing.assert_array_equal(bare_hull.x[0], test_x)
        np.testing.assert_array_equal(bare_hull.Q[0], test_Q)
        for ind in range(len(bare_hull.voltages)):
            assert len(bare_hull.Q[ind]) == len(bare_hull.voltages[ind])
            assert np.isnan(bare_hull.Q[ind][-1])
            assert bare_hull.voltages[ind][-1] == 0

    def testBinaryVoltageAgain(self):
        # test LiP voltage curve from Mayo et al, Chem. Mater. (2015) DOI: 10.1021/acs.chemmater.5b04208
        res_list = glob(REAL_PATH + 'data/hull-LiP-mdm_chem_mater/*.res')
        cursor = [res2dict(res)[0] for res in res_list]
        hull = QueryConvexHull(cursor=cursor, elements=['Li', 'P'], no_plot=True, subcmd='voltage', quiet=True)
        self.assertEqual(len(hull.voltages), len(hull.Q))
        self.assertEqual(len(hull.voltages), len(hull.Q))
        LiP_voltage_curve = np.loadtxt(REAL_PATH + 'data/LiP_voltage.csv', delimiter=',')
        self.assertTrue(len(hull.voltages) == 1)
        np.testing.assert_allclose(hull.voltages[0], LiP_voltage_curve[:, 1], verbose=True, rtol=1e-4)
        np.testing.assert_allclose(hull.Q[0], LiP_voltage_curve[:, 0], verbose=True, rtol=1e-4)

    def testTernaryVoltage(self):
        # test data from LiSnS
        # with open(os.devnull, 'w') as sys.stdout:
        res_list = glob(REAL_PATH + 'data/hull-LiSnS/*.res')
        cursor = [res2dict(res)[0] for res in res_list]
        hull = QueryConvexHull(cursor=cursor, elements=['Li', 'Sn', 'S'], no_plot=True, pathways=True, subcmd='voltage',
                               debug=True, quiet=False)
        pin = np.array([[2, 0, 0, -380.071],
                        [0, 2, 4, -1305.0911],
                        [2, 0, 1, -661.985],
                        [6, 2, 0, -1333.940],
                        [16, 4, 16, -7906.417],
                        [4, 4, 0, -1144.827],
                        [0, 4, 4, -1497.881],
                        [0, 1, 0, -95.532],
                        [0, 0, 48, -13343.805]])
        tot = pin[:, 0] + pin[:, 1] + pin[:, 2]
        points = pin/tot[:, None]

        voltage_data = [np.asarray([1.9415250000000697, 1.9415250000000697, 1.8750000000001705, 1.4878749999999741,
                                    0.63925000000000409, 0.34612500000000068, 0.0]),
                        np.asarray([1.4878749999999741, 1.4878749999999741, 0.63925000000000409, 0.34612500000000068, 0.0])]

        Q_data = [np.array([0, 195, 293, 586, 733, 1026, np.NaN]), np.array([0, 356, 533, 889, np.NaN])]

        points = np.delete(points, 2, axis=1)

        self.assertEqual(len(hull.Q), len(Q_data))
        for i in range(len(hull.voltages)):
            np.testing.assert_array_almost_equal(hull.voltages[i], voltage_data[i], decimal=3)
            np.testing.assert_array_almost_equal(hull.Q[i], Q_data[i], decimal=0)
        for ind in range(len(hull.voltages)):
            assert len(hull.Q[ind]) == len(hull.voltages[ind])
            assert np.isnan(hull.Q[ind][-1])
            assert hull.voltages[ind][-1] == 0

    def testTernaryVoltageWithOneTwoPhaseRegion(self):
        # load old hull then rejig it to go through a ternary phase
        res_list = glob(REAL_PATH + 'data/hull-KPSn-KP/*.res')
        self.assertEqual(len(res_list), 87, 'Could not find test res files, please check installation...')
        cursor = [res2dict(res)[0] for res in res_list]
        cursor = [doc for doc in cursor if (doc['stoichiometry'] != [['P', 3], ['Sn', 4]] and
                                            doc['stoichiometry'] != [['P', 3], ['Sn', 1]] and
                                            doc['stoichiometry'] != [['K', 3], ['P', 7]] and
                                            doc['stoichiometry'] != [['K', 1], ['P', 7]] and
                                            doc['stoichiometry'] != [['K', 2], ['P', 3]] and
                                            doc['stoichiometry'] != [['K', 8], ['P', 4], ['Sn', 1]] and
                                            doc['stoichiometry'] != [['K', 1], ['P', 2], ['Sn', 2]] and
                                            doc['stoichiometry'] != [['K', 1], ['Sn', 1]] and
                                            doc['stoichiometry'] != [['K', 4], ['Sn', 9]] and
                                            doc['stoichiometry'] != [['K', 5], ['P', 4]] and
                                            doc['stoichiometry'] != [['P', 2], ['Sn', 1]])]
        hull = QueryConvexHull(cursor=cursor, elements=['K', 'Sn', 'P'], no_plot=True, pathways=True, subcmd='voltage', quiet=True)
        self.assertEqual(len(hull.voltages), len(hull.Q))
        np.testing.assert_array_almost_equal(np.asarray(hull.voltages), np.asarray([[1.0229, 1.0229, 0.2676, 0.000]]), decimal=3)
        for ind in range(len(hull.voltages)):
            assert len(hull.Q[ind]) == len(hull.voltages[ind])
            assert np.isnan(hull.Q[ind][-1])
            assert hull.voltages[ind][-1] == 0

    def testTernaryVoltageWithTwoTwoPhaseRegions(self):
        # load old hull then rejig it to go through a ternary phase
        res_list = glob(REAL_PATH + 'data/hull-KPSn-KP/*.res')
        self.assertEqual(len(res_list), 87, 'Could not find test res files, please check installation...')
        cursor = [res2dict(res)[0] for res in res_list]
        cursor = [doc for doc in cursor if (doc['stoichiometry'] != [['P', 3], ['Sn', 4]] and
                                            doc['stoichiometry'] != [['P', 3], ['Sn', 1]] and
                                            doc['stoichiometry'] != [['K', 3], ['P', 7]] and
                                            doc['stoichiometry'] != [['K', 1], ['P', 7]] and
                                            doc['stoichiometry'] != [['K', 2], ['P', 3]] and
                                            doc['stoichiometry'] != [['K', 8], ['P', 4], ['Sn', 1]] and
                                            doc['stoichiometry'] != [['K', 1], ['Sn', 1]] and
                                            doc['stoichiometry'] != [['K', 4], ['Sn', 9]] and
                                            doc['stoichiometry'] != [['K', 5], ['P', 4]] and
                                            doc['stoichiometry'] != [['P', 2], ['Sn', 1]])]
        hull = QueryConvexHull(cursor=cursor, elements=['K', 'Sn', 'P'], no_plot=True, pathways=True, subcmd='voltage', quiet=True)
        self.assertEqual(len(hull.voltages), len(hull.Q))
        for ind in range(len(hull.voltages)):
            self.assertTrue(len(hull.voltages[ind])-1, len(hull.Q[ind]) or len(hull.voltages[ind]) == len(hull.Q[ind]))
        np.testing.assert_array_almost_equal(np.asarray(hull.voltages[0]), np.asarray([1.1845, 1.1845, 0.8612, 0.2676, 0.000]), decimal=3)
        self.assertAlmostEqual(hull.Q[ind][-2], 425.7847612)
        for ind in range(len(hull.voltages)):
            assert len(hull.Q[ind]) == len(hull.voltages[ind])
            assert np.isnan(hull.Q[ind][-1])
            assert hull.voltages[ind][-1] == 0

    def testTernaryVoltageOnlyTwoPhaseRegions(self):
        # load old hull then rejig it to go through a ternary phase
        res_list = glob(REAL_PATH + 'data/hull-KPSn-KP/*.res')
        self.assertEqual(len(res_list), 87, 'Could not find test res files, please check installation...')
        cursor = [res2dict(res)[0] for res in res_list]
        cursor = [doc for doc in cursor if (doc['stoichiometry'] == [['P', 1], ['Sn', 1]] or
                                            doc['stoichiometry'] == [['K', 1], ['P', 1], ['Sn', 1]] or
                                            doc['stoichiometry'] == [['P', 1]] or
                                            doc['stoichiometry'] == [['K', 1]] or
                                            doc['stoichiometry'] == [['Sn', 1]])]

        hull = QueryConvexHull(cursor=cursor, elements=['K', 'Sn', 'P'], no_plot=True, pathways=True, subcmd='voltage', quiet=True)
        self.assertEqual(len(hull.voltages), len(hull.Q))
        self.assertEqual(len(hull.voltages), 1)
        for ind in range(len(hull.voltages)):
            assert len(hull.Q[ind]) == len(hull.voltages[ind])
            assert np.isnan(hull.Q[ind][-1])

    def testTernaryVoltageWithSinglePhaseRegion(self):
        # load old hull then rejig it to go through a ternary phase
        res_list = glob(REAL_PATH + 'data/hull-LiSiP/*.res')
        cursor = [res2dict(res)[0] for res in res_list]
        hull = QueryConvexHull(cursor=cursor, elements=['Li', 'Si', 'P'], pathways=True, no_plot=True, subcmd='voltage', quiet=True)
        self.assertEqual(len(hull.voltages), len(hull.Q))
        np.testing.assert_array_almost_equal(np.asarray(hull.voltages[0]),
                                             np.asarray([1.1683, 1.1683, 1.0759, 0.7983,
                                                         0.6447, 0.3726, 0.3394, 0.1995,
                                                         0.1570, 0.1113, 0.1041, 0.0000]),
                                             decimal=3)
        for ind in range(len(hull.voltages)):
            self.assertTrue(len(hull.voltages[ind])-1, len(hull.Q[ind]) or len(hull.voltages[ind]) == len(hull.Q[ind]))
        for ind in range(len(hull.voltages)):
            assert len(hull.Q[ind]) == len(hull.voltages[ind])
            assert np.isnan(hull.Q[ind][-1])
            assert hull.voltages[ind][-1] == 0

    def testAngelasAwkwardTernaryVoltage(self):
        # test data from NaFeP
        res_list = glob(REAL_PATH + 'data/hull-NaFeP-afh41_new_Na+Fe+P/*.res')
        self.assertEqual(len(res_list), 16, 'Could not find test res files, please check installation...')
        cursor = [res2dict(res)[0] for res in res_list]
        hull = QueryConvexHull(cursor=cursor, elements=['Na', 'Fe', 'P'], no_plot=True, quiet=True, subcmd='voltage')
        self.assertEqual(len(hull.voltages[0]), 8)
        self.assertEqual(len(hull.voltages[1]), 5)
        self.assertEqual(len(hull.voltages[2]), 3)


if __name__ == '__main__':
    unittest.main(buffer=True, verbosity=2)