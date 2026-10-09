"""Middleware: quello che sta in mezzo tra l'agente, i suoi strumenti e il framework.

`log_step` intercetta ogni chiamata a tool e la stampa: nome, argomenti, risultato.
Nasce come aiuto didattico (a schermo si vede che l'agente sta davvero lavorando) ma e'
la stessa presa in cui, in produzione, infili logging strutturato, metriche e guardrail.
In EP 5 diventa il posto dove si mette il freno.

`turno_di_fila` protegge da un difetto della group chat di MAF (vedi la sua docstring).
"""

from agent_framework import Message, agent_middleware, function_middleware

PROMEMORIA_TURNO = (
    "Il Moderatore ti ha dato di nuovo la parola: prosegui dal tuo intervento precedente, "
    "senza ripeterlo."
)


@agent_middleware
async def turno_di_fila(context, call_next):
    """Se un partecipante riceve la parola senza nessun messaggio, gliene da' uno.

    Il difetto, in agent-framework-orchestrations 1.3.0 (verificato sul sorgente e
    riprodotto forzando l'ordine dei turni): dopo un intervento l'orchestratore manda la
    conversazione a tutti **tranne** a chi ha appena parlato, e chi ha parlato svuota la
    propria cache. Se l'orchestratore gli ridà subito la parola, l'agente parte con zero
    messaggi e OpenAI rifiuta la richiesta ("Messages are required"). Il dibattito si rompe
    a caso, perche' dipende da una scelta del Moderatore: nelle prove, 2 run su 8.

    Il contesto non va perso: la sessione dell'agente conserva i suoi turni, quindi basta
    un promemoria per riprendere il filo (provato: al secondo turno di fila Fan e Critico
    proseguono la propria tesi). Tocca solo il caso a zero messaggi, il resto passa intatto.
    """
    if not context.messages:
        context.messages.append(Message(role="user", contents=[PROMEMORIA_TURNO]))
    await call_next()


def _testo_result(res) -> str:
    """Il risultato di un tool arriva come Content (o lista di Content), non come str:
    ne estraiamo il testo (text/result/output)."""
    if res is None:
        return ""
    if isinstance(res, str):
        return res
    parti = []
    for it in res if isinstance(res, (list, tuple)) else [res]:
        for attr in ("text", "result", "output"):
            v = getattr(it, attr, None)
            if isinstance(v, str) and v:
                parti.append(v)
                break
        else:
            parti.append(str(it))
    return " ".join(parti)


@function_middleware
async def log_step(context, call_next):
    """Intercetta ogni chiamata a tool: nome + argomenti prima, risultato (troncato) dopo."""
    args = context.arguments
    if hasattr(args, "model_dump"):
        args = args.model_dump()
    print(f"  -> {context.function.name}({args})", flush=True)
    await call_next()
    res = _testo_result(context.result)
    print(f"  <- {context.function.name}: {res[:140]}{'...' if len(res) > 140 else ''}\n", flush=True)
