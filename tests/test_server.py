import time


def test_server_imports_quickly():
    start = time.monotonic()
    import canvas_mcp.server  # noqa: F401
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, f"Server import took {elapsed:.2f}s — must be under 2s"
