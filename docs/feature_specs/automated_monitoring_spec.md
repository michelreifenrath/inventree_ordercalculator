# Spezifikation: Automatisierte Teilelistenüberwachung und E-Mail-Benachrichtigung

Dieses Dokument definiert die funktionalen Anforderungen und technischen Spezifikationen für die Implementierung einer automatisierten Überwachungsfunktion für Teilelisten mit anschließender E-Mail-Benachrichtigung.

## 1. Übersicht

Die Funktion ermöglicht es Benutzern, spezifische Teilelisten mit Mengen zu definieren. Diese Listen werden in konfigurierbaren Intervallen automatisch überprüft, wobei die bestehende Kalkulationslogik des Inventree Order Calculators verwendet wird. Das Ergebnis der Überprüfung (analog zur aktuellen Streamlit-App- oder CLI-Ausgabe) wird dann per E-Mail an konfigurierbare Empfänger gesendet.

## 2. Detaillierte Spezifikationen

### 2.1. Datenspeicherung der Teilelisten

*   **Anforderung:** Zu überwachende Teilelisten und deren Mengen müssen persistent gespeichert werden.
*   **Lösung:** Die bestehende Datei [`presets.json`](presets.json) wird erweitert. Ein neuer Top-Level-Schlüssel `monitoring_lists` wird eingeführt. Dieser Schlüssel enthält ein Array von Überwachungslistenobjekten.
*   **Struktur pro Überwachungsliste in [`presets.json`](presets.json):**
    ```json
    {
      "id": "uuid_string_als_eindeutige_id", // Eindeutige ID für die Aufgabe
      "name": "Bezeichnung der Überwachungsliste", // Benutzerdefinierter Name
      "parts": [
        {"name": "Teil A", "quantity": 10, "version": "optional_specific_version"},
        {"name": "Teil B", "quantity": 5}
      ],
      "active": true, // boolean: true = aktiv, false = inaktiv
      "cron_schedule": "0 * * * *", // Cron-Ausdruck für den Überprüfungszyklus
      "recipients": ["empfaenger1@example.com", "empfaenger2@example.com"], // E-Mail-Empfänger für diese Liste
      "notify_condition": "on_change", // "always" oder "on_change"
      "last_hash": "optional_md5_hash_of_last_significant_result" // Für "on_change" Logik
    }
    ```
*   **TDD-Anker:**
    *   `// TEST: presets_manager_can_load_monitoring_lists`
    *   `// TEST: presets_manager_can_save_new_monitoring_list`
    *   `// TEST: presets_manager_can_update_existing_monitoring_list`
    *   `// TEST: presets_manager_can_delete_monitoring_list`
    *   `// TEST: monitoring_list_schema_validation_passes_for_valid_data`
    *   `// TEST: monitoring_list_schema_validation_fails_for_invalid_data`

### 2.2. Konfiguration des Überprüfungszyklus

*   **Anforderung:** Der Intervall oder Zeitplan für die zyklische Überprüfung muss pro Liste konfigurierbar sein.
*   **Lösung:** Jede Überwachungsliste in [`presets.json`](presets.json) enthält ein Feld `cron_schedule`, das einen Cron-ähnlichen Ausdruck zur Definition des Zeitplans akzeptiert (z.B. "0 9 * * 1-5" für jeden Werktag um 9:00 Uhr). Eine Bibliothek zur Interpretation von Cron-Ausdrücken wird verwendet.
*   **TDD-Anker:**
    *   `// TEST: scheduler_correctly_parses_valid_cron_schedule`
    *   `// TEST: scheduler_rejects_invalid_cron_schedule`
    *   `// TEST: scheduler_triggers_task_at_correct_time_based_on_cron`

### 2.3. E-Mail-Inhalt

*   **Anforderung:** Der E-Mail-Inhalt soll die relevanten Ergebnisse der Überprüfung klar und verständlich darstellen.
*   **Lösung:**
    *   **Format:** Die E-Mail wird primär als HTML formatiert, um Tabellen und Hervorhebungen zu ermöglichen. Eine Plain-Text-Alternative wird ebenfalls bereitgestellt.
    *   **Inhalt:** Die E-Mail enthält die gleichen Informationen und Tabellen, die auch in der Streamlit-App und der CLI-Ausgabe generiert werden:
        *   Name der überwachten Liste
        *   Datum und Uhrzeit der Überprüfung
        *   Zusammenfassung (z.B. Gesamtbedarf, Deckung)
        *   Detaillierte Stückliste mit Mengen, verfügbaren Mengen, Fehlmengen
        *   Informationen zu Alternativteilen (falls relevant und implementiert)
        *   Fehler oder Warnungen während der Kalkulation (z.B. Teil nicht gefunden)
*   **TDD-Anker:**
    *   `// TEST: email_generator_creates_html_output_from_calculation_result`
    *   `// TEST: email_generator_creates_plaintext_output_from_calculation_result`
    *   `// TEST: email_content_includes_all_required_tables_and_summary`

### 2.4. E-Mail-Konfiguration

*   **Anforderung:** Parameter für den E-Mail-Versand müssen sicher konfiguriert werden können.
*   **Lösung:**
    *   Die Konfiguration erfolgt über Umgebungsvariablen oder eine separate `.env`-Datei, die von `.gitignore` erfasst wird.
    *   **Benötigte Parameter:**
        *   `EMAIL_SMTP_SERVER`: Adresse des SMTP-Servers
        *   `EMAIL_SMTP_PORT`: Port des SMTP-Servers (z.B. 587 oder 465)
        *   `EMAIL_USE_TLS`: `true` oder `false`
        *   `EMAIL_USE_SSL`: `true` oder `false`
        *   `EMAIL_USERNAME`: Benutzername für die SMTP-Authentifizierung
        *   `EMAIL_PASSWORD`: Passwort für die SMTP-Authentifizierung (sensibel!)
        *   `EMAIL_SENDER_ADDRESS`: Absender-E-Mail-Adresse
        *   `ADMIN_EMAIL_RECIPIENTS`: Komma-separierte Liste von Admin-E-Mail-Adressen für Systemfehlerbenachrichtigungen.
    *   Die Empfänger für die regulären Berichte werden pro Überwachungsliste in [`presets.json`](presets.json) definiert (`recipients`-Array).
*   **Sicherheit:** Passwörter und andere sensible Daten werden niemals im Code oder in versionierten Konfigurationsdateien gespeichert. Die Verwendung von Umgebungsvariablen ist hierfür der Standard.
*   **TDD-Anker:**
    *   `// TEST: email_config_loads_parameters_from_env_variables`
    *   `// TEST: email_sender_connects_to_smtp_server_with_tls`
    *   `// TEST: email_sender_connects_to_smtp_server_with_ssl`
    *   `// TEST: email_sender_authenticates_successfully`
    *   `// TEST: email_sender_fails_gracefully_on_auth_failure`

### 2.5. Fehlerbehandlung

*   **Anforderung:** Das System muss robust auf verschiedene Fehlerszenarien reagieren.
*   **Lösung:**
    *   **Logging:** Alle Operationen, Fehler und Warnungen werden detailliert geloggt. Dies beinhaltet den Start und das Ende jeder Überprüfung, API-Aufrufe, Kalkulationsergebnisse und E-Mail-Versandstatus.
    *   **InvenTree API nicht erreichbar:**
        *   Loggen des Fehlers.
        *   Versuch eines oder mehrerer Wiederholungsversuche mit exponentiellem Backoff.
        *   Wenn weiterhin nicht erreichbar, Versand einer Benachrichtigungs-E-Mail an `ADMIN_EMAIL_RECIPIENTS`. Die reguläre Berichts-E-Mail wird nicht gesendet oder enthält eine Fehlermeldung.
    *   **Teile nicht gefunden:**
        *   Dies wird als Teil des normalen Kalkulationsergebnisses behandelt und in der E-Mail entsprechend ausgewiesen (z.B. in der Tabelle der Fehlmengen). Es führt nicht zu einem Systemfehler, es sei denn, es ist ein Konfigurationsproblem.
    *   **E-Mail-Versand fehlgeschlagen:**
        *   Loggen des Fehlers (inkl. SMTP-Fehlermeldung).
        *   Versuch eines oder mehrerer Wiederholungsversuche mit exponentiellem Backoff.
        *   Wenn weiterhin fehlschlägt, Versand einer Benachrichtigungs-E-Mail an `ADMIN_EMAIL_RECIPIENTS` (falls möglich, ggf. über einen alternativen Kanal oder nur Logging, wenn das primäre E-Mail-System betroffen ist).
    *   **Konfigurationsfehler (z.B. ungültiger Cron-String, fehlerhafte E-Mail-Konfig):**
        *   Loggen des Fehlers.
        *   Deaktivierung der betroffenen Überwachungsaufgabe (optional, mit Benachrichtigung an Admin).
        *   Benachrichtigung an `ADMIN_EMAIL_RECIPIENTS`.
*   **TDD-Anker:**
    *   `// TEST: error_handler_logs_api_unreachable_error`
    *   `// TEST: error_handler_initiates_retry_for_api_error`
    *   `// TEST: error_handler_sends_admin_notification_for_persistent_api_error`
    *   `// TEST: error_handler_logs_email_send_failure`
    *   `// TEST: error_handler_initiates_retry_for_email_send_failure`
    *   `// TEST: error_handler_sends_admin_notification_for_persistent_email_failure`
    *   `// TEST: part_not_found_is_reported_in_email_not_as_system_error`

### 2.6. Verwaltung der Überwachungsaufgaben

*   **Anforderung:** Benutzer sollen Überwachungsaufgaben erstellen, anzeigen, ändern, löschen, aktivieren und deaktivieren können.
*   **Lösung:**
    *   **CLI:** Neue Befehle werden zur CLI hinzugefügt:
        *   `inventree-order-calculator monitor list`: Zeigt alle Überwachungsaufgaben an.
        *   `inventree-order-calculator monitor add --name "Name" --parts "Teil1:10,Teil2:5" --schedule "0 9 * * *" --recipients "a@b.c,d@e.f" [--notify-condition "on_change|always"]`: Fügt eine neue Aufgabe hinzu.
        *   `inventree-order-calculator monitor update <task_id> [--name "Neuer Name"] [--parts "..."] [--schedule "..."] [--recipients "..."] [--active true|false] [--notify-condition "on_change|always"]`: Aktualisiert eine bestehende Aufgabe.
        *   `inventree-order-calculator monitor delete <task_id>`: Löscht eine Aufgabe.
        *   `inventree-order-calculator monitor activate <task_id>`: Aktiviert eine Aufgabe.
        *   `inventree-order-calculator monitor deactivate <task_id>`: Deaktiviert eine Aufgabe.
        *   `inventree-order-calculator monitor run <task_id>`: Führt eine Aufgabe manuell aus (außerhalb des Zeitplans).
    *   **Streamlit UI:** Ein neuer Bereich in der Streamlit-UI wird erstellt, um Überwachungsaufgaben grafisch zu verwalten (CRUD-Operationen, Aktivierung/Deaktivierung). Dies interagiert mit den gleichen Funktionen des `PresetsManager` wie die CLI.
    *   Die `id` für jede Aufgabe wird automatisch generiert (z.B. UUID) bei der Erstellung.
*   **TDD-Anker:**
    *   `// TEST: cli_monitor_list_displays_tasks`
    *   `// TEST: cli_monitor_add_creates_new_task_in_presets`
    *   `// TEST: cli_monitor_update_modifies_existing_task`
    *   `// TEST: cli_monitor_delete_removes_task_from_presets`
    *   `// TEST: cli_monitor_activate_sets_task_active_flag_true`
    *   `// TEST: cli_monitor_deactivate_sets_task_active_flag_false`
    *   `// TEST: streamlit_ui_can_display_monitoring_tasks`
    *   `// TEST: streamlit_ui_can_create_new_monitoring_task`
    *   `// TEST: streamlit_ui_can_edit_monitoring_task`
    *   `// TEST: streamlit_ui_can_delete_monitoring_task`

### 2.7. Benachrichtigungslogik

*   **Anforderung:** E-Mails sollen entweder bei jeder Überprüfung oder nur bei relevanten Änderungen gesendet werden.
*   **Lösung:**
    *   Jede Überwachungsliste in [`presets.json`](presets.json) hat ein Feld `notify_condition` mit den möglichen Werten:
        *   `"always"`: Eine E-Mail wird nach jeder erfolgreichen Überprüfung gesendet.
        *   `"on_change"`: Eine E-Mail wird nur gesendet, wenn sich das Ergebnis der Überprüfung signifikant vom vorherigen Ergebnis unterscheidet.
            *   Um "signifikante Änderungen" zu erkennen, wird ein Hash (z.B. MD5) des relevanten Teils des Kalkulationsergebnisses (z.B. der Tabelle der Fehlmengen oder einer Zusammenfassung der kritischen Teile) gespeichert (`last_hash` im `monitoring_lists` Objekt). Bei jeder neuen Überprüfung wird der aktuelle Hash mit dem gespeicherten Hash verglichen.
*   **TDD-Anker:**
    *   `// TEST: notification_logic_sends_email_if_condition_is_always`
    *   `// TEST: notification_logic_calculates_result_hash_correctly`
    *   `// TEST: notification_logic_sends_email_if_condition_is_on_change_and_hash_differs`
    *   `// TEST: notification_logic_does_not_send_email_if_condition_is_on_change_and_hash_is_same`
    *   `// TEST: notification_logic_updates_last_hash_after_sending_on_change_email`

## 3. Nicht-funktionale Anforderungen

*   **Performance:** Die Überprüfung und E-Mail-Generierung sollte performant genug sein, um auch bei mehreren Überwachungsaufgaben nicht das System übermäßig zu belasten. API-Aufrufe an InvenTree sollten effizient gestaltet sein.
*   **Sicherheit:** Sensible Daten (Passwörter) müssen sicher gehandhabt werden (siehe 2.4).
*   **Skalierbarkeit:** Das System sollte so konzipiert sein, dass es eine moderate Anzahl von Überwachungsaufgaben verwalten kann.
*   **Zuverlässigkeit:** Der Überwachungsprozess und der E-Mail-Versand müssen zuverlässig funktionieren. Fehler müssen korrekt behandelt und geloggt werden.
*   **Wartbarkeit:** Der Code für diese Funktion sollte modular, gut dokumentiert und testbar sein.

## 4. Entschiedene Punkte (vormals "Offene Punkte")

*   **Definition von "signifikanten Änderungen" für die `on_change` Benachrichtigungslogik:** Für die Hash-Berechnung werden die "Fehlmengenliste" und "kritische Teile unter Schwellenwert" (sofern definiert und relevant) herangezogen. Dies stellt sicher, dass nur relevante Änderungen eine Benachrichtigung auslösen.
*   **Scheduler-Bibliothek:** `APScheduler` wird für die Implementierung der Cron-basierten Zeitplanung verwendet, aufgrund seiner Robustheit und Flexibilität.
*   **Globaler E-Mail-Schalter:** Eine Umgebungsvariable `GLOBAL_EMAIL_NOTIFICATIONS_ENABLED` (Werte: `true` oder `false`, Standard `true`) wird eingeführt. Wenn auf `false` gesetzt, werden keine E-Mail-Benachrichtigungen (weder Berichte noch Admin-Benachrichtigungen) versendet. Dies dient als globaler Schalter für Wartungsarbeiten oder Tests.

## 5. Pseudocode-Module (Platzhalter für spätere Detaillierung)

*   `08_monitoring_service_pseudocode.md` (Hauptlogik für Scheduling, Ausführung der Checks)
*   `09_email_service_pseudocode.md` (Logik für E-Mail-Generierung und -Versand)
*   Erweiterungen in `01_config_pseudocode.md` (für E-Mail-Konfiguration)
*   Erweiterungen in `presets_manager_pseudocode.md` (für CRUD der Monitoring-Listen)
*   Erweiterungen in `05_cli_pseudocode.md` (für neue CLI-Befehle)
*   Erweiterungen in `07_streamlit_ui_spec.md` (für neue UI-Elemente)