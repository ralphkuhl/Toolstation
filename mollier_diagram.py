import matplotlib.pyplot as plt
import numpy as np
from scipy.constants import R, zero_Celsius

"""
Mollier Diagram Generator en Luchtbehandelingsprocessen

Dit script genereert een Mollier (h-w) diagram en stelt gebruikers in staat
om diverse luchtbehandelingsprocessen te visualiseren.

Kernfunctionaliteit:
- Psychrometrische berekeningen: verzadigingsdruk, vochtgehalte, enthalpie, dauwpunt.
- Generatie van een Mollier-diagram met lijnen voor constante relatieve vochtigheid (RH)
  en constante temperatuur (isothermen).
- Visualisatie van standaard luchtbehandelingsprocessen:
    - Verstandige verwarming
    - Verstandige koeling
    - Koeling en ontvochtiging
    - Verwarming en bevochtiging (met stoom)
    - Adiabatische koeling (verdampingskoeling)
- Plotten van een voorbeeld welzijnszone.

Gebruikte bibliotheken:
- Matplotlib: Voor het genereren van de plots.
- NumPy: Voor numerieke operaties, met name array manipulaties.
- SciPy: Voor fysische constanten.

Formules en constanten zijn gebaseerd op standaard HVAC-literatuur en
psychrometrische principes. Waar mogelijk zijn bronnen of gebruikte benaderingen
in commentaar aangegeven.
"""

# Psychrometrische constanten
CP_AIR = 1006  # J/kg.K (specifieke warmte van droge lucht bij constante druk)
CP_WATER_VAPOR = 1860  # J/kg.K (specifieke warmte van waterdamp bij constante druk)
H_VAPORIZATION = 2.501e6  # J/kg (latente verdampingswarmte van water bij 0°C)
R_AIR = 287.058  # J/kg.K (specifieke gasconstante voor droge lucht)
R_WATER_VAPOR = 461.526 # J/kg.K (specifieke gasconstante voor waterdamp)
P_ATM = 101325 # Pa (standaard atmosferische druk)

def saturation_pressure(T_celsius):
    """
    Berekent de verzadigingsdampdruk (Pa) van water.
    Gebruikt Tetens' formule, die een goede benadering geeft voor typische HVAC temperaturen.
    Referentie: Buck (1981), Alduchov and Eskridge (1996) voor variaties.

    Args:
        T_celsius (float): Temperatuur in Celsius.

    Returns:
        float: Verzadigingsdampdruk in Pascal (Pa).
    """
    # T_kelvin = T_celsius + zero_Celsius # Niet direct nodig voor Tetens'

    if T_celsius >= 0:
        # Tetens' formule voor verzadigingsdampdruk boven water
        # Ps(T) = P0 * exp( (a*T) / (b+T) ) waar T in Celsius
        # P0 = 610.78 Pa (of 6.1078 hPa/mbar)
        # a = 17.27, b = 237.3 voor water
        Ps = 610.78 * np.exp((17.27 * T_celsius) / (T_celsius + 237.3))
    else:
        # Tetens' formule voor verzadigingsdampdruk boven ijs
        # a = 21.875, b = 265.5 voor ijs
        Ps = 610.78 * np.exp((21.875 * T_celsius) / (T_celsius + 265.5))
    return Ps


def humidity_ratio_from_rh(T_celsius, RH):
    """
    Berekent het vochtgehalte (kg waterdamp / kg droge lucht) op basis van
    temperatuur en relatieve vochtigheid.

    Args:
        T_celsius (float): Temperatuur in Celsius.
        RH (float): Relatieve vochtigheid (als fractie, bv. 0.5 voor 50%).

    Returns:
        float: Vochtgehalte (w) in kg/kg. Kan np.nan retourneren bij ongeldige input.
    """
    Ps = saturation_pressure(T_celsius)
    if Ps is None or np.isnan(Ps) or Ps < 0: # Controleer op ongeldige Ps
        return np.nan
    Pv = RH * Ps # Werkelijke dampdruk

    # Formule: w = (M_water / M_air) * Pv / (P_atm - Pv)
    # M_water / M_air = R_air / R_water_vapor approx 0.6219
    denominator = P_ATM - Pv
    if abs(denominator) < 1e-9 or denominator < 0: # Voorkom deling door nul of onfysische situatie
        return np.nan # Pv >= P_ATM is onfysisch voor 'vochtige lucht'

    w = (R_AIR / R_WATER_VAPOR) * Pv / denominator
    if w < 0: # Vochtgehalte kan niet negatief zijn
        return 0 # Of np.nan, afhankelijk van gewenste afhandeling
    return w

def enthalpy(T_celsius, w):
    """
    Berekent de specifieke enthalpie (kJ/kg droge lucht) van vochtige lucht.
    De referentietoestand is droge lucht en vloeibaar water bij 0°C.

    Args:
        T_celsius (float): Temperatuur in Celsius.
        w (float): Vochtgehalte (kg waterdamp / kg droge lucht).

    Returns:
        float: Specifieke enthalpie (h) in kJ/kg droge lucht.
    """
    # h = c_pa * T + w * (h_fg_0C + c_pv * T)
    # c_pa = specifieke warmte droge lucht
    # c_pv = specifieke warmte waterdamp
    # h_fg_0C = latente verdampingswarmte water bij 0°C
    h_joules = CP_AIR * T_celsius + w * (H_VAPORIZATION + CP_WATER_VAPOR * T_celsius)
    return h_joules / 1000  # Converteer van J/kg naar kJ/kg

def dew_point_temperature(T_celsius, RH):
    """
    Berekent de dauwpuntstemperatuur (°C) met behulp van de Magnus-formule.
    Dit is een benadering.

    Args:
        T_celsius (float): Drogeboltemperatuur in Celsius.
        RH (float): Relatieve vochtigheid (als fractie, e.g., 0.6 voor 60%).

    Returns:
        float: Dauwpuntstemperatuur in Celsius. Kan np.nan zijn bij ongeldige input.
    """
    Ps = saturation_pressure(T_celsius)
    if Ps is None or np.isnan(Ps) or Ps <= 0: # Ongeldige verzadigingsdruk
        return np.nan
    Pv = RH * Ps # Werkelijke dampdruk
    if Pv <= 0: # Dampdruk moet positief zijn voor logaritme
        return np.nan

    # Magnus-formule (benadering, parameters kunnen variëren)
    # Gebruikte parameters (vaak voor T > 0°C):
    # b = 17.625 (of 17.27, 17.62, etc. afhankelijk van bron en nauwkeurigheidsrange)
    # c = 243.04 °C (of 237.3 °C, etc.)
    # Referentiedruk voor logaritme P0 = 610.94 Pa (verzadigingsdruk bij 0.01°C)

    # Ln(Pv/P0) waar P0 = 610.94 Pa (soms 611.2 Pa gebruikt)
    try:
        # Alternatieve set parameters (meer gebruikelijk in sommige bronnen):
        log_val = np.log(Pv / 610.78) # Basis op P0 = 610.78 Pa, consistent met Tetens' P0
        A = 17.27 # Parameter voor water (boven 0°C)
        B = 237.3 # Parameter voor water (boven 0°C) in °C
        # Voor temperaturen onder 0°C kunnen andere parameters (A_ice, B_ice) gebruikt worden
        # if T_celsius < 0:
        #    A = 21.875
        #    B = 265.5
        T_dp = (B * log_val) / (A - log_val)

    except (ValueError, RuntimeWarning): # Vangt log(negatief getal) of andere math errors
        return np.nan

    # Controleer of noemer (A - log_val) nul is
    if abs(A - log_val) < 1e-9:
        return np.nan # Of een extreme waarde als indicatie

    return T_dp


def create_mollier_diagram(ax, T_min=-10, T_max=50, w_max=0.030):
    """
    Creëert de basisstructuur van het Mollier-diagram op een gegeven Matplotlib Axes.
    Dit omvat lijnen voor constante relatieve vochtigheid en constante temperatuur.

    Args:
        ax (matplotlib.axes.Axes): Het Matplotlib Axes-object waarop getekend wordt.
        T_min (float, optional): Minimumtemperatuur (°C) voor het diagram. Default is -10.
        T_max (float, optional): Maximumtemperatuur (°C) voor het diagram. Default is 50.
        w_max (float, optional): Maximum vochtgehalte (kg/kg) voor het diagram. Default is 0.030.

    Returns:
        matplotlib.axes.Axes: Het Axes-object met het Mollier-diagram.
    """
    temperatures_c = np.linspace(T_min, T_max, 100) # Array van temperaturen voor berekeningen

    # --- Plot lijnen van constante relatieve vochtigheid (RH) ---
    for rh_percent in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        RH = rh_percent / 100.0

        processed_points = [] # Lijst voor (w,h) punten voor deze RH-lijn
        for T in temperatures_c:
            w = humidity_ratio_from_rh(T, RH)
            # Filter ongeldige of buiten-bereik w-waarden
            if np.isnan(w) or w < 0 or w > w_max:
                continue
            h = enthalpy(T, w)
            if np.isnan(h): # Filter ongeldige h-waarden
                continue
            processed_points.append((w, h))

        if not processed_points: # Sla over als er geen valide punten zijn
            continue

        humidity_ratios_plot, enthalpies_kj_plot = zip(*processed_points)

        ax.plot(
            humidity_ratios_plot,
            enthalpies_kj_plot,
            color='gray', # Kleur voor RH-lijnen
            linestyle='-',
            linewidth=0.8,
            label=f'{rh_percent}% RH' if rh_percent == 50 else None # Label alleen 50% RH voor legenda
        )

        # Heuristiek voor het plaatsen van tekstlabels voor RH-lijnen
        if processed_points:
            # Streef naar een T-waarde voor labelplaatsing die centraal ligt of goed zichtbaar is.
            label_T_target = T_max - 15 if T_max > 20 else (T_min + T_max) / 2
            if rh_percent == 100: label_T_target = T_max - 5 # Voor de verzadigingslijn, plaats label meer naar het einde.
            if rh_percent < 30 : label_T_target = T_max - 2 # Voor lage RH, plaats meer naar het einde.


            actual_label_w, actual_label_h = np.nan, np.nan

            # Zoek het punt op de curve dat het dichtst bij label_T_target ligt
            # Dit vereist het terugkoppelen van 'processed_points' naar de oorspronkelijke 'T' waarden,
            # wat complex kan zijn omdat niet alle T-waarden in processed_points resulteren.
            # Eenvoudigere aanpak: gebruik een punt halverwege de geplotte lijn, of een specifiek berekend punt.

            _w_label = humidity_ratio_from_rh(label_T_target, RH)
            if not (np.isnan(_w_label) or _w_label < 0 or _w_label > w_max * 0.95): # Zorg dat het label niet te ver rechts komt
                _h_label = enthalpy(label_T_target, _w_label)
                if not np.isnan(_h_label):
                    actual_label_w, actual_label_h = _w_label, _h_label

            if np.isnan(actual_label_w): # Fallback: neem een punt 3/4e op de lijn als die lang genoeg is
                 if len(processed_points) > len(temperatures_c) // 3 :
                    actual_label_w, actual_label_h = processed_points[min(len(processed_points)-1, int(len(processed_points)*0.75))]
                 elif processed_points: # Anders, het laatste punt
                    actual_label_w, actual_label_h = processed_points[-1]


            if not (np.isnan(actual_label_w) or np.isnan(actual_label_h)):
                 # Zorg dat het label binnen de plotgrenzen valt en leesbaar is
                 if actual_label_w < w_max * 0.98 and \
                    actual_label_h < enthalpy(T_max, w_max) * 0.98 and \
                    actual_label_h > enthalpy(T_min,0) - 5: # Kleine marge aan de onderkant
                    # Rotatie is afhankelijk van de helling van de lijn op dat punt.
                    # Voor nu een vaste rotatie.
                    rotation_angle = 20 + (rh_percent / 100) * 15 # Meer rotatie voor hogere RH
                    ax.text(actual_label_w, actual_label_h, f'{rh_percent}%',
                            fontsize=6, color='dimgray', ha='left', va='bottom', rotation=rotation_angle)

    # --- Plot lijnen van constante temperatuur (isothermen) ---
    # Isothermen zijn (bijna) rechte lijnen in een h-w diagram.
    # De helling wordt bepaald door (H_VAPORIZATION + CP_WATER_VAPOR * T_iso_celsius).
    for T_iso_celsius in np.arange(round(T_min / 5) * 5, T_max + 1, 5): # Elke 5 graden Celsius, startend op een veelvoud van 5
        # Bepaal het eindpunt van de isotherm: ofwel bij w_max of bij verzadiging.
        w_sat_at_T_iso = humidity_ratio_from_rh(T_iso_celsius, 1.0) # Vochtgehalte bij verzadiging

        current_w_end = w_max # Standaard eindpunt
        if not np.isnan(w_sat_at_T_iso) and w_sat_at_T_iso < w_max and w_sat_at_T_iso > 0: # Moet positief zijn
            current_w_end = w_sat_at_T_iso # Beperk tot verzadiging als dat eerder is

        if np.isnan(current_w_end) or current_w_end <= 0: # Kan gebeuren bij lage T_iso
            current_w_end = w_max # Fallback, of sla over als 0

        ws_iso_line = np.linspace(0, current_w_end, 2) # Twee punten (begin, eind) voor de lijn

        h_points_iso = []
        valid_ws_iso_line = []
        for w_val in ws_iso_line:
            if w_val < 0: continue # Sla negatieve w over (kan door linspace komen als current_w_end ~0 is)
            h_val = enthalpy(T_iso_celsius, w_val)
            if not np.isnan(h_val):
                h_points_iso.append(h_val)
                valid_ws_iso_line.append(w_val)

        if len(valid_ws_iso_line) < 2: # Minimaal twee valide punten nodig
            continue

        ax.plot(valid_ws_iso_line, h_points_iso, color='royalblue', linestyle='--', linewidth=0.7)

        # Plaatsen van tekstlabels voor isothermen
        label_w_iso = valid_ws_iso_line[-1]
        label_h_iso = h_points_iso[-1]

        if not (np.isnan(label_w_iso) or np.isnan(label_h_iso)):
             # Zorg dat label binnen redelijke grenzen valt
             y_upper_bound = enthalpy(T_max, w_max) + 5
             y_lower_bound = enthalpy(T_min, 0) - 5
             if label_h_iso < y_upper_bound and label_h_iso > y_lower_bound and label_w_iso > 0.0005: # Niet te dicht bij y-as
                 ax.text(label_w_iso * 0.95, label_h_iso * 1.01, f'{T_iso_celsius}°C',
                         fontsize=6, color='royalblue', ha='right', va='bottom', rotation=65) # Meer rotatie voor isothermen

    # --- Instellingen voor de plot (assen, titel, grid) ---
    ax.set_xlabel('Vochtgehalte (x) (kg water / kg droge lucht)')
    ax.set_ylabel('Enthalpie (h) (kJ / kg droge lucht)')
    ax.set_title('Mollier Diagram (h-w)')

    # Bepaal grenzen voor de y-as (enthalpie)
    h_min_val = enthalpy(T_min, 0) # Enthalpie bij T_min, w=0
    h_max_val_approx = enthalpy(T_max, w_max) # Geschatte maximale enthalpie

    ax.set_xlim(-0.0005, w_max) # Start net voor 0 voor zichtbaarheid y-as
    ax.set_ylim(h_min_val -5 , h_max_val_approx + 15) # Voeg wat marge toe, vooral boven

    ax.grid(True, linestyle=':', alpha=0.6, linewidth=0.7) # Subtieler grid
    return ax

# --- Luchtbehandelingsprocessen Definities ---

def sensible_heating(T_start_c, RH_start, T_end_c):
    """
    Simuleert een proces van verstandige verwarming.
    Het vochtgehalte blijft constant.

    Args:
        T_start_c (float): Starttemperatuur in Celsius.
        RH_start (float): Start relatieve vochtigheid (fractie).
        T_end_c (float): Eindtemperatuur in Celsius.

    Returns:
        tuple: Twee tuples, elk (w, h), voor start- en eindpunt.
    """
    w_start = humidity_ratio_from_rh(T_start_c, RH_start)
    h_start = enthalpy(T_start_c, w_start)

    w_end = w_start # Vochtgehalte (w) is constant
    h_end = enthalpy(T_end_c, w_end) # Enthalpie verandert met temperatuur

    return (w_start, h_start), (w_end, h_end)

def sensible_cooling(T_start_c, RH_start, T_end_c):
    """
    Simuleert een proces van verstandige koeling.
    Het vochtgehalte blijft constant.

    Args:
        T_start_c (float): Starttemperatuur in Celsius.
        RH_start (float): Start relatieve vochtigheid (fractie).
        T_end_c (float): Eindtemperatuur in Celsius (T_end_c < T_start_c).

    Returns:
        tuple: Twee tuples, elk (w, h), voor start- en eindpunt.
    """
    # Identiek aan sensible_heating, maar T_end_c is lager.
    return sensible_heating(T_start_c, RH_start, T_end_c)

def cooling_dehumidification(T_start_c, RH_start, T_coil_c, RH_coil_assumed=0.95):
    """
    Simuleert koeling en ontvochtiging (bv. over een koelbatterij).
    Lucht wordt gekoeld tot T_coil_c (typisch ADP - Apparaat DauwPunt).
    Aangenomen wordt dat lucht de batterij verlaat bij RH_coil_assumed (bv. 95% of 100%).

    Args:
        T_start_c (float): Starttemperatuur in Celsius.
        RH_start (float): Start relatieve vochtigheid (fractie).
        T_coil_c (float): Temperatuur van de koelbatterij / ADP in Celsius.
        RH_coil_assumed (float, optional): Aangenomen RH na de batterij. Default 0.95.

    Returns:
        tuple: Twee tuples, elk (w, h), voor start- en eindpunt (na batterij).
    """
    w_start = humidity_ratio_from_rh(T_start_c, RH_start)
    h_start = enthalpy(T_start_c, w_start)

    # Eindpunt condities (na de koelbatterij)
    w_end = humidity_ratio_from_rh(T_coil_c, RH_coil_assumed)
    h_end = enthalpy(T_coil_c, w_end)

    return (w_start, h_start), (w_end, h_end)


def heating_humidification_steam(T_start_c, RH_start, T_end_c, w_end):
    """
    Simuleert verwarming en bevochtiging met stoom.
    De eindtemperatuur en eindvochtgehalte worden direct gespecificeerd.

    Args:
        T_start_c (float): Starttemperatuur in Celsius.
        RH_start (float): Start relatieve vochtigheid (fractie).
        T_end_c (float): Gewenste eindtemperatuur in Celsius.
        w_end (float): Gewenst eindvochtgehalte (kg/kg).

    Returns:
        tuple: Twee tuples, elk (w, h), voor start- en eindpunt.
    """
    w_start = humidity_ratio_from_rh(T_start_c, RH_start)
    h_start = enthalpy(T_start_c, w_start)

    # Eindpunt wordt direct bepaald door T_end_c en w_end
    h_end = enthalpy(T_end_c, w_end)

    return (w_start, h_start), (w_end, h_end)

def evaporative_cooling(T_start_c, RH_start, efficiency=0.8):
    """
    Simuleert adiabatische koeling (verdampingskoeling).
    De enthalpie blijft (nagenoeg) constant.

    Args:
        T_start_c (float): Starttemperatuur in Celsius.
        RH_start (float): Start relatieve vochtigheid (fractie).
        efficiency (float, optional): Efficiëntie van de bevochtiger (0 tot 1). Default 0.8.

    Returns:
        tuple: Twee tuples, elk (w, h), voor start- en eindpunt.
    """
    w_start = humidity_ratio_from_rh(T_start_c, RH_start)
    h_start = enthalpy(T_start_c, w_start)

    # Vind de natteboltemperatuur (T_wb) iteratief.
    # T_wb is de temperatuur waarbij lucht verzadigd raakt bij constante enthalpie h_start.
    T_wet_bulb_approx = T_start_c - 5 # Startgok voor iteratie
    for _ in range(20): # Max 20 iteraties
        w_sat_at_T_wb = humidity_ratio_from_rh(T_wet_bulb_approx, 1.0)
        if np.isnan(w_sat_at_T_wb): break
        h_at_T_wb_sat = enthalpy(T_wet_bulb_approx, w_sat_at_T_wb)
        if np.isnan(h_at_T_wb_sat): break # Voorkom problemen met NaN
        if abs(h_at_T_wb_sat - h_start) < 0.1: # Tolerantie voor convergentie
            break
        # Eenvoudige correctiestap
        denominator_deriv = (CP_AIR + (w_sat_at_T_wb if not np.isnan(w_sat_at_T_wb) else 0) * CP_WATER_VAPOR) / 1000
        if abs(denominator_deriv) < 1e-6: break # Voorkom deling door (bijna) nul
        T_wet_bulb_approx -= (h_at_T_wb_sat - h_start) / denominator_deriv


    w_end_theoretical_max = humidity_ratio_from_rh(T_wet_bulb_approx, 1.0) # Maximaal vochtgehalte bij T_wb
    if np.isnan(w_end_theoretical_max) or w_end_theoretical_max < w_start : # Moet wel bevochtigen
        w_end_theoretical_max = w_start # Fallback als T_wb niet goed convergeert

    # Werkelijk eindvochtgehalte op basis van efficiëntie
    w_end = w_start + efficiency * (w_end_theoretical_max - w_start)

    # Eindpunt heeft dezelfde enthalpie als startpunt (h_end = h_start)
    # De eindtemperatuur T_end_c moet gevonden worden zodat enthalpy(T_end_c, w_end) = h_start.
    T_end_c_approx = T_start_c - 10 # Startgok voor eindtemperatuur
    for _ in range(20): # Max 20 iteraties
        h_calc = enthalpy(T_end_c_approx, w_end)
        if np.isnan(h_calc): break
        if abs(h_calc - h_start) < 0.1: # Tolerantie
            break
        denominator_deriv_T = (CP_AIR + w_end * CP_WATER_VAPOR) / 1000
        if abs(denominator_deriv_T) < 1e-6 : break
        T_end_c_approx -= (h_calc - h_start) / denominator_deriv_T


    return (w_start, h_start), (w_end, h_start) # h blijft constant

def plot_process(ax, point_start, point_end, label, color='red'):
    """
    Helper functie om een luchtbehandelingsproces als een lijn op het diagram te plotten.
    Markeert start- (1) en eindpunt (2).

    Args:
        ax (matplotlib.axes.Axes): Het Axes-object waarop getekend wordt.
        point_start (tuple): (w, h) coördinaten van het startpunt.
        point_end (tuple): (w, h) coördinaten van het eindpunt.
        label (str): Label voor de proceslijn in de legenda.
        color (str, optional): Kleur van de proceslijn. Default is 'red'.
    """
    w_coords = [point_start[0], point_end[0]]
    h_coords = [point_start[1], point_end[1]]

    # Controleer of punten valide zijn voordat geplot wordt
    if any(np.isnan(coord) for coord in w_coords + h_coords):
        print(f"Waarschuwing: Ongeldige coördinaten voor proces '{label}'. Plotten overgeslagen.")
        return

    ax.plot(w_coords, h_coords, marker='o', linestyle='-', color=color, label=label, linewidth=2, markersize=5)
    # Label start- (1) en eindpunten (2)
    ax.text(point_start[0], point_start[1]*1.01, "1", color=color, ha='right', va='bottom', fontsize=9)
    ax.text(point_end[0], point_end[1]*1.01, "2", color=color, ha='left', va='bottom', fontsize=9)


# --- Hoofdgedeelte van het script: Demonstratie ---
if __name__ == '__main__':
    fig, ax = plt.subplots(figsize=(14, 10)) # Maak een groter figuur voor duidelijkheid
    # Creëer het basis Mollier diagram met aangepaste temperatuur- en vochtgrenzen
    create_mollier_diagram(ax, T_min=-10, T_max=45, w_max=0.028)

    # --- Definieer en plot voorbeeld luchtbehandelingsprocessen ---

    # 0. Startpunt voor enkele processen (P0)
    T0 = 20  # °C
    RH0 = 0.50  # 50%
    w0 = humidity_ratio_from_rh(T0, RH0)
    h0 = enthalpy(T0, w0)
    ax.plot(w0, h0, 'ko', markersize=7, label=f'Startpunt P0: {T0}°C, {RH0*100:.0f}% RH')
    ax.text(w0*1.01, h0, f'P0 ({T0}°C, {RH0*100:.0f}%)', color='black', va='bottom', ha='left')

    # 1. Voorbeeld: Verstandige Verwarming vanaf P0
    p_start_sh, p_end_sh = sensible_heating(T0, RH0, 30) # Verwarm van 20°C, 50%RH naar 30°C
    plot_process(ax, p_start_sh, p_end_sh, '1. Verstandige Verwarming (P0 -> 30°C)', 'orange')

    # 2. Voorbeeld: Verstandige Koeling vanaf P0
    p_start_sc, p_end_sc = sensible_cooling(T0, RH0, 10) # Koel van 20°C, 50%RH naar 10°C
    plot_process(ax, p_start_sc, p_end_sc, '2. Verstandige Koeling (P0 -> 10°C)', 'deepskyblue')

    # 3. Voorbeeld: Koeling en Ontvochtiging
    # Definieer een ander startpunt (P_CD_start) voor dit proces voor duidelijkheid
    T_start_cd = 30 # °C
    RH_start_cd = 0.60 # 60%
    w_start_cd_val = humidity_ratio_from_rh(T_start_cd, RH_start_cd)
    h_start_cd_val = enthalpy(T_start_cd, w_start_cd_val)
    ax.plot(w_start_cd_val, h_start_cd_val, 's', color='purple', markersize=7, label=f'Start CD: {T_start_cd}°C, {RH_start_cd*100:.0f}% RH')

    p_start_cd, p_end_cd = cooling_dehumidification(T_start_cd, RH_start_cd, T_coil_c=10, RH_coil_assumed=0.95)
    plot_process(ax, p_start_cd, p_end_cd, '3. Koeling & Ontvochtiging (Batterij 10°C, 95%RH)', 'purple')

    # 4. Voorbeeld: Verwarming en Bevochtiging (Stoom)
    # Definieer een ander startpunt (P_HB_start)
    T_start_hb = 15 # °C
    RH_start_hb = 0.30 # 30%
    w_start_hb_val = humidity_ratio_from_rh(T_start_hb, RH_start_hb)
    h_start_hb_val = enthalpy(T_start_hb, w_start_hb_val)
    ax.plot(w_start_hb_val, h_start_hb_val, 'D', color='green', markersize=7, label=f'Start HB: {T_start_hb}°C, {RH_start_hb*100:.0f}% RH')

    T_end_hb = 22 # Gewenste eindtemperatuur
    w_end_hb = 0.009 # Gewenst eindvochtgehalte (kg/kg)
    p_start_hb, p_end_hb = heating_humidification_steam(T_start_hb, RH_start_hb, T_end_hb, w_end_hb)
    plot_process(ax, p_start_hb, p_end_hb, f'4. Verw. & Stoombevocht. (naar {T_end_hb}°C, w={w_end_hb:.4f})', 'green')

    # 5. Voorbeeld: Adiabatische Koeling (Verdampingskoeling)
    # Definieer een warmer, droger startpunt (P_AC_start)
    T_start_ac = 35 # °C
    RH_start_ac = 0.20 # 20%
    w_start_ac_val = humidity_ratio_from_rh(T_start_ac, RH_start_ac)
    h_start_ac_val = enthalpy(T_start_ac, w_start_ac_val)
    ax.plot(w_start_ac_val, h_start_ac_val, 'P', color='darkcyan', markersize=7, label=f'Start AC: {T_start_ac}°C, {RH_start_ac*100:.0f}% RH')

    p_start_ac, p_end_ac = evaporative_cooling(T_start_ac, RH_start_ac, efficiency=0.85)
    plot_process(ax, p_start_ac, p_end_ac, '5. Adiabatische Koeling (85% eff.)', 'darkcyan')


    # --- Plot een voorbeeld welzijnszone ---
    # Definieer grenzen voor comfort (dit is een zeer vereenvoudigd voorbeeld)
    # Typische zomercomfort: Tussen 23-26°C, RH tussen 40-60%
    T_comfort_min, T_comfort_max = 22, 25 # °C
    RH_comfort_min, RH_comfort_max = 0.40, 0.60 # 40% en 60% RH

    w_comfort_pts = [] # Vochtgehaltes van de hoekpunten
    h_comfort_pts = [] # Enthalpieën van de hoekpunten

    # Hoekpunten van de comfortzone polygoon:
    # 1. (T_min, RH_min)
    w_c1 = humidity_ratio_from_rh(T_comfort_min, RH_comfort_min)
    h_c1 = enthalpy(T_comfort_min, w_c1)
    # 2. (T_max, RH_min)
    w_c2 = humidity_ratio_from_rh(T_comfort_max, RH_comfort_min)
    h_c2 = enthalpy(T_comfort_max, w_c2)
    # 3. (T_max, RH_max)
    w_c3 = humidity_ratio_from_rh(T_comfort_max, RH_comfort_max)
    h_c3 = enthalpy(T_comfort_max, w_c3)
    # 4. (T_min, RH_max)
    w_c4 = humidity_ratio_from_rh(T_comfort_min, RH_comfort_max)
    h_c4 = enthalpy(T_comfort_min, w_c4)

    w_comfort_polygon = [w_c1, w_c2, w_c3, w_c4, w_c1] # Sluit de polygoon
    h_comfort_polygon = [h_c1, h_c2, h_c3, h_c4, h_c1]

    # Filter eventuele NaN waarden uit de polygoonpunten
    valid_comfort_indices = [i for i, w_val in enumerate(w_comfort_polygon)
                             if not np.isnan(w_val) and not np.isnan(h_comfort_polygon[i])]

    w_comfort_plot = np.array(w_comfort_polygon)[valid_comfort_indices]
    h_comfort_plot = np.array(h_comfort_polygon)[valid_comfort_indices]

    if len(w_comfort_plot) > 2: # Er moeten minstens 3 punten zijn om een polygoon te vormen
        ax.plot(w_comfort_plot, h_comfort_plot, color='lightcoral', linestyle='--', linewidth=1.5, label='Welzijnszone (voorbeeld)')
        ax.fill(w_comfort_plot, h_comfort_plot, color='lightcoral', alpha=0.2) # Gevulde zone


    # --- Afronding van de plot ---
    ax.legend(fontsize='small', loc='upper left', bbox_to_anchor=(1.02, 1)) # Legenda buiten de plot
    plt.tight_layout(rect=[0, 0, 0.82, 1]) # Maak ruimte voor de legenda aan de rechterkant
    plt.show() # Toon de plot

    # --- Optionele print statements voor debuggen van processen ---
    # (Commentarieer uit voor normale werking)
    # print("\nVoorbeeldpunt P0 Details:")
    # print(f"  T={T0}°C, RH={RH0*100}%")
    # print(f"  Vochtgehalte (w): {w0:.5f} kg/kg")
    # print(f"  Enthalpie (h): {h0:.2f} kJ/kg")
    # T_dp0 = dew_point_temperature(T0, RH0)
    # print(f"  Dauwpunt (T_dp): {T_dp0:.2f} °C")

    # print("\nDetails Proces 1 (Verstandige Verwarming):")
    # print(f"  Start (w,h): ({p_start_sh[0]:.5f}, {p_start_sh[1]:.2f})")
    # print(f"  Eind (w,h): ({p_end_sh[0]:.5f}, {p_end_sh[1]:.2f})")

    # print("\nDetails Proces 3 (Koeling & Ontvochtiging):")
    # print(f"  Start (w,h): ({p_start_cd[0]:.5f}, {p_start_cd[1]:.2f})")
    # print(f"  Eind (w,h): ({p_end_cd[0]:.5f}, {p_end_cd[1]:.2f})")
    # T_end_cd_real = 10 # Dit is T_coil_c
    # RH_end_cd_real = humidity_ratio_to_rh(T_end_cd_real, p_end_cd[0]) # Helper nodig
    # # print(f"  Eindcondities: T={T_end_cd_real}°C, RH={RH_end_cd_real*100:.1f}% (benaderd)")


    # Helper functie om RH terug te rekenen (voor rapportage/debug)
    # def humidity_ratio_to_rh(T_celsius, w):
    #     """Berekent RH op basis van T en w."""
    #     Pv = (w * P_ATM) / ((R_AIR / R_WATER_VAPOR) + w)
    #     Ps = saturation_pressure(T_celsius)
    #     if Ps is None or np.isnan(Ps) or Ps <= 0 : return np.nan
    #     RH = Pv / Ps
    #     return min(max(RH, 0), 1) # Klem RH tussen 0 en 1
