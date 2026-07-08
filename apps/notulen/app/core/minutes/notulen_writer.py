"""Claude API call that turns a transcript into meeting notulen (minutes).

Output language comes from ``MINUTES_LANGUAGE`` (ISO 639-1 code, default
``nl`` — Dutch). Loads the notulen template once (lazy) and prompts
Claude with strict invul-rules so the output is always parsable
downstream. Does NOT
own the AI-call bookkeeping — ``dashkit.ai.call_claude`` logs tokens/cost
to ``notulen_ai_calls``.

Twin declaration: ``apps/notulen/entrypoints/worker.py``
carries its own prompt + template loader by design (self-contained GPU
image, module-standard §2.2 twin rule).

FAILURE POLICY: Tier-1 — a Claude error raises ``RuntimeError``;
``process_job`` marks the job ``failed``.
"""
from __future__ import annotations

import os

from dashkit.ai import call_claude

from apps.notulen.app.core.publish.github.target_path import target_path
from apps.notulen.app.shared.config import TEMPLATE_PATH

_NOTULEN_TEMPLATE: str = ""


def _load_template() -> str:
    global _NOTULEN_TEMPLATE
    if not _NOTULEN_TEMPLATE:
        if TEMPLATE_PATH.exists():
            _NOTULEN_TEMPLATE = TEMPLATE_PATH.read_text(encoding="utf-8")
        else:
            # Fallback: hardcoded template
            _NOTULEN_TEMPLATE = (
                "# Meeting: [onderwerp]\n\n"
                "**Datum**: YYYY-MM-DD\n"
                "**Aanwezig**:\n"
                "**Notulist**:\n\n"
                "## Agenda\n\n1. ...\n\n"
                "## Besproken\n\n### Punt 1\n-\n\n"
                "## Actiepunten\n\n"
                "| Actie | Wie | Deadline |\n|---|---|---|\n| | | |\n\n"
                "## Volgende meeting\n\n"
                "**Datum**:\n**Onderwerpen**:\n"
            )
    return _NOTULEN_TEMPLATE


def generate_notulen(
    transcript: str,
    title: str,
    meeting_date: str,
    attendees: list[str],
    job_id: str,
    agenda: str = "",
) -> str:
    """Call Claude to structure the transcript into Dutch notulen markdown."""
    template = _load_template()

    agenda_block = ""
    if agenda.strip():
        agenda_block = f"""
AGENDA (vooraf opgegeven door de gebruiker):
{agenda.strip()}

Gebruik deze agenda als structuur voor de "Besproken" sectie. Als er onderwerpen
besproken zijn die niet op de agenda stonden, voeg ze toe als extra punt."""

    # Output language for the minutes (ISO 639-1 code; read at call time).
    minutes_language = os.environ.get("MINUTES_LANGUAGE", "nl")

    system_prompt = f"""Je bent een professionele notulist.

Maak notulen van de vergadering op basis van het transcript. Het transcript bevat
timestamps [MM:SS] en spreker-labels [SPEAKER_00], [SPEAKER_01] etc. per blok.
Verschillende labels = verschillende personen. Pauzes tussen blokken markeren
onderwerpwisselingen.

AANWEZIGEN: {", ".join(attendees)}
Koppel de spreker-labels aan de aanwezigen op basis van context (wie zegt wat,
wie wordt aangesproken). Als de koppeling onduidelijk is, gebruik dan het label
zelf (bijv. "Spreker 1"). Als er geen spreker-labels in het transcript staan,
probeer dan uit context af te leiden wie wat zegt.

TEMPLATE:
{template}
{agenda_block}
INVULREGELS:
- Onderwerp: "{title}"
- Datum: {meeting_date}
- Aanwezig: {", ".join(attendees)}
- Notulist: "Automatisch (Whisper + Claude)"
- Schrijf de notulen in de taal met taalcode "{minutes_language}" ("nl" = Nederlands)
- "Besproken": maak een subsectie (### Punt N: titel) per besproken onderwerp.
  Per punt: 2-5 bondige bullets met de kern van wat er gezegd is.
  Noem wie iets zei of voorstelde als dat uit het transcript blijkt.
- "Besluiten": lijst alleen expliciete besluiten op die tijdens de vergadering
  zijn genomen (bijv. "We gaan X doen", "Besloten om Y"). Als er geen expliciete
  besluiten zijn, schrijf "Geen expliciete besluiten genomen."
- "Actiepunten": vul de tabel. Elke concrete taak of toezegging apart.
  Wie: naam van de persoon, of "Allen" / "Nader te bepalen".
  Deadline: alleen als expliciet een datum of termijn is genoemd, anders leeg.
- "Volgende meeting": alleen invullen als dit expliciet besproken is.
- Sla small talk, herhalingen, en niet-inhoudelijke opmerkingen over.
- Geef ALLEEN het ingevulde template terug, geen inleiding of afsluiting."""

    result = call_claude(
        system_prompt=system_prompt,
        user_prompt=f"TRANSCRIPT:\n\n{transcript}",
        ai_calls_table="notulen_ai_calls",
        run_id=job_id,
        # One path grammar (shared/slug.py via target_path): the AI-call
        # label and the committed file now agree on <YYYY-MM>_<slug>.md.
        doc_path=target_path(meeting_date, title),
    )

    if "error" in result:
        raise RuntimeError(f"Claude API error: {result.get('detail', result['error'])}")

    return result["content"]
