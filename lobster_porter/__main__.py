"""
龍蝦搬運工 CLI 入口點。

使用方式::

    python -m lobster_porter <command> [options]

Commands
--------
move      批量移動檔案
copy      批量複製檔案
classify  批量分類並輸出到指定路徑
"""

import sys
from .core import main

sys.exit(main())
