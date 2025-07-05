# Full Planes - Flugsuche Web-Anwendung

## Warum?

Inspiriert durch den Tagesspiegel-Artikel ["Missbrauch von vertraulichen Informationen: Berliner CDU will Flüchtlingsaktivisten bestrafen, die Abschiebungen verraten"](
https://www.tagesspiegel.de/berlin/missbrauch-von-vertraulichen-informationen-berliner-cdu-will-fluchtlingsaktivisten-bestrafen-die-abschiebungen-verraten-13973525.html).

Da die CDU Berlin Menschen bestrafen will, die Flugdetails von Abschiebungen verraten, zeigt diese Anwendung, mit welch geringem Aufwand (kein halber Tag Programmierung mit Unterstützung durch eine KI) sich potenziell für Abschiebungen genutzte Flüge in Deutschland ermitteln lassen. 

Ich bin mal gespannt, ob diese App, die lediglich dazu dient, Flugdaten und Auslastungen von Linienflügen zügig zu ermitteln, schon kriminell ist ;-)

## Einrichtung

1.  **Abhängigkeiten installieren:**
    Stelle sicher, dass du Python 3 installiert hast. Installiere dann die notwendigen Pakete:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Amadeus API-Schlüssel:**
    Um die Anwendung zu nutzen, benötigst du eigene API-Schlüssel von Amadeus for Developers.
    1.  Registriere dich auf der [Amadeus for Developers Webseite](https://developers.amadeus.com/register).
    2.  Nach der Anmeldung, gehe zu deinem Dashboard und erstelle eine neue App.
    3.  Du erhältst einen "API Key" (Client ID) und einen "API Secret" (Client Secret).
    4.  Diese beiden Werte musst du in die `.env`-Datei eintragen, siehe nächster Schritt.
    Die Nutzung der Test-API im "Self-Service"-Tier ist kostenlos.

3.  **Umgebungsvariablen setzen:**
    Kopiere die `.env.example`-Datei zu `.env` und trage deine Amadeus API-Schlüssel ein:
    ```bash
    cp .env.example .env
    ```
    Öffne die `.env`-Datei und ersetze die Platzhalter.

## Nutzung

`python app.py` um die App zu starten.

Im Browser http://localhost:5000 öffnen und die Maske ausfüllen.

![Suchmaske](https://github.com/user-attachments/assets/6b5f0685-5d18-4bbd-9e73-3e39833bb486)

Auf "Flüge suchen" klicken, warten, bis Ergebnisse da sind:

![Ergebnisse](https://github.com/user-attachments/assets/c7760b71-c583-4d2c-b83c-63776f41bbf7)

## Wichtiger Hinweis

Diese Anwendung nutzt die **Test-API** von Amadeus. Die angezeigten Flugdaten sind daher **nicht real**, sondern dienen lediglich als Demonstrationsbeispiel.

Es werden ausschließlich **Linienflüge** abgefragt, keine Charterflüge, die häufig für Abschiebungen genutzt werden.

## Disclaimer

Diese Anwendung richtet sich gegen die versuchte Kriminialisierung von menschlicher Solidarität, nicht gegen Abschiebungen an sich.

## GPL

Lizenz: Diese App ist lizenziert unter der GPL 3.0 Lizenz. Sie darf kopiert, verändert und weitergegeben, aber nicht kommerziell verwendet werden.

*Erstellt: 2025-07-05*
