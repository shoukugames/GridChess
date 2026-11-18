"""Grid Chess: Blitz Edition - a chess notation and typing trainer."""
__version__ = "0.1.1"
TITLE = "Grid Chess: Blitz Edition"

# True when running in a web browser (pygbag / WebAssembly).
import sys as _sys
WEB = _sys.platform == "emscripten"
