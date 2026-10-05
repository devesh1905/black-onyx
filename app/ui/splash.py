"""Full-screen Black Onyx boot splash (about 1.5 s), pure CSS. No video, no JS, no external assets.

Sequence: emblem barely visible in darkness -> scanline sweep reveals it with RGB separation ->
one brief horizontal slice glitch -> everything settles to a sharp white wordmark and tagline ->
the overlay fades into the page. prefers-reduced-motion gets a still frame and a short fade.
"""
from __future__ import annotations

import base64
import io
import mimetypes
import os
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent

BRAND_DIR = _HERE / "brand"


def _custom_image(stem: str, env: str, limit: int = 1100) -> Optional[str]:
    """Data URI of a user-supplied image (env var, or app/ui/brand/<stem>.png|webp|jpg|svg), else None."""
    cands = [Path(os.environ[env])] if os.environ.get(env) else []
    cands += [BRAND_DIR / f"{stem}.{e}" for e in ("png", "webp", "jpg", "jpeg", "svg")]
    for p in cands:
        try:
            if not p.is_file():
                continue
            if p.suffix.lower() == ".svg":
                return _uri(p.read_text(encoding="utf-8"))
            try:  # shrink big rasters so the page stays light
                from PIL import Image
                im = Image.open(p)
                im.thumbnail((limit, limit))
                buf = io.BytesIO()
                im.save(buf, "PNG", optimize=True)
                return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
            except Exception:
                mime = mimetypes.guess_type(str(p))[0] or "image/png"
                return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")
        except OSError:
            continue
    return None


def custom_emblem() -> Optional[str]:
    """Splash emblem override: app/ui/brand/emblem.* or env BLACKONYX_EMBLEM."""
    return _custom_image("emblem", "BLACKONYX_EMBLEM")


def custom_logo() -> Optional[str]:
    """Home-screen (sidebar) logo override: app/ui/brand/logo.* or env BLACKONYX_LOGO."""
    return _custom_image("logo", "BLACKONYX_LOGO", limit=256)


CH = {  # colour-matrix rows that keep one channel only (screen-blending the three rebuilds the original)
    "r": "1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0",
    "g": "0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0",
    "b": "0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0",
}


def _uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _mark_variants() -> dict[str, str]:
    src = (_HERE / "logo_mark.svg").read_text(encoding="utf-8")
    inner = src[src.index(">") + 1: src.rindex("</svg>")]
    out = {"base": _uri(src)}
    for k, m in CH.items():
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120"><defs><filter id="ch" color-interpolation-filters="sRGB">'
               f'<feColorMatrix type="matrix" values="{m}"/></filter></defs><g filter="url(#ch)">{inner}</g></svg>')
        out[k] = _uri(svg)
    return out


def _word_variants() -> dict[str, str]:
    def svg(fill: str, flt: str = "") -> str:
        defs = f'<defs><filter id="ch" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="{flt}"/></filter></defs>' if flt else ""
        g = ' filter="url(#ch)"' if flt else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 84">{defs}<g{g}>'
                f'<text x="320" y="62" text-anchor="middle" font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif" '
                f'font-size="60" font-weight="800" letter-spacing="15" fill="{fill}">BLACK ONYX</text></g></svg>')
    out = {"base": _uri(svg("#FFFFFF"))}
    for k, m in CH.items():
        out[k] = _uri(svg("#FFFFFF", m))
    return out


CSS_CUSTOM = """
.bo-img{position:relative;width:min(70vw,640px);max-height:64vh}
.bo-img img{display:block;width:100%;height:auto;max-height:64vh;object-fit:contain;opacity:.07;clip-path:inset(0 0 100% 0);
  animation:bo-reveal .5s cubic-bezier(.3,0,.2,1) .10s forwards,bo-glow .3s linear .10s forwards,bo-split-img .7s cubic-bezier(.2,.7,.2,1) .10s forwards}
.bo-img .bo-slice2{position:absolute;inset:0;clip-path:inset(36% 0 46% 0);opacity:0;animation:bo-slice .16s steps(1,end) .56s forwards}
.bo-img .bo-slice2 img{opacity:1;clip-path:none;animation:none;filter:none}
@keyframes bo-split-img{0%{filter:drop-shadow(-6px 0 0 rgba(255,40,40,.55)) drop-shadow(6px 0 0 rgba(60,140,255,.55))}60%{filter:drop-shadow(-2px 0 0 rgba(255,40,40,.35)) drop-shadow(2px 0 0 rgba(60,140,255,.35))}100%{filter:none}}
@media (prefers-reduced-motion:reduce){.bo-img img{opacity:1!important;clip-path:none!important;filter:none!important}.bo-slice2{display:none!important}}
"""

CSS = """
.bo-splash{position:fixed;inset:0;z-index:2147483000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px;
  background:radial-gradient(ellipse at 50% 46%,#0b0f16 0%,#05070b 62%,#020305 100%);color:#fff;overflow:hidden;
  animation:bo-out .36s ease-in @OUT@s forwards;font-family:Inter,'Segoe UI',system-ui,sans-serif}
.bo-splash *{box-sizing:border-box}
.bo-stack{position:relative}
.bo-stack img{position:absolute;inset:0;width:100%;height:100%;display:block;object-fit:contain;pointer-events:none}
.bo-mark{width:150px;height:150px}
.bo-word{width:min(78vw,520px);aspect-ratio:640/84}
.bo-ch{mix-blend-mode:screen;will-change:transform,clip-path,opacity}
.bo-base{opacity:0}
/* emblem: faint in the dark, scan reveal, split settles, one slice glitch */
.bo-mark .bo-ch{opacity:.07;clip-path:inset(0 0 100% 0);animation:bo-reveal .42s cubic-bezier(.3,0,.2,1) .10s forwards,bo-glow .2s linear .10s forwards}
.bo-mark .r{animation-name:bo-reveal,bo-glow,bo-split-r;animation-duration:.42s,.2s,.62s;animation-delay:.10s,.10s,.10s;animation-fill-mode:forwards;animation-timing-function:cubic-bezier(.3,0,.2,1),linear,cubic-bezier(.2,.7,.2,1)}
.bo-mark .b{animation-name:bo-reveal,bo-glow,bo-split-b;animation-duration:.42s,.2s,.62s;animation-delay:.10s,.10s,.10s;animation-fill-mode:forwards;animation-timing-function:cubic-bezier(.3,0,.2,1),linear,cubic-bezier(.2,.7,.2,1)}
.bo-mark .bo-base{animation:bo-base .08s linear .74s forwards}
.bo-slice{position:absolute;inset:0;clip-path:inset(34% 0 50% 0);opacity:0;animation:bo-slice .16s steps(1,end) .52s forwards;mix-blend-mode:screen}
.bo-slice img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}
/* wordmark */
.bo-word .bo-ch{opacity:0;clip-path:inset(0 0 100% 0);animation:bo-reveal .26s cubic-bezier(.3,0,.2,1) .70s forwards,bo-on .01s linear .70s forwards}
.bo-word .r{animation-name:bo-reveal,bo-on,bo-split-r2;animation-duration:.26s,.01s,.36s;animation-delay:.70s,.70s,.70s;animation-fill-mode:forwards}
.bo-word .b{animation-name:bo-reveal,bo-on,bo-split-b2;animation-duration:.26s,.01s,.36s;animation-delay:.70s,.70s,.70s;animation-fill-mode:forwards}
.bo-word .bo-base{animation:bo-base .06s linear 1.02s forwards}
.bo-tag{font-size:13px;letter-spacing:.2em;text-transform:none;color:#aab3c0;opacity:0;transform:translateY(4px);animation:bo-tag .28s ease-out .94s forwards;text-align:center;padding:0 16px}
/* scanlines and sweep over the whole screen */
.bo-lines{position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(0,0,0,.42) 0 1px,transparent 1px 3px);opacity:.9;animation:bo-lines .9s ease-out .0s forwards}
.bo-sweep{position:absolute;left:0;right:0;top:0;height:90px;pointer-events:none;background:linear-gradient(180deg,transparent,rgba(190,205,225,.08) 62%,rgba(220,230,245,.22) 96%,transparent);transform:translateY(-120px);opacity:0;animation:bo-sweep .5s cubic-bezier(.4,0,.3,1) .10s forwards}
@keyframes bo-reveal{from{clip-path:inset(0 0 100% 0)}to{clip-path:inset(0 0 0 0)}}
@keyframes bo-glow{from{opacity:.07}to{opacity:1}}
@keyframes bo-on{to{opacity:1}}
@keyframes bo-split-r{0%{transform:translateX(-6px)}55%{transform:translateX(-2px)}100%{transform:translateX(0)}}
@keyframes bo-split-b{0%{transform:translateX(6px)}55%{transform:translateX(2px)}100%{transform:translateX(0)}}
@keyframes bo-split-r2{0%{transform:translateX(-4px)}100%{transform:translateX(0)}}
@keyframes bo-split-b2{0%{transform:translateX(4px)}100%{transform:translateX(0)}}
@keyframes bo-base{to{opacity:1}}
@keyframes bo-slice{0%{opacity:1;transform:translateX(7px)}50%{opacity:1;transform:translateX(-5px)}100%{opacity:0;transform:translateX(0)}}
@keyframes bo-tag{to{opacity:1;transform:none}}
@keyframes bo-lines{0%{opacity:.9}70%{opacity:.35}100%{opacity:0}}
@keyframes bo-sweep{0%{opacity:1;transform:translateY(-120px)}100%{opacity:0;transform:translateY(110vh)}}
@keyframes bo-out{to{opacity:0;visibility:hidden}}
@media (prefers-reduced-motion:reduce){
  .bo-splash{animation:bo-out .4s ease 1.3s forwards}
  .bo-splash *{animation:none!important}
  .bo-ch,.bo-slice,.bo-sweep,.bo-lines{display:none!important}
  .bo-base{opacity:1!important}.bo-tag{opacity:1!important;transform:none!important}
}
"""


def _timed(css: str) -> str:
    """Stretch every duration/delay by SPLASH_SCALE (env BLACKONYX_SPLASH_SCALE, default 1.8) and add a hold before the fade-out."""
    import re
    k = float(os.environ.get("BLACKONYX_SPLASH_SCALE", "1.8"))
    out_at = 1.14 * k + 1.1                      # the finished wordmark stays on screen for about a second
    keep = css.replace("@OUT@", "@@OUT@@")
    scaled = re.sub(r"(?<![\w.%-])(\d*\.\d+|\d+)s\b", lambda m: f"{float(m.group(1)) * k:.3f}s", keep)
    return scaled.replace("@@OUT@@s", f"{out_at:.2f}s")


def splash_html() -> str:
    img = custom_emblem()
    if img:
        return (f"<style>{_timed(CSS + CSS_CUSTOM)}</style><div class='bo-splash' role='img' aria-label='Black Onyx'><div class='bo-lines'></div><div class='bo-sweep'></div>"
                f"<div class='bo-img'><img src='{img}' alt=''><div class='bo-slice2'><img src='{img}' alt=''></div></div></div>")
    m, w = _mark_variants(), _word_variants()

    def stack(cls: str, v: dict[str, str]) -> str:
        return (f'<div class="bo-stack {cls}"><img class="bo-ch r" src="{v["r"]}" alt=""><img class="bo-ch g" src="{v["g"]}" alt="">'
                f'<img class="bo-ch b" src="{v["b"]}" alt=""><img class="bo-base" src="{v["base"]}" alt="">'
                + ('<div class="bo-slice"><img src="' + v["base"] + '" alt=""></div>' if cls == "bo-mark" else "") + "</div>")

    return (f"<style>{_timed(CSS)}</style><div class='bo-splash' role='img' aria-label='Black Onyx. Trust every action. Verify every source.'>"
            f"<div class='bo-lines'></div><div class='bo-sweep'></div>{stack('bo-mark', m)}{stack('bo-word', w)}"
            f"<div class='bo-tag'>Trust every action. Verify every source.</div></div>")
