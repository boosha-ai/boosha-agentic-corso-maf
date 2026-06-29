# Setup

Due modi per seguire le puntate: **Google Colab** (zero installazione) o **locale** con `uv` e Jupyter.

## Google Colab

Apri `pratica.ipynb` della puntata col badge "Apri in Colab" nel suo README. La prima cella rileva l'ambiente e installa le dipendenze con `pip`. Ti servira' solo la `OPENAI_API_KEY` (la inserisci quando il notebook la chiede, o nei *Secrets* di Colab).

## Locale (uv + VS Code)

Gestione dipendenze con [`uv`](https://docs.astral.sh/uv/).

```bash
# dalla cartella del corso
uv sync
uv run jupyter lab
```

Se preferisci partire da zero invece di `uv sync`:

```bash
uv init
uv add agent-framework-core agent-framework-openai agent-framework-ollama python-dotenv
```

> Nota: il meta-pacchetto `agent-framework[all]` non risolve per via degli extra Azure ancora in pre-release. Si installano i sotto-pacchetti elencati sopra.

## Variabili d'ambiente (`.env`)

MAF non carica il `.env` da solo: i notebook chiamano `load_dotenv()`. Copia il template e compila:

```bash
cp .env.example .env
```

- `OPENAI_API_KEY` - sempre (provider cloud di default).
- `PUSHOVER_TOKEN` / `PUSHOVER_USER` - opzionali, per le notifiche push (da EP 1 in poi).
- Ollama gira in locale e non richiede chiave (default `http://localhost:11434`).

## Provider

- **OpenAI** e' il default cross-platform di tutte le puntate.
- **Ollama** compare solo in EP 1, per chi vuole un modello locale. Usa un modello piccolo non-reasoning (es. `llama3.2` 3B): i modelli grossi o "thinking" rallentano molto.
