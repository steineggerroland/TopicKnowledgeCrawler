# Content Collector

Ein **Content Collector** zur automatisierten Sammlung und Aufbereitung von Informationen aus RSS-Feeds. Die Daten werden gespeichert, zusammengefasst und kategorisiert mithilfe von **OpenAI GPT**.

## Features
- Automatisches Sammeln von Artikeln aus RSS-Feeds
- Speicherung von Rohdaten und Archivierung
- Text-Zusammenfassung (Kurz- und Langform) durch GPT-Integration
- Kategorisierung und Bewertung der Relevanz der Inhalte
- Ausgabe der aufbereiteten Daten als JSON-Dateien

---

## Installation

1. **Virtuelle Umgebung erstellen und aktivieren**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Für Linux/macOS
   .venv\Scripts\activate     # Für Windows
   ```

2. **Abhängigkeiten installieren**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **API-Schlüssel einrichten**:
   - Erstelle eine `.env`-Datei im Projektverzeichnis:
     ```plaintext
     OPENAI_API_KEY=your_openai_api_key_here
     ```

---

## n8n-Orchestrierung

Workflow mit **Data Tables**, **Python Code Nodes** und **AI Nodes** (ohne `summary_history.json`) ist unter [`n8n/README.md`](n8n/README.md) beschrieben. Python-Paket für n8n: **`tkcrawler`** (`src/tkcrawler/`).

## Geplante Weiterentwicklung

Die Zielarchitektur ist in [`docs/TARGET_ARCHITECTURE.md`](docs/TARGET_ARCHITECTURE.md) definiert. Die naechsten Schritte fuer intelligentere Source-Policies, Vorab-Skip-Logik, Rate-Limits und eine engere infl0-Integration sind in [`docs/PLANNED_CHANGES.md`](docs/PLANNED_CHANGES.md) gesammelt. Der konkrete Umsetzungsplan steht in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

## Ausführung

1. **Quellen konfigurieren**:  
   Bearbeite die Datei `config/sources.json`:
   ```json
   {
     "sources": [
       {
         "name": "Quellname",
         "type": "rss",
         "url": "https://somenonexisting.url/feed.atom"
       }
     ]
   }
   ```

2. **Rohdaten sammeln**:
   ```bash
   python src/collector.py
   ```

3. **Wissensextraktion und Zusammenfassung**:
   ```bash
   python src/summarizer.py
   ```

Die Rohdaten werden im Ordner `data/raw` gespeichert und die aufbereiteten JSON-Dateien landen in `data/processed`.

---

## Projektstruktur

```plaintext
content_collector/
│
├── config/                
│   └── sources.json           # Konfigurationsdatei für Quellen (RSS-Feeds)
│
├── data/                     
│   ├── raw/                   # Gesammelte Rohdaten
│   └── processed/             # Zusammengefasste Daten
│
├── src/                      
│   ├── collector.py           # Informationssammler
│   ├── summarizer.py          # Wissensextraktion und GPT-Integration
│   ├── archiver.py            # Rohdatenarchivierung
│   └── utils/                 # Hilfsfunktionen
│
├── tests/                     # Tests
│
├── .env                       # API-Schlüssel (nicht in Git pushen!)
├── .gitignore                 # Ignoriert .env und .venv
├── pyproject.toml             # Projektkonfiguration und Abhängigkeiten
└── README.md                  # Diese Datei
```

---
