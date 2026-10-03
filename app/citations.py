import re
from app.schemas import SourceMetadata

_CITATION_RE = re.compile(r"\[(\d+)\]")


def validate_citations(report: str, sources: list[SourceMetadata]) -> tuple[bool, str | None]:
    if not sources:
        return True, None

    matches = [int(m.group(1)) for m in _CITATION_RE.finditer(report)]
    if not matches:
        return False, "Report includes sources but no citation markers like [1]."

    max_id = len(sources)
    for citation_id in matches:
        if citation_id < 1 or citation_id > max_id:
            return False, f"Citation [{citation_id}] does not map to an available source."

    for source in sources:
        if not source.title or not source.url or not source.publisher:
            return False, "A source is missing required metadata (title/url/publisher)."

    return True, None


def deterministic_report(question: str, evidence_lines: list[str], uncertainty: str | None = None) -> str:
    lines = [f"Research question: {question}", "", "Key findings:"]
    if not evidence_lines:
        lines.append("- Limited evidence was available from configured sources.")
    else:
        for line in evidence_lines:
            lines.append(f"- {line}")

    if uncertainty:
        lines.extend(["", f"Uncertainty: {uncertainty}"])

    return "\n".join(lines)
