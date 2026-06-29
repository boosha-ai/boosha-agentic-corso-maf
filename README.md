# Boosha - corso agentic AI (Microsoft Agent Framework)

Materiale della serie YouTube di Boosha su come costruire agenti AI in modo code-first e production-minded, con il **Microsoft Agent Framework (MAF)**.

Ogni puntata costruisce qualcosa che funziona end-to-end: si parte dall'agente base e si arriva a orchestrazione, workflow deterministici e valutazione automatica.

> Esiste una serie gemella su **LangGraph** (stesso arco didattico, framework diverso). Verra' pubblicata a parte.

## Come partire

Ogni puntata sta in `maf/epNN_nome/` e contiene:

- `pratica.ipynb` - il notebook eseguibile, da aprire in Google Colab o in Jupyter (VS Code).
- `agente.py` - lo script da terminale, quando la puntata lo prevede.

Il modo piu' veloce: apri il notebook con il badge **"Apri in Colab"** nel README di ogni puntata. In Colab la prima cella rileva l'ambiente e installa le dipendenze da sola.

Per scaricare tutto in locale: `Code -> Download ZIP` qui su GitHub, oppure clona la repo.

## Setup in locale

Vedi [`SETUP.md`](SETUP.md). In sintesi (gestione dipendenze con [`uv`](https://docs.astral.sh/uv/)):

```bash
uv sync
cp .env.example .env   # poi inserisci la tua OPENAI_API_KEY
uv run jupyter lab
```

## A chi e' rivolto

Sviluppatori con un po' di Python (e nozioni minime di `async`/`await`) che vogliono costruire agenti senza lock-in di framework. Non serve esperienza con AutoGen o Semantic Kernel. Serve una chiave OpenAI; Ollama e' opzionale (solo EP 1, per chi vuole girare in locale).

## Le puntate

| EP | Tema | Stato |
| --- | --- | --- |
| [1](maf/ep01_primo_agente/) | Il tuo primo agente (agente vs workflow, multi-provider) | disponibile |
| 2 | Dare strumenti: tools + MCP | in arrivo |
| 3 | Memoria e stato: thread, sessioni, context provider | in arrivo |
| 4 | Orchestrare piu' agenti: handoff e group chat | in arrivo |
| 5 | Workflow deterministici + human-in-the-loop | in arrivo |
| 6 | Valutare: AI-as-judge + AI avversaria | in arrivo |

## Link

- Sito Boosha: <https://boosha.it/>
- YouTube: <https://www.youtube.com/@BooshaAI>
- LinkedIn Boosha: <https://www.linkedin.com/company/boosha-ai/>
- LinkedIn Veronica: <https://www.linkedin.com/in/veronicaschembri/>

## Licenza

Materiale rilasciato con licenza [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE): puoi riusarlo e adattarlo, anche commercialmente, **citando Boosha** come fonte.
