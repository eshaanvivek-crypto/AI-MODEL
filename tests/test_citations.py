from datetime import datetime, timezone

from app.citations import deterministic_report, validate_citations
from app.schemas import SourceMetadata


def _source(idx: int) -> SourceMetadata:
    return SourceMetadata(
        id=idx,
        title=f"Source {idx}",
        url=f"https://example.com/{idx}",
        publisher="example.com",
        retrieved_at=datetime.now(timezone.utc),
        snippet="snippet",
    )


def test_validate_citations_accepts_valid_markers():
    ok, err = validate_citations("Claim one [1]\nClaim two [2]", [_source(1), _source(2)])
    assert ok
    assert err is None


def test_validate_citations_rejects_unknown_marker():
    ok, err = validate_citations("Bad citation [3]", [_source(1), _source(2)])
    assert not ok
    assert "does not map" in err


def test_deterministic_report_contains_uncertainty_when_set():
    report = deterministic_report("Q", ["evidence [1]"], uncertainty="Low confidence")
    assert "Low confidence" in report
