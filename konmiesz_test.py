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

    def test_multicols(self):
        self.assertEqual(multicols('Grupa', ['a', 'b']), [
            ('Grupa', 'a'),
            ('Grupa', 'b'),
        ])

    def test_oblicz_premie_mieszkaniowa_I_rok_krotszy_niz_9mcy(self):
        """
        Test gdy w pierwszym roku konto było prowadzone krócej niż 9 miesięcy.

        Zgodnie z art. 14.1 ustawy, jeśli w pierwszym roku konto było
        prowadzone przez okres krótszy niż 9 miesięcy premia za ten rok nie
        przysługuje.
        """

        ile_wplat = 36
        daty_wplat = pd.date_range(
            start='2023-05-01',
            periods=ile_wplat,
            freq=pd.offsets.MonthBegin()
        )
        index = pd.Index(range(1, ile_wplat + 1), name=WPLATA_NR)
        df_konto = DataFrame(data={
            MIESIAC: daty_wplat,
            WPLATA_TOTAL: range(1000, 1000 * (ile_wplat + 1), 1000)
        },
            index=index
        )
        df_konto[ROK] = pd.DatetimeIndex(df_konto[MIESIAC]).year
        del df_konto[MIESIAC]
        zalozenia = zalozenia_inflacji_i_wzrostu_m2(
            data_startu='2023', inflacja=[pct / 100 for pct in [12] * 4],
            wzrost_m2=None)

        # w 2023 tylko 8 rat, nie ma jeszcze premii
        skladniki_premii = [0.00] * 8
        df = df_konto.tail(-8)  # omiń raty z pierwszego roku

        for _, row in df.iterrows():
            suma = row[WPLATA_TOTAL]
            premia = zalozenia.at[str(row[ROK]), PREMIA]
            skladnik = suma * premia / 12
            skladniki_premii.append(skladnik)

        oczekiwane = DataFrame(data=skladniki_premii, index=index)

        testowane = oblicz_premie_mieszkaniowa(
            df=df_konto, zalozenia=zalozenia)
        pd.testing.assert_frame_equal(testowane, oczekiwane)

    def test_oblicz_premie_mieszkaniowa_I_rok_niekrotszy_niz_9mcy(self):
        """
        Test gdy w pierwszym roku konto było prowadzone co najmniej 9 miesięcy.

        Zgodnie z art. 14.1 ustawy, jeśli w pierwszym roku konto było
        prowadzone przez okres krótszy niż 9 miesięcy premia za ten rok nie
        przysługuje.
        """
        ile_wplat = 36
        daty_wplat = pd.date_range(
            start='2023-04-01',
            periods=ile_wplat,
            freq=pd.offsets.MonthBegin()
        )
        index = pd.Index(range(1, ile_wplat + 1), name=WPLATA_NR)
        df_konto = DataFrame(data={
            MIESIAC: daty_wplat,
            WPLATA_TOTAL: range(1000, 1000 * (ile_wplat + 1), 1000)
        },
            index=index
        )
        df_konto[ROK] = pd.DatetimeIndex(df_konto[MIESIAC]).year
        del df_konto[MIESIAC]
        zalozenia = zalozenia_inflacji_i_wzrostu_m2(
            data_startu='2023', inflacja=[pct / 100 for pct in [12] * 4],
            wzrost_m2=None)

        # w 2023 było 9 rat, liczymy premię od początku
        skladniki_premii = []
        df = df_konto

        for _, row in df.iterrows():
            suma = row[WPLATA_TOTAL]
            premia = zalozenia.at[str(row[ROK]), PREMIA]
            skladnik = suma * premia / 12
            skladniki_premii.append(skladnik)

        oczekiwane = DataFrame(data=skladniki_premii, index=index)

        testowane = oblicz_premie_mieszkaniowa(
            df=df_konto, zalozenia=zalozenia)
        pd.testing.assert_frame_equal(testowane, oczekiwane)

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
            'Odsetki': [Procent(5.0)] * 6 + [Procent(3.0)] * 4
            + [ProcentInflacji(100.0 * 1.0 / 7.0)] * 2
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
            'Odsetki': [Procent(3.0)] * 7 +
            [ProcentInflacji(100.0 * 1.0 / 7.0)] * 5
        }, index=pd.Index(range(1, 13)))
        pd.testing.assert_frame_equal(odsetki_pekao, expected)

    def test_odsetki_bankowe_alior_wczesna_lokata(self):
        daty = pd.date_range(
            start='2023-10-01',
            periods=7,
            freq=pd.offsets.MonthBegin()
        )
        odsetki_alior = odsetki_bankowe_alior(daty)
        # ponieważ lokata założona do 2023-12-31, to oprocentowanie:
        # - do końca 2023 (3 raty) po 5%
        # - a potem 1/6 inflacji (ostatnie 4 raty)
        expected = pd.DataFrame(data={
            'Odsetki': [Procent(5.0)] * 3 +
            [ProcentInflacji(100 * 1.0 / 6.0)] * 4
        }, index=pd.Index(range(1, 8)))
        pd.testing.assert_frame_equal(odsetki_alior, expected)

    def test_odsetki_bankowe_alior_pozna_lokata(self):
        daty = pd.date_range(
            start='2024-01-01',
            periods=5,
            freq=pd.offsets.MonthBegin()
        )
        odsetki_alior = odsetki_bankowe_alior(daty)
        # ponieważ lokata założona po 2023-12-31, to oprocentowanie:
        # - wszystkie 5 rat 1/6 inflacji
        expected = pd.DataFrame(data={
            'Odsetki': [ProcentInflacji(100 * 1.0 / 6.0)] * 5
        }, index=pd.Index(range(1, 6)))
        pd.testing.assert_frame_equal(odsetki_alior, expected)

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
            data_startu='2024', inflacja=[
                pct / 100 for pct in [9.6] * 3], wzrost_m2=None)
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
        oczekiwane.columns = pd.MultiIndex.from_tuples([
            KOL_WPLATA_TOTAL, KOL_PREMIA_TOTAL])

        testowane = df_roczne[[KOL_WPLATA_TOTAL, KOL_PREMIA_TOTAL]]
        pd.testing.assert_frame_equal(testowane, oczekiwane)

    # def test_notebooka(self):
    #     wyswietl_symulacje(
    #         data_startu='2024-01',
    #         ile_wplat=3 * 12,
    #         wysokosc_wplat=1000,
    #         zalozenia=zalozenia_inflacji_i_wzrostu_m2(data_startu='2024',
    #             inflacja=[pct / 100 for pct in [9.6] * 3], wzrost_m2=None
    #         ),
    #         lokata=PEKAO)
