# Black Onyx trust model (one page)

**Origin, not wording.** A value's provenance label decides what it may do, never what it says.

- **Trust levels:** `USER` > `VERIFIED` > `UNTRUSTED`. USER = typed by the user. UNTRUSTED = anything a tool returned
  (email, web, file, search result). VERIFIED = passed a validated declassifier.
- **Origin sources** (bitmask): `USER, CONTACTS, PAYEE_LIST, DOC_INDEX, EMAIL, WEB, FILE, TOOL_OTHER`.
- **Propagation:** every operation (concat, slice, split, join, format, decode, extract, summarise) returns a
  `LabeledObject` whose sources are the OR of its inputs and whose trust is the lowest input trust. In strict
  mode `str()`, f-strings and `%` raise, so a label cannot be dropped by accident.
- **Control vs data arguments:** control arguments choose where something goes or what runs (recipient, account,
  path, URL, attendees). Data arguments are payload (body, subject, notes). Untrusted data may fill data
  arguments, never control arguments. This is the main overblocking defence.
- **Fixed plan:** the call sequence is produced from the user's request alone, before any tool runs. Injected
  text cannot add, remove or reorder calls. Any call outside the plan is denied with an alert.
- **Validated declassifiers** (the only way trust goes up): `payee_lookup`, `contact_lookup`, `doc_resolve`,
  `amount_check`, `mailbox_ref`. Each is a small deterministic function that returns data from a trusted table
  and logs one event. The attacker can at most pick among legitimate table entries.
- **Policy** (`policy/policy.yaml`): per tool, per argument, which origins and minimum trust are allowed.
  Anything not in the policy is denied.
- **Laya sentinel:** a local model scores whether a call fits the user's task. It writes a score and may raise a
  warning on an allowed call. It never relaxes a rule denial.

```
user request -> planner (fixed plan) -> interpreter -> policy gate -> mock tools
                                            ^   |            |
                                  declassifiers  label wrapper + transforms (labels = union of inputs)
                                            audit log (JSONL) -> live graph, alerts, report
```

**Guarantee claimed:** untrusted data cannot choose a destination or an argument the policy reserves for USER or
VERIFIED data, provided the orchestrator, policy file, validators and tool registry are correct (the trusted
computing base).

**Not claimed:** a poisoned page cannot make a summary's wording misleading (such summaries stay labelled untrusted);
protection against implicit flows (branching on tainted data); that Laya is accurate on its own; that the simulated
attacker-following agent is a real LLM (it models a compliant one).
