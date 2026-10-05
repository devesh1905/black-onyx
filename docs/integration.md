# Using Black Onyx with an existing agent

Black Onyx's engine labels values itself because it runs the plan. For an existing tool-calling agent you only
have strings, so `blackonyx.guard.Guard` recovers provenance at the boundary and applies the same YAML policy.

```python
from blackonyx.guard import Guard
from blackonyx.labels import Source

guard = Guard(user_request=user_text, trusted={Source.CONTACTS: set(contact_addresses)})
guard.register("read_inbox", read_inbox, result_source=Source.EMAIL)   # what it returns is untrusted EMAIL text
guard.register("send_email", send_email)

# in your loop, replace  result = tools[name](**args)  with:
res = guard.call(name, **args)
messages.append(tool_message(res.for_model()))     # a refusal the model can read, or the real output
```

How each argument is labelled: appears in the user's request -> USER; entry of a trusted table -> VERIFIED;
appears in earlier tool output -> UNTRUSTED with that tool's source; anything else -> UNTRUSTED (the model invented it).
The policy file is `policy/policy.yaml` (per tool, per argument). Decisions are written to the audit log when one
is active (`with Audit(path): ...`), so the same UI can replay them.

Runnable example (no network, a stand-in model that obeys injected text): `python examples/guarded_agent.py`.

## Where the call goes in a real client (pattern, not run against a live API here)

- OpenAI-style: after `response.choices[0].message.tool_calls`, call `guard.call(tc.function.name, **json.loads(tc.function.arguments))`
  and return `res.for_model()` as the `tool` message.
- Anthropic-style: for each `tool_use` block, call `guard.call(block.name, **block.input)` and return `res.for_model()` in the `tool_result`.

## Honest limits

Substring matching can be fooled if the model rewrites a value (for example re-spelling an address), which is why the
default for unknown values is UNTRUSTED and the call is refused rather than allowed. The engine's `LabeledObject` path
is the stronger mechanism; the guard is the pragmatic bridge. A proxy for MCP servers would follow the same idea.
