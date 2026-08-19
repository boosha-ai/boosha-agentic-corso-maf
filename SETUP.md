# Setup

Due modi per seguire le puntate: **Google Colab** (zero installazione) o **locale** con `uv` e Jupyter.

## Google Colab

Apri `pratica.ipynb` della puntata col badge "Apri in Colab" nel suo README. La prima cella rileva l'ambiente e installa le dipendenze con `pip`. Ti servira' solo la `OPENAI_API_KEY`: il notebook te la chiede con un prompt nascosto, e resta in memoria per tutta la sessione (non viene salvata da nessuna parte).

## Locale (uv + VS Code)

Gestione dipendenze con [`uv`](https://docs.astral.sh/uv/).

```bash
# dalla cartella del corso
uv sync --all-groups
uv run jupyter lab
```

Se preferisci partire da zero invece di `uv sync`:

```bash
uv init
uv add agent-framework-core agent-framework-openai agent-framework-ollama python-dotenv beautifulsoup4 mcp tavily-python gradio
```

> Nota: il meta-pacchetto `agent-framework[all]` non risolve per via degli extra Azure ancora in pre-release. Si installano i sotto-pacchetti elencati sopra.
>
> Nota: `gradio` serve solo a `agente.py` di EP 3, che apre una piccola interfaccia nel browser. I notebook non lo usano.

## Script da terminale (`agente.py`)

Ogni puntata ha anche uno script standalone, che si lancia dalla cartella dell'episodio:

```bash
cd maf/ep03_memoria_stato
uv run python agente.py
```

In EP 3 lo script apre un'interfaccia nel browser (si apre da sola su `127.0.0.1`). Se lavori da remoto, per esempio via SSH, dove `127.0.0.1` non e' raggiungibile dal tuo browser, aggiungi `--share` per ottenere un link pubblico temporaneo:

```bash
uv run python agente.py --share
```

## Variabili d'ambiente (`.env`)

MAF non carica il `.env` da solo: i notebook chiamano `load_dotenv()`. Copia il template e compila:

```bash
cp .env.example .env
```

- `OPENAI_API_KEY` - sempre (provider cloud di default).
- `PUSHOVER_TOKEN` / `PUSHOVER_USER` - opzionali, per le notifiche push (da EP 1 in poi).
- `TAVILY_API_KEY` - opzionale, per la ricerca recensioni su domini fidati (da EP 2).
- Ollama gira in locale e non richiede chiave (default `http://localhost:11434`).

> Guida passo-passo per creare le chiavi: [`maf/Extra/chiavi-api.md`](maf/Extra/chiavi-api.md).
> Approfondimento su `uv`: [`maf/Extra/ambiente-python-uv.md`](maf/Extra/ambiente-python-uv.md).

## Provider

- **OpenAI** e' il default cross-platform di tutte le puntate.
- **Ollama** compare solo in EP 1, per chi vuole un modello locale. Usa un modello piccolo non-reasoning (es. `llama3.2` 3B): i modelli grossi o "thinking" rallentano molto.
