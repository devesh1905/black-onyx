"""PyVis dataflow & policy graph generator for Black Onyx.

Renders an interactive graph showing:
- Green: USER nodes
- Blue: VERIFIED nodes
- Orange: UNTRUSTED nodes
- Grey: Planned / tool-call nodes
- Red: Blocked call nodes (flashing red via injected offline JavaScript)

Fully offline: Vis.js is inlined, external bootstrap CDN tags are stripped.
"""
from __future__ import annotations

import json
import re
from typing import Any, List, Optional
from pyvis.network import Network


# Trust and node color palette
COLOR_USER = "#22c55e"       # Green
COLOR_VERIFIED = "#3b82f6"   # Blue
COLOR_UNTRUSTED = "#f97316"  # Orange
COLOR_CALL = "#64748b"       # Grey
COLOR_BLOCKED = "#ef4444"    # Red
COLOR_EFFECT = "#8b5cf6"     # Purple
COLOR_BG = "#0f172a"         # Slate 900 dark background
COLOR_TEXT = "#f8fafc"       # Slate 50


def events_to_html(events: Optional[List[dict[str, Any]]] = None) -> str:
    """Build an offline PyVis network graph HTML from an event list.

    Args:
        events: List of event dicts conforming to docs/event-schema.md.

    Returns:
        Stand-alone HTML string containing inlined vis-network and flashing blocked nodes.
    """
    if not events:
        return (
            '<div style="background-color: #0f172a; color: #94a3b8; height: 600px; '
            'display: flex; flex-direction: column; align-items: center; justify-content: center; '
            'font-family: ui-sans-serif, system-ui, sans-serif; border-radius: 8px; border: 1px solid #334155;">'
            '<h3 style="color: #cbd5e1; margin-bottom: 8px;">No Events Recorded</h3>'
            '<p style="margin: 0;">Select scenario options and click <b>Run</b> to inspect the dataflow graph.</p>'
            '</div>'
        )

    net = Network(
        height="640px",
        width="100%",
        bgcolor=COLOR_BG,
        font_color=COLOR_TEXT,
        directed=True,
        cdn_resources="in_line",
    )

    # Configure physics for clear, readable hierarchical or force-directed layouts
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2,
        "shadow": true,
        "font": { "face": "system-ui, -apple-system, sans-serif" }
      },
      "edges": {
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.8 } },
        "color": { "color": "#64748b", "highlight": "#38bdf8" },
        "smooth": { "type": "cubicBezier", "roundness": 0.2 },
        "font": { "size": 11, "align": "middle", "color": "#cbd5e1" }
      },
      "physics": {
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08,
          "damping": 0.4
        },
        "stabilization": { "iterations": 80 }
      }
    }
    """)

    added_nodes: set[str] = set()
    node_labels: dict[str, str] = {}
    blocked_call_ids: set[str] = set()

    def add_node_safe(
        node_id: str,
        label: str,
        color: str,
        shape: str = "box",
        size: int = 25,
        title: Optional[str] = None,
        font: Optional[dict[str, Any]] = None,
    ) -> None:
        if node_id in added_nodes:
            # Update node properties if needed
            return
        font_config = font or {"color": "#ffffff", "size": 13, "face": "monospace"}
        net.add_node(
            node_id,
            label=label,
            color=color,
            shape=shape,
            size=size,
            title=title or label.replace("\n", " "),
            font=font_config,
        )
        added_nodes.add(node_id)
        node_labels[node_id] = label

    def add_edge_safe(
        src: str,
        dst: str,
        label: Optional[str] = None,
        color: Optional[str] = None,
        dashes: bool = False,
        width: int = 1,
    ) -> None:
        if src in added_nodes and dst in added_nodes:
            edge_args: dict[str, Any] = {"dashes": dashes, "width": width}
            if label:
                edge_args["label"] = label
            if color:
                edge_args["color"] = color
            net.add_edge(src, dst, **edge_args)

    # 1. First pass: Collect alerts and blocked calls so call nodes can be colored appropriately
    for ev in events:
        ev_type = ev.get("type")
        if ev_type == "alert":
            call_id = ev.get("call_id")
            if call_id:
                blocked_call_ids.add(f"call_{call_id}")
        elif ev_type == "call_check" and ev.get("decision") == "deny":
            call_id = ev.get("call_id")
            if call_id:
                blocked_call_ids.add(f"call_{call_id}")

    # 2. Second pass: Process events in sequence
    for ev in events:
        ev_type = ev.get("type")

        if ev_type == "request":
            req_id = "node_request"
            task_id = ev.get("task_id", "REQ")
            text_preview = ev.get("text", "")
            if len(text_preview) > 35:
                text_preview = text_preview[:32] + "..."
            add_node_safe(
                req_id,
                label=f"USER REQUEST [{task_id}]\n{text_preview}",
                color=COLOR_USER,
                shape="ellipse",
                font={"color": "#052e16", "size": 14, "bold": True},
                title=f"User Request: {ev.get('text', '')}\nDefence: {ev.get('defence', '')}",
            )

        elif ev_type == "plan":
            steps = ev.get("steps", [])
            for step in steps:
                cid = step.get("call_id")
                tool = step.get("tool")
                desc = step.get("desc", "")
                call_node_id = f"call_{cid}"
                is_blocked = call_node_id in blocked_call_ids
                node_color = COLOR_BLOCKED if is_blocked else COLOR_CALL
                status_txt = "🚨 BLOCKED" if is_blocked else "tool call"

                add_node_safe(
                    call_node_id,
                    label=f"TOOL: {tool}\n({cid})\n[{status_txt}]",
                    color=node_color,
                    shape="box",
                    title=f"Plan Step {cid}: {tool}\n{desc}",
                )
                if "node_request" in added_nodes:
                    add_edge_safe("node_request", call_node_id, label="planned", dashes=True)

        elif ev_type == "tool_result":
            vid = ev.get("value_id")
            cid = ev.get("call_id")
            tool = ev.get("tool", "")
            trust = ev.get("trust", "UNTRUSTED")
            sources = ",".join(ev.get("sources", []))
            preview = ev.get("preview", "")

            val_node_id = f"val_{vid}"
            node_color = COLOR_USER if trust == "USER" else (COLOR_VERIFIED if trust == "VERIFIED" else COLOR_UNTRUSTED)
            add_node_safe(
                val_node_id,
                label=f"{vid}: [{trust}]\nsources: {sources}\n{preview[:30]}",
                color=node_color,
                shape="ellipse",
                title=f"Tool Result ({vid})\nTool: {tool}\nTrust: {trust}\nSources: {sources}\nPreview: {preview}",
            )
            call_node_id = f"call_{cid}"
            if call_node_id in added_nodes:
                add_edge_safe(call_node_id, val_node_id, label="returns", color=node_color)

        elif ev_type == "op":
            op_name = ev.get("op", "op")
            out_vid = ev.get("output")
            inputs = ev.get("inputs", [])
            trust = ev.get("trust", "UNTRUSTED")
            sources = ",".join(ev.get("sources", []))
            preview = ev.get("preview", "")

            out_node_id = f"val_{out_vid}"
            node_color = COLOR_USER if trust == "USER" else (COLOR_VERIFIED if trust == "VERIFIED" else COLOR_UNTRUSTED)
            add_node_safe(
                out_node_id,
                label=f"{out_vid}: [{trust}]\n({op_name})\n{preview[:30]}",
                color=node_color,
                shape="ellipse",
                title=f"Operation: {op_name}\nOutput: {out_vid}\nTrust: {trust}\nSources: {sources}\nPreview: {preview}",
            )
            for in_vid in inputs:
                in_node_id = f"val_{in_vid}"
                if in_node_id in added_nodes:
                    add_edge_safe(in_node_id, out_node_id, label=op_name, color=node_color)

        elif ev_type == "declassify":
            validator = ev.get("validator", "validator")
            in_val = ev.get("input")
            out_vid = ev.get("output")
            sources = ",".join(ev.get("sources", []))
            preview = ev.get("preview", "")

            out_node_id = f"val_{out_vid}"
            add_node_safe(
                out_node_id,
                label=f"{out_vid}: [VERIFIED]\n✓ {validator}\n{preview[:30]}",
                color=COLOR_VERIFIED,
                shape="ellipse",
                title=f"Declassified by {validator}\nRule: {ev.get('rule', '')}\nSources: {sources}\nPreview: {preview}",
            )
            in_node_id = f"val_{in_val}"
            if in_node_id in added_nodes:
                add_edge_safe(in_node_id, out_node_id, label=f"✓ {validator}", color=COLOR_VERIFIED, width=2)

        elif ev_type == "call_check":
            cid = ev.get("call_id")
            tool = ev.get("tool", "")
            arg = ev.get("argument", "")
            vid = ev.get("value_id")
            decision = ev.get("decision", "allow")
            reason = ev.get("reason", "")

            call_node_id = f"call_{cid}"
            is_blocked = (decision == "deny") or (call_node_id in blocked_call_ids)
            node_color = COLOR_BLOCKED if is_blocked else COLOR_CALL
            status_txt = "🚨 BLOCKED" if is_blocked else "tool call"

            # Ensure call node exists
            add_node_safe(
                call_node_id,
                label=f"TOOL: {tool}\n({cid})\n[{status_txt}]",
                color=node_color,
                shape="box",
                title=f"Tool Call: {tool} ({cid})\nDecision: {decision}\nReason: {reason}",
            )

            val_node_id = f"val_{vid}"
            if val_node_id in added_nodes:
                edge_color = COLOR_BLOCKED if decision == "deny" else "#10b981"
                edge_label = f"{arg}: DENIED" if decision == "deny" else f"{arg}: allow"
                add_edge_safe(
                    val_node_id,
                    call_node_id,
                    label=edge_label,
                    color=edge_color,
                    width=3 if decision == "deny" else 1,
                )

        elif ev_type == "laya_score":
            cid = ev.get("call_id")
            score = ev.get("score")
            ms = ev.get("ms", 0.0)
            warn = ev.get("warn", False)

            call_node_id = f"call_{cid}"
            if call_node_id in added_nodes:
                badge = f" [fit: {score:.2f}]" if score is not None else " [fit: n/a]"
                if warn:
                    badge = f" ⚠️[fit: {score:.2f}]"
                # Update node in pyvis
                for node in net.nodes:
                    if node["id"] == call_node_id:
                        node["label"] += f"\n{badge}"
                        break

        elif ev_type == "alert":
            cid = ev.get("call_id")
            tool = ev.get("tool", "")
            chain = ev.get("chain", "")
            reason = ev.get("reason", "")

            call_node_id = f"call_{cid}"
            blocked_call_ids.add(call_node_id)
            add_node_safe(
                call_node_id,
                label=f"TOOL: {tool}\n({cid})\n🚨 BLOCKED 🚨",
                color=COLOR_BLOCKED,
                shape="box",
                title=f"SECURITY ALERT\nTool: {tool}\nReason: {reason}\nChain: {chain}",
            )

        elif ev_type == "effect":
            cid = ev.get("call_id")
            kind = ev.get("kind", "effect")
            desc = ev.get("description", "")

            eff_id = f"effect_{cid}"
            add_node_safe(
                eff_id,
                label=f"EFFECT: {kind}\n{desc[:35]}",
                color=COLOR_EFFECT,
                shape="circle",
                font={"color": "#ffffff", "size": 12},
                title=f"External Effect: {kind}\n{desc}",
            )
            call_node_id = f"call_{cid}"
            if call_node_id in added_nodes:
                add_edge_safe(call_node_id, eff_id, label="produces", color="#a855f7", width=2)

    # Generate HTML string
    raw_html = net.generate_html()

    # Strip external bootstrap & cdn links & scripts injected by PyVis
    clean_html = re.sub(
        r'<link[^>]*href=["\']https?://[^"\']*["\'][^>]*>',
        '',
        raw_html,
        flags=re.IGNORECASE,
    )
    clean_html = re.sub(
        r'<script[^>]*src=["\']https?://[^"\']*["\'][^>]*>\s*</script>',
        '',
        clean_html,
        flags=re.IGNORECASE,
    )
    # Strip any node_modules relative references (vis.js is already inlined in a separate script block)
    clean_html = re.sub(
        r'<script[^>]*src=["\'][^"\']*node_modules[^"\']*["\'][^>]*>\s*</script>',
        '',
        clean_html,
        flags=re.IGNORECASE,
    )
    clean_html = re.sub(
        r'<link[^>]*href=["\'][^"\']*node_modules[^"\']*["\'][^>]*>',
        '',
        clean_html,
        flags=re.IGNORECASE,
    )


    # Inject offline flashing JavaScript for blocked nodes
    blocked_ids_list = list(blocked_call_ids)
    flash_js = f"""
    <script type="text/javascript">
    (function() {{
        var blockedIds = {json.dumps(blocked_ids_list)};
        if (!blockedIds || blockedIds.length === 0) return;

        function startFlashing() {{
            if (typeof network === "undefined" || !network || !network.body || !network.body.data) {{
                setTimeout(startFlashing, 150);
                return;
            }}
            var isBright = false;
            setInterval(function() {{
                isBright = !isBright;
                var bgColor = isBright ? "#ef4444" : "#7f1d1d";
                var borderColor = isBright ? "#fecaca" : "#ffffff";
                for (var i = 0; i < blockedIds.length; i++) {{
                    var bid = blockedIds[i];
                    var existing = network.body.data.nodes.get(bid);
                    if (existing) {{
                        network.body.data.nodes.update({{
                            id: bid,
                            color: {{
                                background: bgColor,
                                border: borderColor,
                                highlight: {{ background: bgColor, border: borderColor }}
                            }}
                        }});
                    }}
                }}
            }}, 400);
        }}

        if (document.readyState === "complete" || document.readyState === "interactive") {{
            setTimeout(startFlashing, 200);
        }} else {{
            document.addEventListener("DOMContentLoaded", function() {{
                setTimeout(startFlashing, 200);
            }});
        }}
    }})();
    </script>
    """

    if "</body>" in clean_html:
        clean_html = clean_html.replace("</body>", f"{flash_js}\n</body>")
    else:
        clean_html += flash_js

    return clean_html
