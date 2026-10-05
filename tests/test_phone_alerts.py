from app.phone_alerts import alert_messages, MAX_PER_RUN


def test_alert_messages_generic_and_deduped():
    a = {"type": "alert", "tool": "send_email", "chain": "to <- extract_email(email#6) <- EMAIL, UNTRUSTED", "reason": "x@evil.net"}
    b = {"type": "alert", "tool": "read_file", "chain": "path <- email#7 <- EMAIL, UNTRUSTED", "reason": "r"}
    msgs = alert_messages([{"type": "tool_result"}, a, a, b])
    assert len(msgs) == 2 <= MAX_PER_RUN
    assert msgs[0][0] == "Black Onyx blocked send_email"
    assert "evil" not in msgs[0][1] and "email untrusted" in msgs[0][1]
    assert alert_messages([{"type": "tool_result"}]) == []
