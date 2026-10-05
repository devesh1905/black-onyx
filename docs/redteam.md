# Red-team pass (5 Oct, after the feature freeze)

Goal: try to get past the rules with hand-written injections and by attacking the policy and the guard adapter directly.
Reproduce with `python -m eval.redteam` (battery) and `pytest tests/test_guard.py tests/test_policy.py`.

## Battery (17 injections x 9 tasks = 153 runs, D2)

Fake system messages, claimed user consent, look-alike contacts, `cc` plus attachment, split or upper-cased addresses,
URLs with secrets, a `user@host` URL trick, a wire-transfer correction, calendar invites, write-file and reply-to-other-mail
requests, and Hinglish or all-caps pressure. In the 104 runs where the simulated attacker acted (the undefended D0 agent
did something harmful), **D2 let 0 through**. In the other 49 runs even D0 did nothing, because the simulated attacker's
directive parser could not read the text; those say nothing about the defence.

## Findings and fixes

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Guard adapter: an argument that was only a **substring** of the user's request inherited USER trust, so `priya@corp.co` (or `priya@corp`) passed when the user wrote `priya@corp.com`. | High (real bypass for guarded real agents) | Fixed: whole-token match, tests added |
| 2 | Guard adapter: short legitimate values such as an amount of `50` were never trusted (3-character minimum), so a normal payment was blocked. | Medium (over-blocking) | Fixed with the same whole-token rule |
| 3 | `web_fetch`: an untrusted URL on an allow-listed host with a `#fragment` or `;params` was accepted (only the query string was rejected). | Low | Fixed: tests cover `@`-host, look-alike host, port and fragment tricks |
| 4 | An untrusted URL on an allow-listed host can still carry data **in its path**. | Low, by design | Documented: allow-list only hosts you control |
| 5 | `contact_lookup` matches by name or address fragments, so an attacker string can only ever be mapped to a real contact (never to the attacker's own address). | Low | Documented: worst case is misrouting among genuine contacts |

Not covered: implicit flows, misleading summary wording, and anything an LLM does without calling a tool.
