# Appendice · Gestione ambiente Python con `uv`

> Modulo opzionale. Risponde a una domanda pratica: *"come faccio a far ripartire un progetto
> Python identico sul mio computer?"* È il problema di tutti i giorni di chi lavora con gli agenti.

## Il problema

Ogni progetto Python ha le sue dipendenze (librerie) e le sue versioni. Se le installi
"alla rinfusa" sul sistema, prima o poi due progetti litigano ("a me funziona, a te no").
La soluzione: ogni progetto ha il **suo ambiente isolato** e una **lista riproducibile** di cosa serve.

`uv` (di Astral) fa tutto questo, ed è veloce. Sostituisce `pip` + `venv` + `pip-tools` in un unico strumento.

---

## I 4 comandi che userai davvero

```bash
uv init                    # crea lo scheletro del progetto (pyproject.toml + .venv)
uv add requests            # aggiungi una dipendenza (la scrive nel pyproject e la installa)
uv sync                    # allinea il tuo ambiente a quello descritto nei file (LA chiave!)
uv run python main.py      # esegui qualcosa dentro l'ambiente del progetto
```

Altri utili:
```bash
uv remove requests         # togli una dipendenza
uv lock                    # rigenera il lockfile (di solito lo fa già add/sync)
```

---

## I tre file (e qui entra Git)

Dopo `uv init` + qualche `uv add` ti ritrovi con tre cose. La domanda chiave per Git è:
**cosa committo e cosa no?**

| Cosa | Committare? | Perché |
|---|---|---|
| `pyproject.toml` | ✅ **Sì** | è la "lista della spesa": quali librerie servono |
| `uv.lock` | ✅ **Sì** | fissa le versioni *esatte* → ambiente identico per tutti |
| `.venv/` | ❌ **No** | è l'ambiente vero e proprio: pesante, locale, si rigenera |

`.venv/` va nel `.gitignore` (in questa repo c'è già). Il `.venv/` **non si versiona mai**:
ognuno se lo ricrea con `uv sync`. È lì che molti principianti sbagliano, committando centinaia
di MB inutili.

> 💡 Regola da ricordare: **committi la ricetta (`pyproject.toml` + `uv.lock`), non la torta (`.venv/`)**.

---

## Il flusso completo: ricreare l'ambiente identico

Il vantaggio vero di `uv`: chiunque riceva il progetto ricrea l'ambiente *esatto* con un comando.

```bash
# 1. Ricrei l'ambiente IDENTICO a quello di chi l'ha scritto
uv sync --all-groups   # legge pyproject.toml + uv.lock e installa tutto, versioni esatte

# 2. Crei il tuo .env con le chiavi (il .env non è versionato: è gitignorato!)
cp .env.example .env
# ... incolla le tue chiavi dentro .env (vedi chiavi-api.md) ...

# 3. Fai girare uno script
uv run maf/ep02_tools_mcp/agente.py
```

Un comando (più le chiavi) e l'agente gira, con *esattamente* le stesse versioni
di chi l'ha scritto. Niente "a me non parte". Questo è il valore di committare il lockfile.

> ⚠️ Perché `--all-groups`? Le librerie per il notebook (jupyter, ipykernel) stanno in un gruppo
> `dev` separato. Un `uv sync` liscio installa solo le dipendenze principali; con `--all-groups`
> tiri dentro anche quelle di sviluppo. Serve anche dopo un `uv add`, che di suo può lasciar fuori i gruppi.

> 🔒 Il `.env` non è versionato perché è nel `.gitignore`. Per questo si distribuisce
> `.env.example` (senza valori): così sai *quali* variabili creare. Come procurarti le chiavi:
> vedi [`chiavi-api.md`](chiavi-api.md).

---

## Aggiungere una dipendenza

```bash
uv add httpx    # aggiunge la libreria e aggiorna pyproject.toml + uv.lock
```

`uv` aggiorna da solo `pyproject.toml` (la lista) e `uv.lock` (le versioni esatte). Sono i due
file da versionare: così chi fa `uv sync` ottiene la libreria in più, con la stessa versione.

---

## In sintesi

- `uv` = ambiente isolato + dipendenze riproducibili, in pochi comandi.
- Committi **`pyproject.toml` + `uv.lock`**, ignori **`.venv/`**.
- Chi riceve il progetto fa **`uv sync --all-groups`** e ha il tuo stesso ambiente.
- Aggiungere una libreria = **`uv add`**, che aggiorna `pyproject.toml` + `uv.lock` da versionare.
