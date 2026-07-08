"""The K8s Job-name grammar — promoted INTO the interface.

Callers that later need to find a Job (the notulen dashboard matching
live Jobs against its queue, operators grepping `kubectl get jobs`) must
reproduce the exact mangling the creators applied. Before this module the
rule lived inline in each creator and was duplicated verbatim in
apps/notulen/app/entrypoints/main.py — an interface fact
leaked into a caller (module-standard §8). One home heals the leak.

FAILURE POLICY: pure string mangling — nothing to swallow.
"""

from __future__ import annotations


def job_name(prefix: str, seed: str, *, seed_chars: int) -> str:
    """Mangle (prefix, seed) into the Job name the creators submit.

    Grammar: ``{prefix}-{seed[:seed_chars]}`` lowercased, trailing ``-``
    stripped (K8s DNS-1123 names reject trailing dashes). ``seed_chars``
    is keyword-only and has no default because the two production
    grammars truncate differently (batch 16, notulen 20) and a silent
    default would change live Job names.
    """
    return f"{prefix}-{seed[:seed_chars]}".lower().rstrip("-")
