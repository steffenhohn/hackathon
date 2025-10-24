Ziel

Python-Code schreiben, der Meldungen faellen zuordnet (oder neue Faelle anlegt), relevante Labor- und Klinikinfos sammelt und den Fall klassifiziert.

Eingabedaten (pro neue Meldung)

Patient_ID

Pathogen_code

Date

ID (Melde-ID)

Verfuegbare Tabellen

falldatenprodukt: case_ID, Patient_ID, Pathogen_code, Date, case_class (optional, wird gefuellt)

Fall_meldung_tabelle: ID, case_ID

labordatenprodukt: ID, date, interpretation

klinikdatenprodukt: ID, date, manifestation

Fall-Matching (Case-Duration 28 Tage)

Suche in falldatenprodukt einen Eintrag mit gleicher Patient_ID und Pathogen_code, dessen Date innerhalb ± 28 Tagen zum Eingangs-Date liegt.

Wenn gefunden:

Verwende dessen case_ID.

Fuege in Fall_meldung_tabelle einen Eintrag {ID, case_ID} hinzu (nur wenn noch nicht vorhanden).

Wenn nicht gefunden:

Erzeuge eine neue case_ID.

Lege in falldatenprodukt einen neuen Datensatz {case_ID, Patient_ID, Pathogen_code, Date} an.

Fuege {ID, case_ID} in Fall_meldung_tabelle hinzu.

Falls mehrere Faelle im 28-Tage-Fenster existieren, waehle den mit der kleinsten Datumsdifferenz (nächstliegendes Date).

Evidenz sammeln (pro case_ID)

IDs bestimmen: Hole alle ID aus Fall_meldung_tabelle, die zu dieser case_ID gehoeren.

Labor pruefen (labordatenprodukt):

Filtere auf diese IDs.

Wenn mehrere Treffer: waehle die frueheste date.

Speichere als lb_date und interpretation.

Klinik pruefen (klinikdatenprodukt):

Filtere auf diese IDs.

Wenn mehrere Treffer: waehle die frueheste date.

Speichere als kb_date und manifestation.

Schreibe die gefundenen Werte in falldatenprodukt fuer diese case_ID:

lb_date, interpretation,

kb_date, manifestation.

Fallklassifikation (Gonorrhoe specific)

Wenn interpretation == "Pos" → case_class = "sicherer Fall".

Wenn interpretation == "Neg" → case_class = "kein Fall".

Wenn interpretation leer/nicht vorhanden und manifestation nicht leer → case_class = "wahrscheinlicher Fall".

Andernfalls: case_class unveraendert/leer lassen.

Annahmen und Hinweise

Saemtliche Datumsfelder sind als Datetime zu behandeln (kein Stringvergleich).

Eintrag {ID, case_ID} wird nicht dupliziert, wenn bereits vorhanden.

Neue Spalten (lb_date, lb_interpretation, kb_date, kb_manifestation, case_class) werden bei Bedarf in falldatenprodukt angelegt.

Kurz-Pseudocode:

find_or_create_case(Patient_ID, Pathogen_code, Date, ID) → case_ID

collect_evidence(case_ID) → (lb_date, interpretation, kb_date, manifestation)

classify_case(interpretation, manifestation) → case_class

update_falldatenprodukt mit obigen Werten

