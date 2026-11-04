import asyncio

import pytest

from src.services.browser.control import ControlError, PageController, _check_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("example.com", "https://example.com"),
        ("http://a.vn/x", "http://a.vn/x"),
        ("about:blank", "about:blank"),
        ("localhost:8080/x", "https://localhost:8080/x"),
    ],
)
def test_allowed_urls(url, expected):
    assert _check_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "file:///C:/Windows/win.ini",
        "view-source:https://a.com",
        "javascript:alert(1)",
        "chrome://x",
        "about:config",
        "about:logins",
        "data:text/html,<script>alert(1)</script>",
    ],
)
def test_blocked_urls(url):
    with pytest.raises(ControlError):
        _check_url(url)


class FakePage:
    def __init__(self, url="about:blank"):
        self.url = url
        self.closed = False

    def is_closed(self):
        return self.closed

    async def title(self):
        return "T"

    async def goto(self, url, wait_until="load"):
        self.url = url

    async def close(self):
        self.closed = True

    async def bring_to_front(self):
        pass


class FakeContext:
    def __init__(self, n=1):
        self.pages = [FakePage(f"https://p{i}.test/") for i in range(n)]

    async def new_page(self):
        page = FakePage()
        self.pages.append(page)
        return page


def run(coro):
    return asyncio.run(coro)


def test_dispatch_rejects_unknown_action_and_bad_params():
    c = PageController(FakeContext())
    with pytest.raises(ControlError, match="Unknown action"):
        run(c.dispatch("rm_rf", {}))
    with pytest.raises(ControlError, match="Invalid parameters"):
        run(c.dispatch("navigate", {"nope": 1}))


def test_navigate_uses_active_tab():
    ctx = FakeContext(2)
    c = PageController(ctx)
    result = run(c.dispatch("navigate", {"url": "example.com"}))
    assert result == {"url": "https://example.com", "title": "T"}
    assert ctx.pages[-1].url == "https://example.com"


def test_tabs_select_and_close():
    ctx = FakeContext(2)
    c = PageController(ctx)
    tabs = run(c.dispatch("tab_select", {"index": 0}))["tabs"]
    assert [t["active"] for t in tabs] == [True, False]
    tabs = run(c.dispatch("tab_close", {"index": 0}))["tabs"]
    assert [t["url"] for t in tabs] == ["https://p1.test/"]
    with pytest.raises(ControlError, match="last tab"):
        run(c.dispatch("tab_close", {"index": 0}))
    with pytest.raises(ControlError, match="No tab"):
        run(c.dispatch("tab_select", {"index": 5}))


def test_tab_param_targets_a_tab_without_selecting_it():
    ctx = FakeContext(3)
    c = PageController(ctx)
    run(c.dispatch("tab_select", {"index": 2}))
    # URL match ignores the trailing slash, query and fragment
    run(c.dispatch("navigate", {"url": "a.test", "tab": "https://p0.test?x=1#y"}))
    run(c.dispatch("navigate", {"url": "b.test", "tab": 1}))
    run(c.dispatch("navigate", {"url": "c.test", "tab": None}))
    assert [p.url for p in ctx.pages] == ["https://a.test", "https://b.test", "https://c.test"]
    tabs = run(c.dispatch("tabs", {"tab": 0}))["tabs"]
    assert [t["active"] for t in tabs] == [False, False, True]
    with pytest.raises(ControlError, match="No tab with URL"):
        run(c.dispatch("navigate", {"url": "a.test", "tab": "https://nope.test/"}))
    with pytest.raises(ControlError, match="No tab at index"):
        run(c.dispatch("navigate", {"url": "a.test", "tab": "7"}))


def test_tab_param_is_per_request():
    ctx = FakeContext(2)
    c = PageController(ctx)

    async def both():
        await asyncio.gather(
            c.dispatch("navigate", {"url": "a.test", "tab": 0}),
            c.dispatch("navigate", {"url": "b.test"}),
        )

    run(both())
    assert [p.url for p in ctx.pages] == ["https://a.test", "https://b.test"]


# ---------------------------------------------------------------------------
# Percent-encoded scheme bypass (fix 3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "%66ile:///C:/Windows/win.ini",  # decodes to file:///...
        "java%73cript:alert(1)",  # decodes to javascript:...
        "%76iew-source:https://a.com",  # decodes to view-source:...
    ],
)
def test_percent_encoded_blocked_schemes(url):
    """Percent-encoded disallowed schemes must be caught before scheme detection."""
    with pytest.raises(ControlError):
        _check_url(url)


@pytest.mark.parametrize("url", ["[", "[]", "[::1", "http://[::1"])
def test_malformed_url_is_a_control_error(url):
    with pytest.raises(ControlError):
        _check_url(url)


def test_upload_disabled_without_allowed_dirs(monkeypatch, tmp_path):
    from src.services.browser.control import UPLOAD_DIRS_ENV, _check_upload_files

    monkeypatch.delenv(UPLOAD_DIRS_ENV, raising=False)
    f = tmp_path / "a.txt"
    f.write_text("x")
    with pytest.raises(ControlError, match="disabled"):
        _check_upload_files([str(f)])


def test_upload_only_inside_allowed_dirs(monkeypatch, tmp_path):
    from src.services.browser.control import UPLOAD_DIRS_ENV, _check_upload_files

    allowed = tmp_path / "ok"
    allowed.mkdir()
    inside = allowed / "a.txt"
    inside.write_text("x")
    outside = tmp_path / "b.txt"
    outside.write_text("x")
    monkeypatch.setenv(UPLOAD_DIRS_ENV, str(allowed))
    assert _check_upload_files([str(inside)]) == [str(inside.resolve())]
    with pytest.raises(ControlError, match="outside"):
        _check_upload_files([str(outside)])
    with pytest.raises(ControlError, match="outside"):
        _check_upload_files([str(allowed / ".." / "b.txt")])
    with pytest.raises(ControlError, match="Not a file"):
        _check_upload_files([str(allowed)])
