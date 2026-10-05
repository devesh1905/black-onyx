from app.phone_alerts import alert_messages, MAX_PER_RUN


def test_alert_messages_only_tool_and_reason():
    ev = [{"type": "tool_result"}, {"type": "alert", "tool": "send_email", "reason": "recipient is untrusted\nsecret@evil.net"}] * 5
    msgs = alert_messages(ev)
    assert len(msgs) == MAX_PER_RUN
    assert msgs[0][1] == "Blocked send_email: recipient is untrusted"
    assert alert_messages([{"type": "tool_result"}]) == []
