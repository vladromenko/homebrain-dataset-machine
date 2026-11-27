"""Explicit evidence limits from a project's current claims document."""
from pathlib import Path
from .adapters import approved


def paper_limits(adapter):
    docs = adapter.spec.get("docs")
    if not docs:
        return "This project has not declared an approved claims document. I cannot assess missing paper evidence."
    path = approved(Path(docs)/"CLAIMS_AND_LIMITATIONS.md",adapter.spec["approved_roots"])
    content = path.read_text()
    current = content.split("## Current study evidence",1)[-1].split("## Historical",1)[0]
    selected = ("Motor data and performance","Physical observation and collection",
                "Witness selection controls","Terminal-reveal supervision")
    rows = [line.split("|") for line in current.splitlines() if any(label in line for label in selected) and line.startswith("|")]
    limits = [f"- {row[1].strip()}: {row[3].strip()}" for row in rows if len(row)>3]
    if not limits:
        return "The claims document format changed; review its current limitations before deciding what evidence is missing. Source: "+str(path)
    return "The project's current claims table identifies these evidence limits:\n"+"\n".join(limits)+"\nThese are documented limits, not a new collection plan. Native receipts determine current physical progress. Source: "+str(path)
