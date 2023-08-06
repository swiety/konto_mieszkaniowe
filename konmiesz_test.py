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

    def test_odsetki_bankowe_pekao_wczesna_lokata(self):
        daty = pd.date_range(
            start='2023-10-01',
            periods=12,
            freq=pd.offsets.MonthBegin()
        )
        odsetki_pekao = odsetki_bankowe_pekao(daty)
        # ponieważ lokata założona przed 2023-10-31, to oprocentowanie:
        # - pierwsze 6 miesięcy 5%
        # - do 2024-07-08 (czyli kolejne 4 miesięce) 3%
        # - a potem 1/7 inflacji (ostatnie 2 raty)
        expected = pd.DataFrame(data={
            'Odsetki': [Procent(0.05)] * 6 + [Procent(0.03)] * 4 + [ProcentInflacji(1.0 / 7.0)] * 2
        }, index=pd.Index(range(1, 13)))
        pd.testing.assert_frame_equal(odsetki_pekao, expected)

    def test_odsetki_bankowe_pekao_pozna_lokata(self):
        daty = pd.date_range(
            start='2024-01-01',
            periods=12,
            freq=pd.offsets.MonthBegin()
        )
        odsetki_pekao = odsetki_bankowe_pekao(daty)
        # ponieważ lokata założona po 2023-10-31, to oprocentowanie:
        # - do 2024-07-08 (czyli pierwsze 7 miesięcy) 3%
        # - a potem 1/7 inflacji (osstatnie 5 rat)
        expected = pd.DataFrame(data={
            'Odsetki': [Procent(0.03)] * 7 + [ProcentInflacji(1.0 / 7.0)] * 5
        }, index=pd.Index(range(1, 13)))
        pd.testing.assert_frame_equal(odsetki_pekao, expected)

    def test_licz_odsetki_procent_zlozony_oproc_stale_wplata_stala(self):
        """Testy dla stałego oprocentowania i wpłaty
        """

        wplaty = DataFrame([1000] * 6)
        odsetki = DataFrame([0.03] * 6)
        index = pd.Index(range(1, 7))

        suma_wplat = 0
        oczekiwane = []
        for wplata, procent in zip(wplaty[0].to_numpy(), odsetki.to_numpy()):
            suma_wplat += wplata
            suma_wplat *= (1 + procent / 12)
            oczekiwane.append(float(suma_wplat))
        oczekiwane = DataFrame(data=oczekiwane, index=index)

        pd.testing.assert_frame_equal(
            licz_odsetki_procent_zlozony(wplaty=wplaty,
                                         odsetki=odsetki,
                                         index=index),
            oczekiwane)

    def test_licz_odsetki_procent_zlozony_oproc_zmienne_wplata_stala(self):
        """
        Testy dla oprocentowania zmiennego i stałej wpłaty
        """

        wplaty = DataFrame([1000] * 6)
        odsetki = DataFrame([0.03] * 3 + [0.02] * 3)
        index = pd.Index(range(1, 7))

        suma_wplat = 0
        oczekiwane = []
        for wplata, procent in zip(wplaty[0].to_numpy(), odsetki.to_numpy()):
            suma_wplat += wplata
            suma_wplat *= (1 + procent / 12)
            oczekiwane.append(float(suma_wplat))
        oczekiwane = DataFrame(data=oczekiwane, index=index)

        pd.testing.assert_frame_equal(
            licz_odsetki_procent_zlozony(wplaty=wplaty,
                                         odsetki=odsetki,
                                         index=index),
            oczekiwane)

    def test_symulatora_przypadek_ze_strony_rzadowej(self):
        """
        Testuje scenariusz ze stron rządowych.

        Konkretnie ze strony https://pierwszemieszkanie.gov.pl/.
        Konkretny scenariusz:
        - 3 lata oszczędzania
        - po 1000zł miesięcznie
        - przy 9.6% inflacji przez wszystkie 3 lata, wskaźnik wzrostu cen m2
          nieistotny

        Zgodnie z infografiką ze tej samej strony rządowej
        https://www.gov.pl/photo/d64c123f-f6b6-4e32-982c-ae85680f408d
        oczekiwana premia mieszkaniowa wynosi:
        - rok 1, 12,000zł wpłacone, premia   624zł
        - rok 2, 24,000zł wpłacone, premia 2,400zł
        - rok 3, 36.000zł wpłacone, premia 5,328zł
        """

        df_inflacja1 = zalozenia_inflacji_i_wzrostu_m2(
            inflacja=[pct / 100 for pct in [9.6] * 3], wzrost_m2=None)
        _, _, df_konto, df_roczne = symulacja_konta(
            data_startu='2024-01', ile_wplat=3 * 12, wysokosc_wplat=1000,
            zalozenia=df_inflacja1, lokata=PEKAO)

        oczekiwane = DataFrame(
            index=pd.RangeIndex(start=2024,
                                stop=2027,
                                name=ROK).astype(np.int32),
            data={
                WPLATA_TOTAL: [12_000, 24_000, 36_000],
                PREMIA_TOTAL: [624.00, 2_400.00, 5_328.00]
            })

        pd.testing.assert_frame_equal(
            df_roczne[[WPLATA_TOTAL, PREMIA_TOTAL]], oczekiwane)

    # def test_notebooka(self):
    #     wyswietl_symulacje(
    #         data_startu='2024-01',
    #         ile_wplat=3 * 12,
    #         wysokosc_wplat=1000,
    #         zalozenia=zalozenia_inflacji_i_wzrostu_m2(
    #             inflacja=[pct / 100 for pct in [9.6] * 3], wzrost_m2=None
    #         ),
    #         lokata=PEKAO)
