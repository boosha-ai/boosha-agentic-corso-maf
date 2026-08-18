"""
EP 3 - Il compagno di cinema (vetrina Gradio).

Un agente Fan con MEMORIA:
- carichi il **dossier** di un film (JSON) -> e' il contratto tra agenti: oggi lo dai
  tu, da EP 4 lo produrra' il Ricercatore in autonomia. La forma non cambia.
- chatti col Fan: ricorda dentro la conversazione (SESSIONE) e ricorda i tuoi gusti
  tra un avvio e l'altro (MEMORIA PERSISTENTE su file, il pannello "Cosa ricordo di te").

Avvio:
    uv run python agente.py        # apre l'interfaccia nel browser

Chiavi nel .env: OPENAI_API_KEY (obbligatoria). MAF non carica .env da solo -> load_dotenv().
"""
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()  # MAF non carica .env da solo

import gradio as gr
from agent_framework import Agent, ContextProvider
from agent_framework.openai import OpenAIChatClient

MODEL = "gpt-4o-mini"
QUI = Path(__file__).parent
# Gli appunti del Fan su di te (ignorato da git). File PROPRIO dell'app: il notebook usa
# profilo_gusti.txt e lo azzera a ogni run, quindi teniamo le due memorie separate.
PROFILO = QUI / "profilo_compagno.txt"
DOSSIER_DIR = QUI / "dossier"                 # dossier pronti prodotti dal Ricercatore di EP 2

FAN = (
    "Sei il Fan del Debate Club: difendi con entusiasmo i film che ami, ma resti onesto. "
    "Argomenta SOLO con i dati del dossier che ti viene dato (incassi, voti, recensioni): "
    "non inventare numeri. Se conosci i gusti dell'utente, adatta il modo in cui difendi il "
    "film a lui. Rispondi in italiano, in 2-3 frasi."
)


# ============================================================ memoria persistente (livello 2)
class ProfiloGusti(ContextProvider):
    """Ricorda i gusti cinematografici dell'utente tra una sessione e l'altra (su file)."""

    def __init__(self, path: Path):
        super().__init__("gusti")
        self.path = Path(path)

    def leggi(self) -> str:
        return self.path.read_text(encoding="utf-8").strip() if self.path.exists() else ""

    async def before_run(self, *, agent, session, context, state: dict[str, Any]) -> None:
        profilo = self.leggi()
        if profilo:
            context.extend_instructions(self.source_id, f"Profilo gusti dell'utente (dai tuoi appunti):\n{profilo}")
        else:
            # cold start: nessuna storia -> chiedi (come Netflix al primo accesso)
            context.extend_instructions(self.source_id, "Non conosci ancora i gusti cinematografici dell'utente: chiediglieli con garbo.")

    async def after_run(self, *, agent, session, context, state: dict[str, Any]) -> None:
        # estrai gusti duraturi dallo scambio e appendili al file
        scambio = "\n".join(f"{m.role}: {m.text}" for m in context.input_messages if getattr(m, "text", ""))
        risposta = context.response.text if context.response is not None else ""
        estrattore = Agent(
            client=OpenAIChatClient(model=MODEL), name="estrattore",
            instructions=("Estrai i gusti cinematografici DURATURI dell'utente (registi/generi amati o odiati). "
                          "Scrivi in italiano corretto, terza persona singolare, una riga per gusto: "
                          "'- Ama <cosa>' oppure '- Odia <cosa>'. Niente duplicati con quanto gia' noto. "
                          "Se non ce ne sono, rispondi solo 'NIENTE'."),
        )
        out = (await estrattore.run(f"Gia' noto:\n{self.leggi()}\n\nScambio:\n{scambio}\nAssistente: {risposta}")).text.strip()
        if out and "NIENTE" not in out.upper():
            self.path.write_text((self.leggi() + "\n" + out).strip(), encoding="utf-8")


# ============================================================ dossier = contratto
def dossier_to_text(d: dict) -> str:
    righe = [
        f"Titolo: {d['titolo']} ({d['anno']}) - regia di {d['regista']}",
        f"Incasso: {d['incasso']} | Rotten Tomatoes: {d['rotten_tomatoes']}",
        f"Trama: {d['descrizione']}",
        "Recensioni:",
    ]
    for r in d["recensioni"]:
        righe.append(f"  - [{r['sentiment']}] {r['fonte']}: {r['estratto']}")
    return "\n".join(righe)


def costruisci_fan(dossier: dict) -> dict:
    """Crea il Fan col dossier nelle istruzioni + una sessione nuova. Ritorna lo stato dell'app."""
    agent = Agent(
        client=OpenAIChatClient(model=MODEL), name="Fan",
        instructions=FAN + "\n\nDossier del film in discussione:\n" + dossier_to_text(dossier),
        context_providers=[ProfiloGusti(PROFILO)],
    )
    return {"agent": agent, "session": agent.create_session(), "titolo": f"{dossier['titolo']} ({dossier['anno']})"}


# libreria di dossier pronti (dal Ricercatore di EP 2)
LIBRERIA = {}
if DOSSIER_DIR.exists():
    for f in sorted(DOSSIER_DIR.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        LIBRERIA[f"{d['titolo']} ({d['anno']})"] = d


def carica_da_libreria(titolo: str):
    if not titolo:
        return None, "*Nessun dossier caricato.*"
    st = costruisci_fan(LIBRERIA[titolo])
    return st, f"Dossier in discussione: **{st['titolo']}**"


def carica_da_file(filepath):
    if not filepath:
        return None, "*Nessun dossier caricato.*"
    d = json.loads(Path(filepath).read_text(encoding="utf-8"))
    st = costruisci_fan(d)
    return st, f"Dossier in discussione: **{st['titolo']}** (caricato da te)"


# ============================================================ UI
def mostra_profilo() -> str:
    p = PROFILO.read_text(encoding="utf-8").strip() if PROFILO.exists() else ""
    return "### Cosa ricordo di te\n" + (p if p else "*Ancora niente: dimmi che film ami e che eviti.*")


def azzera_profilo():
    if PROFILO.exists():
        PROFILO.unlink()
    return mostra_profilo()


async def rispondi(messaggio, storia, stato):
    storia = storia or []
    if not messaggio:
        return storia, "", mostra_profilo()
    if not stato:
        storia = storia + [{"role": "assistant", "content": "Prima scegli o carica un dossier qui sopra."}]
        return storia, "", mostra_profilo()
    r = await stato["agent"].run(messaggio, session=stato["session"])
    storia = storia + [
        {"role": "user", "content": messaggio},
        {"role": "assistant", "content": r.text.strip()},
    ]
    return storia, "", mostra_profilo()


with gr.Blocks(title="Il compagno di cinema") as demo:
    gr.Markdown(
        "# Il compagno di cinema\n"
        "Un agente **Fan** che difende i film - e che **si ricorda di te**. "
        "Scegli (o carica) il **dossier** di un film: oggi lo dai tu, da EP 4 lo produrra' il **Ricercatore** "
        "in autonomia. La forma del contratto non cambia."
    )
    stato = gr.State(None)
    with gr.Row():
        dd = gr.Dropdown(choices=list(LIBRERIA), label="Scegli un dossier pronto", value=None)
        up = gr.File(label="...oppure carica un dossier (JSON)", file_types=[".json"])
    stato_txt = gr.Markdown("*Nessun dossier caricato.*")

    with gr.Row():
        with gr.Column(scale=3):
            chat = gr.Chatbot(label="Fan", height=380)
            msg = gr.Textbox(placeholder="Parla col Fan del film (e digli cosa ti piace)...", label="Tu")
            with gr.Row():
                invia = gr.Button("Invia", variant="primary")
                azzera = gr.Button("Dimentica cio' che sai di me")
        with gr.Column(scale=1):
            profilo = gr.Markdown(mostra_profilo())

    dd.change(carica_da_libreria, inputs=dd, outputs=[stato, stato_txt])
    up.upload(carica_da_file, inputs=up, outputs=[stato, stato_txt])
    invia.click(rispondi, inputs=[msg, chat, stato], outputs=[chat, msg, profilo])
    msg.submit(rispondi, inputs=[msg, chat, stato], outputs=[chat, msg, profilo])
    azzera.click(azzera_profilo, outputs=profilo)


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Manca OPENAI_API_KEY nel .env. Aggiungila e riprova.")
    # --share: link pubblico temporaneo (utile da remoto/SSH, dove 127.0.0.1 non e' raggiungibile dal tuo browser)
    demo.launch(share="--share" in sys.argv)
