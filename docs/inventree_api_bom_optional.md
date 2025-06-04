Hier das Wichtigste in Kürze: Jede Zeile einer Stückliste (BOM) besitzt im InvenTree-Modell **BomItem** ein bool’sches Feld *optional*. Über die Python-Bibliothek **inventree** kannst du dieses Feld direkt abfragen – entweder als Attribut des einzelnen BomItem-Objekts oder schon beim List-Aufruf via Filter `optional=True/False`. Unten findest du ein Minimal-Skript, das beide Varianten zeigt und damit zuverlässig erkennt, ob ein bestimmtes Teil in der BOM als „optional“ markiert wurde.

---

## 1  Hintergrund: das Feld *optional*

* In der Web-UI wird es als Checkbox „Optional“ angezeigt; technisch ist es ein bool’sches Datenbankfeld des Modells **BomItem**. ([docs.inventree.org][1])
* Das REST-End-point `/api/bom/` liefert es genauso zurück und erlaubt es auch als Query-Parameter zum Filtern. ([docs.inventree.org][2])

---

## 2  Python-Zugriff mit der Bibliothek *inventree*

### 2.1 Installation und Verbindung

```bash
pip install inventree
```

```python
from inventree.api import InvenTreeAPI
api = InvenTreeAPI("https://dein-server.tld", token="API_TOKEN")
```

*(Benutzername/Passwort gehen natürlich auch.)* ([github.com][3])

### 2.2 Feldnamen nachschlagen (optional)

Mit `fieldNames` oder `fieldInfo` kannst du dir live anzeigen lassen, welche Felder verfügbar sind – darunter eben auch *optional*. ([docs.inventree.org][4])

```python
from inventree.bom import BomItem
print("optional" in BomItem.fieldNames(api))   # -> True
```

---

## 3  Beispielskript

```python
"""
Zeigt alle BOM-Positionen eines gewählten Assembly-Teils
und druckt, ob sie optional sind.
"""
from inventree.api import InvenTreeAPI
from inventree.part import Part
from inventree.bom import BomItem

# 1) Verbinden
api = InvenTreeAPI("https://dein-server.tld", token="API_TOKEN")

# 2) Das Assembly-Teil holen (hier per Name – alternativ per PK)
assembly = Part.list(api, name="Meine Hauptplatine")[0]   # first match

# 3a) Alle BOM-Positionen dieses Assemblys abrufen
items = BomItem.list(api, part=assembly.pk)

print(f"BOM von '{assembly.name}':")
for line in items:
    status = "OPTIONAL" if line.optional else "Pflichtteil"
    print(f"- {line.sub_part['name']:30s}  →  {status}")

# 3b) Nur die optionalen Positionen vorab filtern (API tut das server-seitig)
optionals = BomItem.list(api, part=assembly.pk, optional=True)
print(f"\nNur optionale Positionen ({len(optionals)}):")
for line in optionals:
    print(f"- {line.sub_part['name']}")
```

**Was passiert im Skript?**

1. Es authentifiziert sich bei deinem InvenTree-Server.
2. Es sucht das gewünschte Assembly-Teil und holt dessen Primärschlüssel (`pk`).
3. Es zieht sämtliche **BomItem**-Datensätze zu diesem Assembly und greift auf das Attribut `line.optional` zu.
4. Alternativ filtert es gleich server-seitig mit `optional=True`, falls du nur die optionalen Zeilen brauchst.

Das Ganze funktioniert identisch, wenn du statt `print` die Daten weiterverarbeitest – z. B. um Pflichtteile und optionale Teile in zwei Tabellen aufzuteilen oder einen Report zu generieren. Die BOM-Positionen sind vollwertige Objekte; d. h. du kannst sie ebenso updaten oder neu anlegen (vgl. offizielle Beispiele). ([docs.inventree.org][5])

---

## 4  Tipps & Fallstricke

* **Große BOMs**: Verwende ggf. das Paging der API (`limit` / `offset`) oder die Hilfsfunktion `all()` der Bibliothek, um automatisch alle Seiten einzusammeln.
* **Variant- oder Sub-BOMs**: Willst du eine verschachtelte BOM durchlaufen, ruf erst die BOM des Assemblys ab und iteriere dann rekursiv über Unter-Assembly-Teile.
* **Caching**: Wenn du das Skript häufiger ausführst, lohnt es sich, die Antworten zwischenzuspeichern (z. B. mit `requests-cache`), um die Server-Last zu senken.

Damit solltest du zuverlässig feststellen können, ob eine BOM-Zeile optional ist – und hast gleich einen Boiler-Plate-Code, den du in größere Tools integrieren kannst. Viel Erfolg!

[1]: https://docs.inventree.org/en/stable/build/bom/?utm_source=chatgpt.com "Bill of Materials - InvenTree Documentation"
[2]: https://docs.inventree.org/en/0.15.7/api/schema/bom/?utm_source=chatgpt.com "Bill of Materials - InvenTree Documentation"
[3]: https://github.com/inventree/inventree-python?utm_source=chatgpt.com "Python library for communication with inventree via API - GitHub"
[4]: https://docs.inventree.org/en/latest/api/python/?utm_source=chatgpt.com "Python Interface - InvenTree Documentation"
[5]: https://docs.inventree.org/en/stable/api/python/examples/?utm_source=chatgpt.com "Python Interface Examples - InvenTree Documentation"
