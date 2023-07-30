import unittest
from konmiesz import *


class TestKonMiesz(unittest.TestCase):

    def test_roczny_wskaznik_premii_min(self):
        self.assertEqual(
            roczny_wskaznik_premii(
                inflacja=-0.1,
                wzrost_m2=0.005),
            0.01,
            "Art. 14.4: wskaźnik premii nie może być niższy niż 0.01 (1%)")

    def test_roczny_wskaznik_premii_max(self):
        self.assertEqual(
            roczny_wskaznik_premii(
                inflacja=16,
                wzrost_m2=0.20),
            0.15,
            "Art. 14.4: wskaźnik premii nie może być wyższy niż 0.15 (15%)")

    def test_roczny_wskaznik_premii_wyzsza_inflacja(self):
        self.assertEqual(
            roczny_wskaznik_premii(
                inflacja=0.12,
                wzrost_m2=0.08),
            0.12,
            "Art. 14.3: wskaźnik premii to wyższy czynnik")

    def test_roczny_wskaznik_premii_nizsza_inflacja(self):
        self.assertEqual(
            roczny_wskaznik_premii(
                inflacja=0.07,
                wzrost_m2=0.13),
            0.13,
            "Art. 14.3: wskaźnik premii to wyższy czynnik")
