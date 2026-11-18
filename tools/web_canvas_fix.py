#!/usr/bin/env python3
"""Keep the browser canvas the game's shape (pygbag web builds).

pygbag sizes the page canvas once, and sometimes does it before the game has opened its window,
which leaves a 16:9 game squeezed into a square. This adds a tiny script to the built index.html
that re-runs pygbag's resize whenever the canvas is shown at the wrong shape.

    python3 tools/web_canvas_fix.py build/web/index.html     (the web build script runs it)
"""
import sys

MARK = "<!-- shouku: canvas shape fix -->"
SCRIPT = MARK + """
<script>
setInterval(function () {
  var c = document.getElementById("canvas");
  if (!c || !window.window_resize || !c.width || !c.height) return;
  var r = c.getBoundingClientRect();
  if (r.width && r.height && Math.abs(r.width / r.height - c.width / c.height) > 0.03) window.window_resize();
}, 500);
</script>
"""


def apply(index_html):
    with open(index_html, encoding="utf-8") as handle:
        page = handle.read()
    if MARK in page:
        return False
    if "</body>" not in page:
        raise SystemExit(f"{index_html}: no </body>")
    with open(index_html, "w", encoding="utf-8") as handle:
        handle.write(page.replace("</body>", SCRIPT + "</body>", 1))
    return True


if __name__ == "__main__":
    for path in sys.argv[1:] or ["build/web/index.html"]:
        print(path, "fixed" if apply(path) else "already fixed")
