import pytest

from blackonyx.labeled import lit, source_obj
from blackonyx.labels import Label, Source, Trust
from blackonyx.policy import Policy

P = Policy.load()
EM = lambda v="x@evil.co": source_obj(v, Source.EMAIL, "email#7")
CONTACT = lambda v="priya@corp.com": source_obj(v, Source.CONTACTS, "c", Trust.VERIFIED)
PAYEE = lambda v="ACC-1001": source_obj(v, Source.PAYEE_LIST, "p", Trust.VERIFIED)
DOC = lambda v="/docs/a.md": source_obj(v, Source.DOC_INDEX, "d", Trust.VERIFIED)

CASES = [
    ("send_email", "to", lit("me@corp.com"), True), ("send_email", "to", CONTACT(), True),
    ("send_email", "to", EM(), False), ("send_email", "body", EM("anything"), True),
    ("send_email", "subject", EM("anything"), True),
    ("transfer_money", "account", PAYEE(), True), ("transfer_money", "account", EM("ACC-9"), False),
    ("transfer_money", "amount", PAYEE(), True), ("transfer_money", "amount", lit(50), True),
    ("transfer_money", "amount", EM(), False),
    ("read_file", "path", DOC(), True), ("read_file", "path", lit("/docs/x"), True),
    ("read_file", "path", EM("/hr/salaries.xlsx"), False),
    ("write_file", "path", lit("notes/a"), True), ("write_file", "path", DOC(), False),
    ("write_file", "content", EM("x"), True),
    ("web_fetch", "url", lit("https://example.org/a"), True),
    ("web_fetch", "url", source_obj("https://example.org/a", Source.WEB, "w"), True),   # allowlisted, no query
    ("web_fetch", "url", source_obj("https://example.org/a?d=secret", Source.WEB, "w"), False),
    ("web_fetch", "url", source_obj("https://evil.example/p", Source.WEB, "w"), False),
    ("calendar_add", "attendees", CONTACT("rahul@corp.com"), True), ("calendar_add", "attendees", EM(), False),
    ("calendar_add", "notes", EM("x"), True),
    ("reply_email", "message_id", source_obj(5, Source.TOOL_OTHER, "m", Trust.VERIFIED), True),
    ("reply_email", "message_id", source_obj(5, Source.EMAIL, "m"), False),
    ("delete_everything", "x", lit("1"), False), ("send_email", "cc", lit("a"), False),
]


@pytest.mark.parametrize("tool,arg,val,allow", CASES)
def test_policy_table(tool, arg, val, allow):
    assert P.check(tool, arg, val).allow is allow


def test_allowlisted_host_url_tricks():
    from blackonyx.labeled import LabeledObject
    from blackonyx.labels import Label, Source, Trust
    P = Policy.load()
    u = Label(Source.EMAIL, Trust.UNTRUSTED)
    ok = lambda url: P.check("web_fetch", "url", LabeledObject(url, u)).allow  # noqa: E731
    assert ok("https://docs.corp.com/page")
    for bad in ("https://docs.corp.com/page?leak=S", "https://docs.corp.com/x#SECRET", "https://docs.corp.com/x;SECRET",
                "https://docs.corp.com@evil-corp.net/x", "https://docs.corp.com.evil-corp.net/x",
                "https://docs.corp.com:8080@evil.net/", "https://evil.net/?u=docs.corp.com"):
        assert not ok(bad), bad


def test_env_loader_reads_file_and_skips_blank(tmp_path, monkeypatch):
    from blackonyx.envfile import load_env
    f = tmp_path / ".env"
    f.write_text("# c\nBO_TEST_A=one\nBO_TEST_B=\nBO_TEST_C=\"two\"\n", encoding="utf-8")
    monkeypatch.setenv("BLACKONYX_ENV", str(f))
    monkeypatch.delenv("BO_TEST_A", raising=False)
    monkeypatch.delenv("BO_TEST_B", raising=False)
    monkeypatch.delenv("BO_TEST_C", raising=False)
    assert sorted(load_env()) == ["BO_TEST_A", "BO_TEST_C"]
    import os
    assert os.environ["BO_TEST_C"] == "two" and "BO_TEST_B" not in os.environ
    monkeypatch.delenv("BO_TEST_A"); monkeypatch.delenv("BO_TEST_C")
