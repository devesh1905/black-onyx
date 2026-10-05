# Event schema (contract between engine and UI)

The engine appends one JSON object per line (JSONL) to a run log. The UI and
`demo/replay.py` read ONLY this log. Every event has:

| field | type | meaning |
|---|---|---|
| `seq` | int | 1,2,3... in order |
| `ts` | float | seconds since run start |
| `type` | str | one of the types below |

`trust` is one of `"USER"`, `"VERIFIED"`, `"UNTRUSTED"`.
`sources` is a list of names from `USER, CONTACTS, PAYEE_LIST, DOC_INDEX, EMAIL, WEB, FILE, TOOL_OTHER`.
Value ids look like `v1`, `v2`; call ids look like `c1`, `c2`.

| type | extra fields | graph effect |
|---|---|---|
| `request` | `text`, `defence` ("D0".."D3"), `task_id` | USER node, green |
| `plan` | `steps`: list of `{call_id, tool, desc}` | grey planned-call nodes |
| `tool_result` | `call_id`, `tool`, `value_id`, `sources`, `trust`, `preview` (<=80 chars) | value node coloured by trust |
| `op` | `op`, `inputs`: [value_id], `output`: value_id, `sources`, `trust`, `preview` | edges inputs -> output |
| `declassify` | `validator`, `input`, `output`, `rule`, `sources`, `trust`, `preview` | edge into blue VERIFIED node |
| `call_check` | `call_id`, `tool`, `argument`, `value_id`, `decision` ("allow"/"deny"), `reason`, `sources`, `trust` | edge value -> call node |
| `laya_score` | `call_id`, `score` (float or null), `ms`, `warn` (bool or null) | badge on call node |
| `alert` | `call_id`, `tool`, `chain` (string like `to <- concat(email#7, email#9) <- EMAIL, UNTRUSTED`), `reason` | RED FLASH + banner |
| `effect` | `call_id`, `kind` ("email_sent","money_moved","http_request","file_written","calendar_added","file_read"), `description` | final node |

Colours (same as slide 3): green = USER, blue = VERIFIED, orange = UNTRUSTED, red flash = blocked.
A `call_check` with decision "deny" is always followed by an `alert` for the same `call_id`.

## Engine notes (added by the engine track)
- `declassify` also carries `ok` (bool). `ok: false` means the validator rejected the input; `output` is then the
  input value id and `trust` stays `UNTRUSTED` (no edge to a blue node; show it grey/orange with a "rejected" tag).
- Out-of-plan calls get call ids `x1, x2...` (planned ones are `c1, c2...`). They always produce a `call_check`
  with decision `deny` and an `alert`.
- A `request` event is emitted once per task; an attack like A6 runs two tasks in one log (two `request` events).
- `blackonyx.runner.run_scenario(task_id, attack_id, defence, injected_text=None)` returns the event list. When
  `attack_id` is set, the attack's own host task is run (A1/A2/A8/A9 on L1, A3 on L5, A4 on L4, A5 on L8,
  A6 on L5 then L9, A7 on L2, A10 on L3) and `task_id` is ignored. `injected_text` is added as a new unread email.
- `effect` also carries `leak` (bool): true when the effect is a sensitive, attacker-benefiting action (external
  email, money to a non-payee account, HTTP to a non-allowlisted host, read of a sensitive file, external attendee).
  Use it to show the HIJACKED banner.
- The log ends with a `summary` event: `{task_id, attack_id, defence, task_ok, leaked, alerts, gate_ms}`. Use it for
  the scoreboard (task finished, leaks, alerts, rule-check time).

- `note` (`level`, `text`): a plain-language hint from the engine, for example when pasted text caused no action because the simulated agent found no instruction it understands.
