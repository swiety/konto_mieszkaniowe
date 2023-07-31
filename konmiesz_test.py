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

    def test_odsetki_bankowe_Pekao_wczesna_lokata(self):
        daty = pd.date_range(
            start='2023-10-01',
            periods=12,
            freq=pd.offsets.MonthBegin()
        )
        odsetki_Pekao = odsetki_bankowe_pekao(daty)
        # ponieważ lokata założona przed 2023-10-31, to oprocentowanie:
        # - pierwsze 6 miesięcy 5%
        # - do 2024-07-08 (czyli kolejne 4 miesięce) 3%
        # - a potem 1/7 inflacji (ostatnie 2 raty)
        expected = pd.DataFrame(data={
            'Odsetki %': [Procent(0.05)] * 6 + [Procent(0.03)] * 4 + [ProcentInflacji(1.0 / 7.0)] * 2
        }, index=pd.Index(range(1, 13)))
        pd.testing.assert_frame_equal(odsetki_Pekao, expected)

    def test_odsetki_bankowe_Pekao_pozna_lokata(self):
        daty = pd.date_range(
            start='2024-01-01',
            periods=12,
            freq=pd.offsets.MonthBegin()
        )
        odsetki_Pekao = odsetki_bankowe_pekao(daty)
        # ponieważ lokata założona po 2023-10-31, to oprocentowanie:
        # - do 2024-07-08 (czyli pierwsze 7 miesięcy) 3%
        # - a potem 1/7 inflacji (osstatnie 5 rat)
        expected = pd.DataFrame(data={
            'Odsetki %': [Procent(0.03)] * 7 + [ProcentInflacji(1.0 / 7.0)] * 5
        }, index=pd.Index(range(1, 13)))
        pd.testing.assert_frame_equal(odsetki_Pekao, expected)
