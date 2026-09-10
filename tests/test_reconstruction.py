"""Geometry regressions with synthetic, known traces (not clinical validation)."""
import unittest

import cv2
import numpy as np
from skimage.measure import label

from ecg_reconstruction import repair_trace


def components(image):
    return int(label(image != 0, connectivity=2).max())


class ReconstructionTests(unittest.TestCase):
    def test_straight_gap_recovers_known_trace_without_thickening(self):
        truth = np.zeros((80, 200), np.uint8)
        cv2.line(truth, (10, 40), (190, 40), 255, 5)
        broken = truth.copy()
        broken[:, 85:110] = 0
        result = repair_trace(broken, max_gap=45)
        self.assertEqual(components(result.image), 1)
        self.assertEqual(len(result.bridges), 1)
        self.assertTrue(np.all(result.image[broken != 0] == 255))
        self.assertTrue(np.array_equal(result.image, truth))

    def test_parallel_traces_are_not_joined_together(self):
        broken = np.zeros((100, 180), np.uint8)
        for y in [35, 55]:
            cv2.line(broken, (10, y), (170, y), 255, 3)
        broken[:, 78:97] = 0
        result = repair_trace(broken, max_gap=40)
        self.assertEqual(components(result.image), 2)
        self.assertEqual(len(result.bridges), 2)
        self.assertFalse(np.any(result.added[40:51]))

    def test_steep_gap_and_reflections_are_supported(self):
        broken = np.zeros((160, 100), np.uint8)
        cv2.line(broken, (25, 10), (70, 150), 255, 3)
        broken[65:87, :] = 0
        for image in [broken, broken[::-1].copy(), broken[:, ::-1].copy(), broken.T.copy()]:
            result = repair_trace(image, max_gap=45)
            self.assertEqual(components(result.image), 1)
            self.assertEqual(len(result.bridges), 1)

    def test_existing_component_is_not_shortcut(self):
        image = np.zeros((90, 110), np.uint8)
        cv2.polylines(image, [np.array([[40, 20], [20, 65], [85, 65], [60, 20]])], False, 255, 3)
        result = repair_trace(image, max_gap=50)
        self.assertEqual(result.bridges, [])
        self.assertTrue(np.array_equal(result.image, image))

    def test_bridge_cannot_cross_a_third_trace(self):
        image = np.zeros((100, 160), np.uint8)
        cv2.line(image, (10, 50), (58, 50), 255, 3)
        cv2.line(image, (100, 50), (150, 50), 255, 3)
        cv2.line(image, (80, 0), (80, 99), 255, 3)
        result = repair_trace(image, max_gap=60)
        self.assertEqual(result.bridges, [])
        self.assertTrue(np.array_equal(result.image, image))

    def test_large_gap_stays_open(self):
        image = np.zeros((60, 180), np.uint8)
        cv2.line(image, (10, 30), (50, 30), 255, 3)
        cv2.line(image, (125, 30), (170, 30), 255, 3)
        result = repair_trace(image, max_gap=50)
        self.assertEqual(result.bridges, [])
        self.assertEqual(components(result.image), 2)

    def test_curved_gap_stays_near_known_centerline(self):
        truth = np.zeros((130, 240), np.uint8)
        x = np.arange(10, 230)
        y = np.rint(65 + 25*np.sin(x/38)).astype(int)
        cv2.polylines(truth, [np.column_stack([x, y]).astype(np.int32)], False, 255, 3)
        broken = truth.copy()
        broken[:, 105:127] = 0
        result = repair_trace(broken, max_gap=45)
        self.assertEqual(components(result.image), 1)
        distance = cv2.distanceTransform((truth == 0).astype(np.uint8), cv2.DIST_L2, 5)
        self.assertLessEqual(float(distance[result.added != 0].max()), 3.0)
        self.assertTrue(np.all(result.image[broken != 0] == 255))

    def test_empty_foreground_is_unchanged(self):
        image = np.zeros((60, 90), np.uint8)
        result = repair_trace(image)
        self.assertEqual(result.bridges, [])
        self.assertFalse(np.any(result.image))

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            repair_trace(np.zeros((10, 10, 3)))
        with self.assertRaises(ValueError):
            repair_trace(np.full((10, 10), 127))
        with self.assertRaises(ValueError):
            repair_trace(np.zeros((10, 10)), max_gap=0)


if __name__ == '__main__':
    unittest.main()
