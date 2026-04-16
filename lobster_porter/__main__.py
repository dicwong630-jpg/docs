"""
lobster_porter/__main__.py
--------------------------

允許以 `python -m lobster_porter` 直接執行 CLI。

使用範例::

    python -m lobster_porter copy /src/docs --dest /tmp/backup --base /src/
    python -m lobster_porter move /src/images --dest /tmp/archive --dry-run
"""

import sys

from lobster_porter.core import main

if __name__ == "__main__":
    sys.exit(main())
