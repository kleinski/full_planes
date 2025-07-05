# Full Planes - Flugsuche Web-Anwendung

## Einrichtung

1.  **Abhängigkeiten installieren:**
    Stelle sicher, dass du Python 3 installiert hast. Installiere dann die notwendigen Pakete:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Umgebungsvariablen setzen:**
    Kopiere die `.env.example`-Datei zu `.env` und trage deine Amadeus API-Schlüssel ein:
    ```bash
    cp .env.example .env
    ```
    Öffne die `.env`-Datei und ersetze die Platzhalter.

## Wichtiger Hinweis

Diese Anwendung nutzt die **Test-API** von Amadeus. Die angezeigten Flugdaten sind daher **nicht real**, sondern dienen lediglich als Demonstrationsbeispiel.

Es werden ausschließlich **Linienflüge** abgefragt, keine Charterflüge, die häufig für Abschiebungen genutzt werden.

## Warum?

Inspiriert durch den Tagesspiegel-Artikel "Missbrauch von vertraulichen Informationen: Berliner CDU will Flüchtlingsaktivisten bestrafen, die Abschiebungen verraten":
https://www.tagesspiegel.de/berlin/missbrauch-von-vertraulichen-informationen-berliner-cdu-will-fluchtlingsaktivisten-bestrafen-die-abschiebungen-verraten-13973525.html

Da die CDU Berlin Menschen bestrafen will, die Flugdetails von Abschiebungen verraten, zeigt diese Anwendung, mit welch geringem Aufwand (kein halber Tag Programmierung mit Unterstützung durch eine KI) sich potenziell für Abschiebungen genutzte Flüge in Deutschland ermitteln lassen. Mal sehen, ob die CDU auch versuchen wird, diese Anwendung zu kriminalisieren.

## Disclaimer

Diese Anwendung richtet sich gegen die versuchte Kriminialisierung von menschlicher Solidarität, nicht gegen Abschiebungen an sich.

## GPL

Lizenz: Diese App ist lizenziert unter der GPL 3.0 Lizenz. Sie darf kopiert, verändert und weitergegeben, aber nicht kommerziell verwendet werden.

*Erstellt: 2025-07-05*