# TODO: porównaj do EDO i do inflacji
# TODO: code formatting
#       fswatch *py |\
#       xargs -n 1 -I {} autopep8 --in-place --aggressive --aggressiv {}

from typing import Callable, NamedTuple, Tuple

import matplotlib.pyplot as plt
import numpy as np
import numpy_financial as npf
import pandas as pd
from IPython.core.display import HTML
from IPython.display import display
from matplotlib.ticker import StrMethodFormatter
from pandas import DataFrame
from pandas.io.formats.style import Styler

WZROST_M2 = 'Wzrost<br/>m2'
INFLACJA = 'Inflacja'
ROK = 'Rok'
PREMIA = 'Premia'
MIESIAC = 'Miesiąc'
WPLATA = 'Wpłata'
WPLATA_NR = "Wpłata<br/>nr"
WPLATA_TOTAL = 'Suma<br/>Wpłat'
ODSETKI_BANKU_PCT = 'Odsetki<br/>banku<br/>[%]'
ODSETKI_BANKU_ABS = 'Odsetki<br/>banku'
ODSETKI_BANKU_TOTAL = 'Suma<br/>odsetek<br/>banku'
WPLATY_Z_ODSETKAMI = "Wpłaty<br/>z<br/>odsetkami"
PREMIA_SKLADNIK_NALICZ = 'Składnik<br/>Naliczeniowy'
PREMIA_TOTAL = 'Premia<br/>Sumaryczna'
PREMIA_BEZ_PROWIZJI = 'Premia<br/>mieszk.<br/>z odliczoną<br/>prowizją banku'
TOTAL_Z_PREMIA = 'Total z<br/>premią<br/>mieszkaniową'
TOTAL_Z_ODSETKAMI_I_PREMIA_BEZ_PROWIZJI = 'Total z odsetkami i<br/>premią mieszk.<br/>z odliczoną<br/>prowizją banku'
GR_KOL_WPLATY = 'Wpłaty'
GR_KOL_ODSETKI = 'Odsetki banku'
GR_KOL_PREMIA = 'Premia Mieszkaniowa'
GR_KOL_TOTALS = 'Totals'
KOL_MIESIAC = (GR_KOL_WPLATY, MIESIAC)
KOL_WPLATA = (GR_KOL_WPLATY, WPLATA)
KOL_WPLATA_TOTAL = (GR_KOL_WPLATY, WPLATA_TOTAL)
KOL_ODSETKI_BANKU_PCT = (GR_KOL_ODSETKI, ODSETKI_BANKU_PCT)
KOL_ODSETKI_BANKU_ABS = (GR_KOL_ODSETKI, ODSETKI_BANKU_ABS)
KOL_ODSETKI_BANKU_TOTAL = (GR_KOL_ODSETKI, ODSETKI_BANKU_TOTAL)
KOL_PREMIA_SKLADNIK_NALICZ = (GR_KOL_PREMIA, PREMIA_SKLADNIK_NALICZ)
KOL_PREMIA_TOTAL = (GR_KOL_PREMIA, PREMIA_TOTAL)
KOL_PREMIA_BEZ_PROWIZJI = (GR_KOL_PREMIA, PREMIA_BEZ_PROWIZJI)
KOL_TOTAL_Z_PREMIA = (GR_KOL_TOTALS, TOTAL_Z_PREMIA)
KOL_TOTAL_TOTAL = (GR_KOL_TOTALS, TOTAL_Z_ODSETKAMI_I_PREMIA_BEZ_PROWIZJI)


class Procent:
    def __init__(self, pct: float) -> None:
        self.pct = pct / 100.0

    def efektywny_procent(self, inflacja: float) -> float:
        return self.pct

    def __str__(self) -> str:
        return f"{self.pct:,.2%}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Procent):
            return NotImplemented
        return self.pct == other.pct


class ProcentInflacji(Procent):
    def efektywny_procent(self, inflacja: float) -> float:
        return self.pct * inflacja

    def __str__(self) -> str:
        return f"{self.pct:,.2%} inflacji"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProcentInflacji):
            return NotImplemented
        return self.pct == other.pct


class Bank(NamedTuple):
    name: str
    oprocentowanie_lokaty: Callable[[pd.DatetimeIndex], DataFrame]


def roczny_wskaznik_premii(inflacja: float, wzrost_m2: float | None) -> float:
    """
    Oblicza roczny wskaźnik premii mieszkaniowej.

    Zgodnie z art. 14.3 ustawy, uwzględnia większy z obu wskaźników (inflacji i
    wzrostu ceny m2).  Zwracany wskaźnik premii mieszkaniowej jest
    normalizowany tak, aby nie był niższy niż 1% i wyższy niż 15% (art. 14.4
    ustawy).

    Args:
        inflacja (float): inflacja obserwowana w danym roku
        wzrost_m2 (float | None): wskaźnik średniego wzrostu cen m2 w danym r.

    Returns:
        _type_: wskaźnik premii mieszkaniowej
    """

    # Większy z obu czynników (art. 14.3 ustawy)
    wskaznik = max(inflacja, wzrost_m2)
    # Wskaźnik nie przekracza 1% od dołu i 15% od góry (art. 14.4 ustawy)
    return min(0.15, max(0.01, wskaznik))


def zalozenia_inflacji_i_wzrostu_m2(
        data_startu: str,
        inflacja: list,
        wzrost_m2: list) -> DataFrame:
    df_inflacja = DataFrame(data={
        INFLACJA: inflacja,
        WZROST_M2: wzrost_m2
    },
        index=pd.date_range(
        start=data_startu,
        periods=len(inflacja),
        freq=pd.offsets.YearBegin(),
        name=ROK
    ).to_period('Y')
    )
    df_inflacja[PREMIA] = df_inflacja.apply(
        lambda row: roczny_wskaznik_premii(
            row[INFLACJA], row[WZROST_M2] or 0), axis=1)
    return df_inflacja


def formatuj_zalozenia(df_inflacja: DataFrame) -> Styler:
    styled = df_inflacja.style.format({
        INFLACJA: '{:,.2%}'.format,
        PREMIA: '{:,.2%}'.format,
    })
    return styled


def html2txt(legend: str) -> str:
    return legend.replace("<br/>", " ")


def oblicz_skladnik_naliczeniowy(suma_wplat: float, premia: float) -> float:
    return suma_wplat * premia / 12  # Art. 14.2 ustawy


def oblicz_premie_bez_prowizji_banku(premia_total: float) -> float:
    return premia_total * 0.99  # bank pobiera 1% prowizji, Art. 16.7.7 ustawy


def multicols(grupa_kolumn: str, kolumny: list[str]) -> list[Tuple[str, str]]:
    return [(grupa_kolumn, kolumna) for kolumna in kolumny]


def oblicz_premie_mieszkaniowa(df: DataFrame,
                               zalozenia: DataFrame) -> DataFrame:
    """
    Oblicza należną premię mieszkaniową dla poszczególnych wpłat.

    Args:
        df (DataFrame): data frame z 2 kolumnami:
             WPLATA_TOTAL: suma bieżąca po kolejnych wpłatach
             ROK:          rok kalendarzowy tej wpłaty
        zalozenia (DataFrame): założenia premii mieszkaniowej na dany rok

    Returns:
        DataFrame: składniki naliczeniowe premii mieszkaniowej dla kolejnych
        wpłat.
    """
    pierwszy_rok = df[ROK].min()
    ile_rat_pierwszego_roku = np.count_nonzero(df[ROK] == pierwszy_rok)
    omin_pierwszy_rok = ile_rat_pierwszego_roku < 9
    df_premia = df.apply(
        lambda row: 0 if omin_pierwszy_rok and row[ROK] == pierwszy_rok else
        oblicz_skladnik_naliczeniowy(
            suma_wplat=row[WPLATA_TOTAL],
            premia=zalozenia.at[str(row[ROK]), PREMIA]), axis=1
    )
    return DataFrame(df_premia)


def aplikuj_style(df: DataFrame) -> Styler:
    styled = df.style.format({
        KOL_MIESIAC: lambda d: d.strftime('%Y-%m'),
        KOL_WPLATA: '{:,.0f} zł'.format,
        KOL_WPLATA_TOTAL: '{:,.0f} zł'.format,
        KOL_ODSETKI_BANKU_PCT: '{:,.2%}'.format,
        KOL_ODSETKI_BANKU_ABS: '{:,.2f} zł'.format,
        KOL_ODSETKI_BANKU_TOTAL: '{:,.2f} zł'.format,
        KOL_PREMIA_SKLADNIK_NALICZ: '{:,.2f} zł'.format,
        KOL_PREMIA_TOTAL: '{:,.2f} zł'.format,
        KOL_PREMIA_BEZ_PROWIZJI: '{:,.2f} zł'.format,
        KOL_TOTAL_Z_PREMIA: '{:,.2f} zł'.format,
        KOL_TOTAL_TOTAL: '{:,.2f} zł'.format,
    }).set_table_styles([
        {'selector': 'th.col_heading', 'props': 'text-align: center;'}
    ], overwrite=False).set_properties(
        subset=[GR_KOL_WPLATY], **{'background-color': 'lightgreen'}
    ).set_properties(
        subset=[GR_KOL_ODSETKI], **{'background-color': 'lightblue'}
    ).set_properties(
        subset=[GR_KOL_PREMIA], **{'background-color': 'lightcyan'}
    ).set_properties(
        subset=[GR_KOL_TOTALS], **{'background-color': 'lightyellow'}
    )
    return styled


def symulacja_konta(data_startu: str,
                    ile_wplat: int,
                    wysokosc_wplat: int,
                    zalozenia: DataFrame,
                    lokata: Bank) -> (Styler,
                                      Styler,
                                      DataFrame,
                                      DataFrame):
    daty_wplat = pd.date_range(
        start=data_startu,
        periods=ile_wplat,
        freq=pd.offsets.MonthBegin()
    )
    df_konto = DataFrame(data={
        MIESIAC: daty_wplat,
        WPLATA: [wysokosc_wplat] * ile_wplat
    },
        index=pd.Index(range(1, ile_wplat + 1), name=WPLATA_NR)
    )
    df_konto[WPLATA_TOTAL] = df_konto[WPLATA].cumsum()
    df_konto[ROK] = pd.DatetimeIndex(df_konto[MIESIAC]).year
    df_konto[PREMIA_SKLADNIK_NALICZ] = oblicz_premie_mieszkaniowa(
        df=df_konto[[WPLATA_TOTAL, ROK]], zalozenia=zalozenia)
    df_konto[PREMIA_TOTAL] = df_konto[PREMIA_SKLADNIK_NALICZ].cumsum()
    df_konto[PREMIA_BEZ_PROWIZJI] = df_konto[PREMIA_TOTAL].apply(
        oblicz_premie_bez_prowizji_banku)
    df_konto[TOTAL_Z_PREMIA] = df_konto.apply(
        lambda row: row[WPLATA_TOTAL] + row[PREMIA_TOTAL], axis=1)
    lokata = lokata.oprocentowanie_lokaty(daty_wplat) if lokata else DataFrame(
        data=[Procent(0)] * ile_wplat, index=pd.Index(range(1, ile_wplat + 1))
    )
    df_konto[ODSETKI_BANKU_PCT] = lokata
    # mapuj odsetki banku z Procent/ProcentInflacji na procent absolutny lub
    # procent względem inflacji, podając inflację założoną dla danego roku
    df_konto[ODSETKI_BANKU_PCT] = df_konto.apply(
        lambda row: row[ODSETKI_BANKU_PCT].efektywny_procent(zalozenia.at[
            str(row[ROK]), INFLACJA]),
        axis=1)
    df_konto[WPLATY_Z_ODSETKAMI] = licz_odsetki_procent_zlozony(
        wplaty=df_konto[WPLATA], odsetki=df_konto[ODSETKI_BANKU_PCT],
        index=df_konto.index
    )
    df_konto[ODSETKI_BANKU_TOTAL] = df_konto.apply(
        lambda row: row[WPLATY_Z_ODSETKAMI] - row[WPLATA_TOTAL], axis=1
    )
    # wylicz miesięczne odsetki banku odejmując od sumarycznych odsetek
    # sumaryczne odsetki dla poprzedniego miesiąca
    df_konto[ODSETKI_BANKU_ABS] = df_konto[ODSETKI_BANKU_TOTAL].sub(
        df_konto[ODSETKI_BANKU_TOTAL].shift(1).fillna(0))

    df_konto[TOTAL_Z_ODSETKAMI_I_PREMIA_BEZ_PROWIZJI] = \
        df_konto[WPLATA_TOTAL] + df_konto[ODSETKI_BANKU_TOTAL] + \
        df_konto[PREMIA_BEZ_PROWIZJI]

    df_konto = df_konto.reindex(
        columns=[
            MIESIAC,
            ROK,
            WPLATA,
            WPLATA_TOTAL,
            ODSETKI_BANKU_PCT,
            ODSETKI_BANKU_ABS,
            ODSETKI_BANKU_TOTAL,
            PREMIA_SKLADNIK_NALICZ,
            PREMIA_TOTAL,
            PREMIA_BEZ_PROWIZJI,
            TOTAL_Z_PREMIA,
            TOTAL_Z_ODSETKAMI_I_PREMIA_BEZ_PROWIZJI])

    df_roczne = df_konto[
        [ROK, WPLATA, ODSETKI_BANKU_ABS, PREMIA_SKLADNIK_NALICZ]
    ].groupby(
        ROK).sum()
    df_roczne[WPLATA_TOTAL] = df_roczne[WPLATA].cumsum()
    df_roczne[ODSETKI_BANKU_TOTAL] = df_roczne[ODSETKI_BANKU_ABS].cumsum()
    df_roczne[PREMIA_TOTAL] = df_roczne[PREMIA_SKLADNIK_NALICZ].cumsum()
    df_roczne[PREMIA_BEZ_PROWIZJI] = df_roczne[PREMIA_TOTAL].apply(
        oblicz_premie_bez_prowizji_banku)
    df_roczne[TOTAL_Z_ODSETKAMI_I_PREMIA_BEZ_PROWIZJI] = \
        df_roczne[WPLATA_TOTAL] + df_roczne[ODSETKI_BANKU_TOTAL] + \
        df_roczne[PREMIA_BEZ_PROWIZJI]
    df_roczne = df_roczne.reindex(
        columns=[
            WPLATA_TOTAL,
            ODSETKI_BANKU_TOTAL,
            PREMIA_TOTAL,
            PREMIA_BEZ_PROWIZJI,
            TOTAL_Z_ODSETKAMI_I_PREMIA_BEZ_PROWIZJI
        ]
    )

    df_konto_cols = \
        multicols(GR_KOL_WPLATY,
                  [MIESIAC,
                   ROK,
                   WPLATA,
                   WPLATA_TOTAL]) + \
        multicols(GR_KOL_ODSETKI,
                  [ODSETKI_BANKU_PCT,
                   ODSETKI_BANKU_ABS,
                   ODSETKI_BANKU_TOTAL]) + \
        multicols(GR_KOL_PREMIA,
                  [PREMIA_SKLADNIK_NALICZ,
                   PREMIA_TOTAL,
                   PREMIA_BEZ_PROWIZJI]) + \
        multicols(GR_KOL_TOTALS,
                  [TOTAL_Z_PREMIA,
                   TOTAL_Z_ODSETKAMI_I_PREMIA_BEZ_PROWIZJI])
    df_konto.columns = pd.MultiIndex.from_tuples(df_konto_cols)

    df_roczne_cols = \
        multicols(GR_KOL_WPLATY, [WPLATA_TOTAL]) + \
        multicols(GR_KOL_ODSETKI, [ODSETKI_BANKU_TOTAL]) + \
        multicols(GR_KOL_PREMIA, [PREMIA_TOTAL, PREMIA_BEZ_PROWIZJI]) + \
        multicols(GR_KOL_TOTALS, [
            TOTAL_Z_ODSETKAMI_I_PREMIA_BEZ_PROWIZJI
        ])

    df_roczne.columns = pd.MultiIndex.from_tuples(df_roczne_cols)

    df_konto_styled = aplikuj_style(df=df_konto)
    df_roczne_styled = aplikuj_style(df=df_roczne)

    return df_konto_styled, df_roczne_styled, df_konto, df_roczne


def rysuj_wykres_lokaty(df_konto):
    # ungroup columns to single level 1st
    df = df_konto.copy()
    df.columns = df.columns.get_level_values(1)
    df_wykres_wplat = df[
        [MIESIAC, WPLATA_TOTAL, ODSETKI_BANKU_TOTAL, PREMIA_BEZ_PROWIZJI]
    ].set_index([MIESIAC])

    col_wplata = html2txt(WPLATA_TOTAL)
    col_odsetki = html2txt(ODSETKI_BANKU_TOTAL)
    col_premia = html2txt(PREMIA_BEZ_PROWIZJI)

    df_wykres_wplat = df_wykres_wplat.rename(columns={
        WPLATA_TOTAL: col_wplata,
        ODSETKI_BANKU_TOTAL: col_odsetki,
        PREMIA_BEZ_PROWIZJI: col_premia,
    })

    fig, axs = plt.subplots(figsize=(8, 4))
    df_wykres_wplat.plot.area(ax=axs)
    axs.set_ylabel('Kwota')
    axs.set_xlabel('Data')
    plt.gca().yaxis.set_major_formatter(
        StrMethodFormatter('{x:,.0f} zł'))  # 0 decimal places
    plt.show()


def odsetki_bankowe_pekao(daty: pd.DatetimeIndex) -> DataFrame:
    """
    Zwraca oprocentowanie lokaty w banku Pekao.

    Stan na 2023-07-29, źródło:
    https://www.pekao.com.pl/klient-indywidualny/oszczedzam-i-inwestuje/konto-mieszkaniowe.html

    - pierwsze 6 miesięcy oszczędzania (dla kont otwartych do 2023-10-31): 5%
    - potem do 2024-07-08: 3%
    - potem 76% oprocentowania standardowego, na dzisiaj 1.52%,
      zakładam 1/7 inflacji (na dzisiaj inflacja 11.5%)

    Args:
        daty (pd.DatetimeIndex): daty poszczególnych wpłat

    Returns:
        DataFrame: jedna kolumna 'Odsetki' typu Procent/ProcentInflacji
    """

    data_3pct = pd.Timestamp(2024, 7, 9)
    pct5 = Procent(5.0)
    pct3 = Procent(3.0)
    pct1_7th_infl = ProcentInflacji(100.0 * 1.0 / 7.0)

    if daty[0] < pd.Timestamp(2023, 11, 1):  # założona przed końcem 2023-10-31
        ile_5pct = 6  # pierwsze 6 miesięcy oprocentowanie 5%
        # kolejne raty 3% do 2024-07-08 (zakładam, że włącznie)
        ile_3pct = np.count_nonzero(daty[6:] < data_3pct)
        # reszta rat 1/7 inflacji
        reszta = np.count_nonzero(daty[6:] > data_3pct)
    else:
        ile_5pct = 0
        # raty 3% do 2024-07-08 (zakładam, że włącznie)
        ile_3pct = np.count_nonzero(daty < data_3pct)
        # reszta rat 1/7 inflacji
        reszta = np.count_nonzero(daty > data_3pct)

    pct = [pct5] * ile_5pct + [pct3] * ile_3pct + [pct1_7th_infl] * reszta
    return DataFrame(data={
        'Odsetki': pct
    }, index=pd.Index(range(1, len(daty) + 1)))


PEKAO = Bank(name="Pekao", oprocentowanie_lokaty=odsetki_bankowe_pekao)


def odsetki_bankowe_alior(daty: pd.DatetimeIndex) -> DataFrame:
    """
    Zwraca oprocentowanie lokaty w banku Alior.

    Stan na 2023-07-29, źródło:
    https://www.aliorbank.pl/klienci-indywidualni/oszczednosci/konto-mieszkaniowe.html

    - 5% w skali roku oprocentowanie promocyjne do 31 grudnia 2023 r.
    - potem 2% (zakładam 1/6 inflacji, na dzisiaj inflacja 11.5%)

    Args:
        daty (pd.DatetimeIndex): daty poszczególnych wpłat

    Returns:
        DataFrame: jedna kolumna 'Odsetki' typu Procent/ProcentInflacji
    """

    data_promocji = pd.Timestamp(2024, 1, 1)
    ile_5pct = np.count_nonzero(daty < data_promocji)
    ile_reszty = len(daty) - ile_5pct
    pct5 = Procent(5)
    pct1_6th_infl = ProcentInflacji(100.0 * 1.0 / 6.0)

    pct = [pct5] * ile_5pct + [pct1_6th_infl] * ile_reszty
    return DataFrame(data={
        'Odsetki': pct
    }, index=pd.Index(range(1, len(daty) + 1)))


ALIOR = Bank(name="Pekao", oprocentowanie_lokaty=odsetki_bankowe_alior)


def licz_odsetki_procent_zlozony(
        wplaty: DataFrame,
        odsetki: DataFrame,
        index: pd.Index) -> DataFrame:
    """
    Oblicza sumaryczne odsetki dla podanych odsetek.

    Args:
        wplaty (DataFrame): wpłaty w poszczególnych miesiącach
        odsetki (DataFrame): odsetki bankowe dla poszczególnych miesięcy
        index (pd.Index): index kolejnych wpłat

    Returns:
        DataFrame: Sumaryczne kwoty lokaty dla podanych wpłat i oprocentowania.
    """
    total = []
    wplaty, odsetki = (list(x.values) for x in (wplaty, odsetki))

    wplata = wplaty.pop(0)
    procent = odsetki.pop(0)
    wartosc_poczatkowa = 0
    powtorzen = 1
    while wplaty:
        if wplata == wplaty[0] and procent == odsetki[0]:
            powtorzen += 1
            wplaty.pop(0)
            odsetki.pop(0)
        else:
            total.extend(npf.fv(
                rate=procent / 12,
                nper=range(powtorzen + 1),
                pmt=-wplata,
                pv=-wartosc_poczatkowa,
                when='begin')[1:])
            wplata = wplaty.pop(0)
            procent = odsetki.pop(0)
            powtorzen = 1
            wartosc_poczatkowa = total[-1]
    total.extend(npf.fv(
        rate=procent / 12,
        nper=range(powtorzen + 1),
        pmt=-wplata,
        pv=-wartosc_poczatkowa,
        when='begin')[1:])
    return DataFrame(data=total, index=index)


def wyswietl_symulacje(data_startu: str,
                       ile_wplat: int,
                       wysokosc_wplat: int,
                       zalozenia: DataFrame,
                       lokata: Bank) -> None:

    df_konto_styled, df_roczne_styled, df_konto, _ = symulacja_konta(
        data_startu=data_startu, ile_wplat=ile_wplat,
        wysokosc_wplat=wysokosc_wplat, zalozenia=zalozenia, lokata=lokata)

    display(HTML(f"""
<h2>Wykres wpłat, odsetek bankowych i naliczonej prowizji mieszkaniowej</h2>
Założenia inflacji i wzrostu ceny m2 patrz niżej.  Odsetki bankowe liczone dla
banku {lokata.name}.
                 """))
    rysuj_wykres_lokaty(df_konto)
    display(HTML(f"""
<h3>Założenia odnośnie inflacji i wzrostu cen m2</h3>
z wyliczoną premią miezkaniową dla tych założeń.
                 """))
    display(formatuj_zalozenia(zalozenia))
    display(HTML(f"""
<h3>Zestawienie roczne wpłat, odsetek banku i premii mieszkaniowej</h3>
                 """))
    display(df_roczne_styled)
    display(HTML(f"""
<h3>Zestawienie miesięczne wpłat, odsetek banku i premii mieszkaniowej</h3>
                 """))
    display(df_konto_styled)
