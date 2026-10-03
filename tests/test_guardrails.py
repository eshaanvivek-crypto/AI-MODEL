from app.guardrails import is_safe_url


def test_safe_url_allows_https():
    assert is_safe_url("https://example.com/path")


def test_safe_url_blocks_localhost_and_private_networks():
    assert not is_safe_url("http://localhost:8000")
    assert not is_safe_url("http://127.0.0.1/admin")
    assert not is_safe_url("http://192.168.1.10/secret")


def test_safe_url_blocks_non_http_schemes():
    assert not is_safe_url("file:///etc/passwd")
    assert not is_safe_url("javascript:alert(1)")
