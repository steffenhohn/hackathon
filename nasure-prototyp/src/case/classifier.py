from dataclasses import dataclass
from datetime import timedelta
import pandas as pd
import numpy as np
import uuid
 
# ------------------------------
# 1) Datenstruktur für einen eingehenden Datensatz
# ------------------------------
@dataclass
class IncomingElement:
    Patient_ID: str
    Pathogen_code: str
    Date: pd.Timestamp  # wir nutzen Timestamps für sichere Datumslogik
    ID: str             # die Meldungs-ID (z. B. Labor-/Klinik-/Melde-ID)
 
# ------------------------------
# 2) Hilfsfunktionen
# ------------------------------
 
def ensure_datetime(df: pd.DataFrame, col: str) -> None:
    """
    Konvertiert eine Spalte sicher in datetime (in-place).
    Falls sie schon datetime ist, passiert nichts.
    """
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
 
def new_case_id() -> str:
    """
    Erzeugt eine neue, zufällige case_ID.
    """
    return str(uuid.uuid4())
 
# ------------------------------
# 3) Kernfunktion: Upsert Case + Link Meldungs-ID
# ------------------------------
 
def upsert_case_and_link_id(
    incoming: IncomingElement,
    falldatenprodukt: pd.DataFrame,
    fall_meldung_tabelle: pd.DataFrame,
    case_duration_days: int = 28
):
    """
    Schritte:
    - Wir suchen in 'falldatenprodukt' nach einem vorhandenen Fall (case_ID),
      der dieselbe Patient_ID + Pathogen_code hat und dessen Fall-Datum innerhalb
      von ± case_duration_days um incoming.Date liegt.
    - Wenn gefunden: wir nehmen dessen case_ID.
      Wenn mehrere passen, nehmen wir den mit dem 'nächstliegenden' Datum (kleinste Differenz).
    - Wenn nicht gefunden: wir erzeugen einen neuen Eintrag in 'falldatenprodukt'
      mit neuer case_ID.
    - In beiden Fällen tragen wir (ID, case_ID) in 'Fall_meldung_tabelle' ein
      (aber nur, falls dieses Paar noch nicht existiert).
    - Die Funktion gibt die verwendete case_ID zurück.
    """
 
    # Sicherstellen, dass Datums-Spalten datetime sind
    ensure_datetime(falldatenprodukt, "Date")
 
    # Filter: gleiches Patient_ID + Pathogen_code
    same_patient_pathogen = falldatenprodukt[
        (falldatenprodukt["Patient_ID"] == incoming.Patient_ID) &
        (falldatenprodukt["Pathogen_code"] == incoming.Pathogen_code)
    ].copy()
 
    # Wenn es passende Zeilen gibt, prüfen wir die Datumsnähe (± 28 Tage)
    if not same_patient_pathogen.empty:
        # absolute Differenz in Tagen
        same_patient_pathogen["abs_day_diff"] = (
            (same_patient_pathogen["Date"] - incoming.Date).abs().dt.days
        )
 
        # Fälle innerhalb des Fensters
        within_window = same_patient_pathogen[
            same_patient_pathogen["abs_day_diff"] <= case_duration_days
        ]
 
        if not within_window.empty:
            # Nimm den Fall mit der kleinsten Abweichung
            idx = within_window["abs_day_diff"].idxmin()
            case_id = within_window.loc[idx, "case_ID"]
        else:
            # Kein Fall im Zeitfenster -> Neuer Fall
            case_id = new_case_id()
            new_row = {
                "case_ID": case_id,
                "Patient_ID": incoming.Patient_ID,
                "Pathogen_code": incoming.Pathogen_code,
                "Date": incoming.Date,
                # optional vorab Felder für spätere Ergebnisse:
                # "case_class": np.nan,
                # "lb_date": pd.NaT, "lb_interpretation": np.nan,
                # "kb_date": pd.NaT, "kb_manifestation": np.nan,
            }
            falldatenprodukt.loc[len(falldatenprodukt)] = new_row
    else:
        # Es gibt überhaupt keinen Eintrag mit gleichem Patient/Pathogen -> Neuer Fall
        case_id = new_case_id()
        new_row = {
            "case_ID": case_id,
            "Patient_ID": incoming.Patient_ID,
            "Pathogen_code": incoming.Pathogen_code,
            "Date": incoming.Date,
        }
        falldatenprodukt.loc[len(falldatenprodukt)] = new_row
 
    # Jetzt die (ID, case_ID)-Verknüpfung in Fall_meldung_tabelle ergänzen,
    # aber nur, wenn das Paar noch nicht existiert.
    pair_exists = (
        (fall_meldung_tabelle["ID"] == incoming.ID) &
        (fall_meldung_tabelle["case_ID"] == case_id)
    ).any()
    if not pair_exists:
        fall_meldung_tabelle.loc[len(fall_meldung_tabelle)] = {
            "ID": incoming.ID,
            "case_ID": case_id
        }
 
    return case_id
 
# ------------------------------
# 4) Informationen (Labor/Klinik) je case_ID einsammeln
# ------------------------------
 
def collect_case_evidence(
    case_id: str,
    falldatenprodukt: pd.DataFrame,
    fall_meldung_tabelle: pd.DataFrame,
    labordatenprodukt: pd.DataFrame,
    klinikdatenprodukt: pd.DataFrame
):
    """
    Schritte:
    - Hole alle IDs aus 'Fall_meldung_tabelle', die zu case_id gehören.
    - Prüfe für diese IDs:
        1) labordatenprodukt: falls mehrere Treffer -> nimm den mit dem frühesten Datum.
           Speichere 'lb_date' und 'interpretation'.
        2) klinikdatenprodukt: analog -> nimm den mit dem frühesten Datum.
           Speichere 'kb_date' und 'manifestation'.
    - Schreibe (falls die Spalten existieren oder neu angelegt werden sollen)
      diese Infos in 'falldatenprodukt' für die betreffende case_id.
    - Ermittele 'case_class' nach Regel:
        - interpretation == "Pos"  -> "sicherer Fall"
        - interpretation == "Neg"  -> "kein Fall"
        - sonst (interpretation leer/NaN) und manifestation vorhanden -> "wahrscheinlicher Fall"
    """
 
    # Datums-Felder in datetime konvertieren (sicher)
    ensure_datetime(labordatenprodukt, "date")
    ensure_datetime(klinikdatenprodukt, "date")
 
    # 1) Alle IDs, die zu diesem Fall gehören
    case_id_mask = fall_meldung_tabelle["case_ID"] == case_id
    ids_for_case = fall_meldung_tabelle.loc[case_id_mask, "ID"].unique()
 
    # 2) LABOR: Zeilen für diese IDs filtern
    lab_rows = labordatenprodukt[labordatenprodukt["ID"].isin(ids_for_case)].copy()
 
    lb_date = pd.NaT
    lb_interp = np.nan
    if not lab_rows.empty:
        # frühestes Datum auswählen
        earliest_idx = lab_rows["date"].idxmin()
        lb_date = lab_rows.loc[earliest_idx, "date"]
        lb_interp = lab_rows.loc[earliest_idx, "interpretation"]
 
    # 3) KLINIK: Zeilen für diese IDs filtern
    klinik_rows = klinikdatenprodukt[klinikdatenprodukt["ID"].isin(ids_for_case)].copy()
 
    kb_date = pd.NaT
    kb_manifest = np.nan
    if not klinik_rows.empty:
        earliest_idx = klinik_rows["date"].idxmin()
        kb_date = klinik_rows.loc[earliest_idx, "date"]
        kb_manifest = klinik_rows.loc[earliest_idx, "manifestation"]
 
    # 4) case_class bestimmen
    if pd.notna(lb_interp):
        if str(lb_interp).strip().lower() == "pos":
            case_class = "sicherer Fall"
        elif str(lb_interp).strip().lower() == "neg":
            case_class = "kein Fall"
        else:
            # eine andere Labor-Kategorie – hier keine Einstufung vorgegeben
            case_class = np.nan
    else:
        # Keine Interpretation -> Klinik prüfen
        if (pd.notna(kb_manifest)) and (str(kb_manifest).strip() != ""):
            case_class = "wahrscheinlicher Fall"
        else:
            case_class = np.nan
 
    # 5) Ergebnisse in falldatenprodukt zurückschreiben
    #    Falls die Spalten noch nicht existieren, legen wir sie an.
    for col in ["lb_date", "lb_interpretation", "kb_date", "kb_manifestation", "case_class"]:
        if col not in falldatenprodukt.columns:
            falldatenprodukt[col] = np.nan
 
    # Zielzeile(n) finden und updaten
    mask_case = falldatenprodukt["case_ID"] == case_id
    if mask_case.any():
        falldatenprodukt.loc[mask_case, "lb_date"] = lb_date
        falldatenprodukt.loc[mask_case, "lb_interpretation"] = lb_interp
        falldatenprodukt.loc[mask_case, "kb_date"] = kb_date
        falldatenprodukt.loc[mask_case, "kb_manifestation"] = kb_manifest
        falldatenprodukt.loc[mask_case, "case_class"] = case_class
 
    # Praktisch: die wichtigsten Ergebnisse auch zurückgeben
    return {
        "case_ID": case_id,
        "IDs": list(ids_for_case),
        "lb_date": lb_date,
        "interpretation": lb_interp,
        "kb_date": kb_date,
        "manifestation": kb_manifest,
        "case_class": case_class
    }
 
# ------------------------------
# 5) Beispiel-Aufruf (Pseudo)
# ------------------------------
# Angenommen, du hast bereits folgende DataFrames:
# falldatenprodukt = pd.DataFrame(columns=["case_ID", "Patient_ID", "Pathogen_code", "Date", "case_class"])
# Fall_meldung_tabelle = pd.DataFrame(columns=["ID", "case_ID"])
# labordatenprodukt = pd.DataFrame(columns=["ID", "date", "interpretation"])
# klinikdatenprodukt = pd.DataFrame(columns=["ID", "date", "manifestation"])
#
# incoming = IncomingElement(
#     Patient_ID="P001",
#     Pathogen_code="A123",
#     Date=pd.Timestamp("2025-10-12"),
#     ID="MELDE-42"
# )
#
# case_id = upsert_case_and_link_id(
#     incoming, falldatenprodukt, Fall_meldung_tabelle, case_duration_days=28
# )
#
# result = collect_case_evidence(
#     case_id, falldatenprodukt, Fall_meldung_tabelle, labordatenprodukt, klinikdatenprodukt
# )
#
# print("Ergebnis:", result)
# print(falldatenprodukt)
# print(Fall_meldung_tabelle)
