import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import StrMethodFormatter

# TODO: 1% dla banku
# TODO: porównaj do EDO i do inflacji
# TODO: pierwszy rok bez premii jak nie ma 9 rat, art 14.1
# TODO: code formatting
#       autopep8 --in-place --aggressive --aggressive konmiesz.py


def roczny_wskaznik_premii(inflacja: float, wzrost_m2: float | None):
    """
    Oblicza roczny wskaźnik premii mieszkaniowej.

    Zgodnie z art. 14.3 ustawy, uwzględnia większy z obu wskaźników (inflacji i
    wzrostu ceny m2).  Zwracany wskaźnik premii mieszkaniowej jest
    normalizowany tak aby nie był niższy niż 1% i wyższy niż 15% (art. 14.4
    ustawy).

    Args:
        inflacja (float): inflacja obserwowana w danym roku
        wzrost_m2 (float | None): wskaźnik średniego wzrostu cen m2 w danym r.

    Returns:
        _type_: wskaźnik premii mieszkaniowej
    """

    # większy z obu czynników (art. 14.3)
    wskaznik = max(inflacja, wzrost_m2)
    # wskaźnik nie przekracza 1% od dołu i 15% od góry (art. 14.4)
    return min(0.15, max(0.01, wskaznik))


def zalozenia_inflacji_i_wzrostu_m2(inflacja: list, wzrost_m2: list):
    df_inflacja = pd.DataFrame(data={
        'Inflacja': inflacja,
        'Wzrost m2': wzrost_m2
    },
        index=pd.date_range(
        start='2024',
        periods=len(inflacja),
        freq=pd.offsets.YearBegin(),
        name='Rok'
    ).strftime('%Y')
    )
    df_inflacja['Premia'] = df_inflacja.apply(
        lambda row: roczny_wskaznik_premii(
            row["Inflacja"], row["Wzrost m2"] or 0), axis=1)
    return df_inflacja


def formatuj_inflacje(df_inflacja: pd.DataFrame):
    styled = df_inflacja.style.format({
        'Inflacja': '{:,.2%}'.format,
        'Premia': '{:,.2%}'.format,
    })
    return styled


def oblicz_skladnik_naliczeniowy(suma_wplat=float, premia=float):
    return suma_wplat * premia / 12  # Art. 14.2


def symulacja_konta(data_startu, ile_lat, ile_wplat, wysokosc_wplat, premia):
    df_konto = pd.DataFrame(data={
        'Miesiąc': pd.date_range(
            start=data_startu,
            periods=ile_wplat,
            freq=pd.offsets.MonthBegin()
        ),
        'Wpłata': [wysokosc_wplat] * ile_wplat
    },
        index=pd.Index(range(1, ile_wplat + 1), name="Wpłata nr")
    )
    df_konto['Suma Wpłat'] = df_konto['Wpłata'].cumsum()
    df_konto['Rok'] = pd.DatetimeIndex(df_konto['Miesiąc']).year
    df_konto['Składnik Naliczeniowy'] = df_konto.apply(
        lambda row: oblicz_skladnik_naliczeniowy(
            suma_wplat=row['Suma Wpłat'], premia=premia._get_value(
                str(row['Rok']), 'Premia')
        ), axis=1
    )
    df_konto['Premia Sumaryczna'] = df_konto['Składnik Naliczeniowy'].cumsum()
    df_konto['Total z Premią'] = df_konto.apply(
        lambda row: row['Suma Wpłat'] + row['Premia Sumaryczna'], axis=1)
    df_konto = df_konto.reindex(columns=[
        'Miesiąc', 'Rok', 'Wpłata', 'Składnik Naliczeniowy',
        'Suma Wpłat', 'Premia Sumaryczna', 'Total z Premią'])
    df_roczne = df_konto[['Wpłata', 'Składnik Naliczeniowy', 'Rok']].groupby(
        'Rok').sum()
    df_roczne = df_roczne.rename(columns={
        "Składnik Naliczeniowy": "Premia roczna",
        "Wpłata": "Suma Wpłat"
    })
    df_roczne['Wpłata całkowita'] = df_roczne['Suma Wpłat'].cumsum()
    df_roczne['Premia całkowita'] = df_roczne['Premia roczna'].cumsum()

    df_konto_styled = df_konto.style.format({
        'Miesiąc': lambda d: d.strftime('%Y-%m'),
        'Wpłata': '{:,.0f} zł'.format,
        'Suma Wpłat': '{:,.0f} zł'.format,
        'Składnik Naliczeniowy': '{:,.2f} zł'.format,
        'Premia Sumaryczna': '{:,.2f} zł'.format,
        'Total z Premią': '{:,.2f} zł'.format
    })
    df_roczne_styled = df_roczne.style.format({
        'Premia roczna': '{:,.0f} zł'.format,
        'Premia całkowita': '{:,.0f} zł'.format,
        'Suma Wpłat': '{:,.0f} zł'.format,
        'Wpłata całkowita': '{:,.0f} zł'.format,
    })
    return df_konto_styled, df_roczne_styled, df_konto, df_roczne


def rysuj_wykres_lokaty(df_konto):
    df_wykres_wplat = df_konto[['Miesiąc', 'Suma Wpłat',
                                'Premia Sumaryczna']].set_index(['Miesiąc'])
    fig, axs = plt.subplots(figsize=(8, 4))
    df_wykres_wplat.plot.area(ax=axs)
    axs.set_ylabel('Wartość')
    axs.set_xlabel('Data')
    plt.gca().yaxis.set_major_formatter(
        StrMethodFormatter('{x:,.0f} zł'))  # 2 decimal places
    plt.show()