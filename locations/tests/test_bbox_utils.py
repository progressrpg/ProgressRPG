from django.test import SimpleTestCase

from ..utils import InvalidBBoxError, MAX_BBOX_AREA_SQ_M, parse_bbox_param


class ParseBBoxParamTest(SimpleTestCase):
    def test_valid_bbox_returns_polygon_with_correct_extent(self):
        polygon = parse_bbox_param("0,0,100,200")
        self.assertEqual(polygon.extent, (0.0, 0.0, 100.0, 200.0))
        self.assertEqual(polygon.srid, 3857)

    def test_missing_bbox_raises(self):
        with self.assertRaises(InvalidBBoxError):
            parse_bbox_param(None)
        with self.assertRaises(InvalidBBoxError):
            parse_bbox_param("")

    def test_wrong_number_of_values_raises(self):
        with self.assertRaises(InvalidBBoxError):
            parse_bbox_param("0,0,100")
        with self.assertRaises(InvalidBBoxError):
            parse_bbox_param("0,0,100,200,300")

    def test_non_numeric_values_raise(self):
        with self.assertRaises(InvalidBBoxError):
            parse_bbox_param("a,b,c,d")

    def test_zero_area_bbox_raises(self):
        with self.assertRaises(InvalidBBoxError):
            parse_bbox_param("0,0,0,200")
        with self.assertRaises(InvalidBBoxError):
            parse_bbox_param("0,0,100,0")

    def test_inverted_min_max_raises(self):
        with self.assertRaises(InvalidBBoxError):
            parse_bbox_param("100,0,0,200")

    def test_oversized_bbox_raises(self):
        side = MAX_BBOX_AREA_SQ_M**0.5 + 1
        with self.assertRaises(InvalidBBoxError):
            parse_bbox_param(f"0,0,{side},{side}")

    def test_bbox_at_max_area_is_allowed(self):
        side = MAX_BBOX_AREA_SQ_M**0.5
        polygon = parse_bbox_param(f"0,0,{side},{side}")
        self.assertIsNotNone(polygon)
