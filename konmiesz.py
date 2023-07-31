from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import StrMethodFormatter
from pandas import DataFrame
from pandas.io.formats.style import Styler


WZROST_M2 = 'Wzrost<br/>m2'
INFLACJA = 'Inflacja'
ROK = 'Rok'
PREMIA = 'Premia'
MIESIAC = 'Miesiąc'
WPLATA = 'Wpłata'
WPLATA_NR = "Wpłata nr"
SUMA_WPLAT = 'Suma<br/>Wpłat'
SKLADNIK_NALICZ = 'Składnik<br/>Naliczeniowy'
PREMIA_SUMARYCZNA = 'Premia<br/>Sumaryczna'
TOTAL_Z_PREMIA = 'Total<br/>z<br/>Premią'
PREMIA_ROCZNA = "Premia<br/>roczna"
WPLATA_CALKOWITA = 'Wpłata<br/>całkowita'
PREMIA_CALKOWITA = 'Premia<br/>całkowita'
ODSETKI_BANKU_PCT = 'Odsetki<br/>banku<br/>[%]'

# TODO: 1% dla banku
# TODO: porównaj do EDO i do inflacji
# TODO: pierwszy rok bez premii jak nie ma 9 rat, art 14.1
# TODO: code formatting
#       autopep8 --in-place --aggressive --aggressive *.py


class Procent:
    def __init__(self, pct: float) -> None:
        self.pct = pct

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


def roczny_wskaznik_premii(inflacja: float, wzrost_m2: float | None):
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

    # Większy z obu czynników (art. 14.3)
    wskaznik = max(inflacja, wzrost_m2)
    # Wskaźnik nie przekracza 1% od dołu i 15% od góry (art. 14.4)
    return min(0.15, max(0.01, wskaznik))


def zalozenia_inflacji_i_wzrostu_m2(
        inflacja: list,
        wzrost_m2: list) -> DataFrame:
    df_inflacja = DataFrame(data={
        INFLACJA: inflacja,
        WZROST_M2: wzrost_m2
    },
        index=pd.date_range(
        start='2024',
        periods=len(inflacja),
        freq=pd.offsets.YearBegin(),
        name=ROK
    ).to_period('Y')
    )
    df_inflacja[PREMIA] = df_inflacja.apply(
        lambda row: roczny_wskaznik_premii(
            row[INFLACJA], row[WZROST_M2] or 0), axis=1)
    return df_inflacja


def formatuj_inflacje(df_inflacja: DataFrame):
    styled = df_inflacja.style.format({
        INFLACJA: '{:,.2%}'.format,
        PREMIA: '{:,.2%}'.format,
    })
    return styled


def oblicz_skladnik_naliczeniowy(suma_wplat: float, premia: float):
    return suma_wplat * premia / 12  # Art. 14.2


def symulacja_konta(data_startu: str,
                    ile_wplat: int,
                    wysokosc_wplat: int,
                    zalozenia: DataFrame,
                    lokata: Callable[[pd.DatetimeIndex],
                                     DataFrame] | None = None) -> (Styler,
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
    df_konto[SUMA_WPLAT] = df_konto[WPLATA].cumsum()
    df_konto[ROK] = pd.DatetimeIndex(df_konto[MIESIAC]).year
    df_konto[SKLADNIK_NALICZ] = df_konto.apply(
        lambda row: oblicz_skladnik_naliczeniowy(
            suma_wplat=row[SUMA_WPLAT], premia=zalozenia.at[str(row[ROK]), PREMIA]
        ), axis=1
    )
    df_konto[PREMIA_SUMARYCZNA] = df_konto[SKLADNIK_NALICZ].cumsum()
    df_konto[TOTAL_Z_PREMIA] = df_konto.apply(
        lambda row: row[SUMA_WPLAT] + row[PREMIA_SUMARYCZNA], axis=1)
    lokata = lokata(daty_wplat) if lokata else DataFrame(
        data=[Procent(0)] * ile_wplat, index=pd.Index(range(1, ile_wplat + 1))
    )
    df_konto[ODSETKI_BANKU_PCT] = lokata
    # mapuj odsetki banku z Procent/ProcentInflacji na procent absolutny lub
    # procent względem inflacji, podając inflację założoną dla danego roku
    df_konto[ODSETKI_BANKU_PCT] = df_konto.apply(
        lambda row: row[ODSETKI_BANKU_PCT].efektywny_procent(zalozenia.at[
            str(row[ROK]), INFLACJA]),
        axis=1)
    df_konto = df_konto.reindex(
        columns=[
            MIESIAC,
            ROK,
            WPLATA,
            ODSETKI_BANKU_PCT,
            SKLADNIK_NALICZ,
            SUMA_WPLAT,
            PREMIA_SUMARYCZNA,
            TOTAL_Z_PREMIA])
    df_roczne = df_konto[[WPLATA, SKLADNIK_NALICZ, ROK]].groupby(
        ROK).sum()
    df_roczne = df_roczne.rename(columns={
        SKLADNIK_NALICZ: PREMIA_ROCZNA,
        WPLATA: SUMA_WPLAT
    })
    df_roczne[WPLATA_CALKOWITA] = df_roczne[SUMA_WPLAT].cumsum()
    df_roczne[PREMIA_CALKOWITA] = df_roczne[PREMIA_ROCZNA].cumsum()

    df_konto_styled = df_konto.style.format({
        MIESIAC: lambda d: d.strftime('%Y-%m'),
        WPLATA: '{:,.0f} zł'.format,
        SUMA_WPLAT: '{:,.0f} zł'.format,
        SKLADNIK_NALICZ: '{:,.2f} zł'.format,
        PREMIA_SUMARYCZNA: '{:,.2f} zł'.format,
        TOTAL_Z_PREMIA: '{:,.2f} zł'.format,
        ODSETKI_BANKU_PCT: '{:,.2%}'.format
    })
    df_roczne_styled = df_roczne.style.format({
        PREMIA_ROCZNA: '{:,.0f} zł'.format,
        PREMIA_CALKOWITA: '{:,.0f} zł'.format,
        SUMA_WPLAT: '{:,.0f} zł'.format,
        WPLATA_CALKOWITA: '{:,.0f} zł'.format,
    })
    return df_konto_styled, df_roczne_styled, df_konto, df_roczne


def rysuj_wykres_lokaty(df_konto):
    df_wykres_wplat = df_konto[[MIESIAC, SUMA_WPLAT, PREMIA_SUMARYCZNA]].set_index([
                                                                                   MIESIAC])
    fig, axs = plt.subplots(figsize=(8, 4))
    df_wykres_wplat.plot.area(ax=axs)
    axs.set_ylabel('Wartość')
    axs.set_xlabel('Data')
    plt.gca().yaxis.set_major_formatter(
        StrMethodFormatter('{x:,.0f} zł'))  # 2 decimal places
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
    pct5 = Procent(0.05)
    pct3 = Procent(0.03)
    pct1_7th_infl = ProcentInflacji(1.0 / 7.0)

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
