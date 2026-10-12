safves

Phase 3 adds a compression mode per file. The walker and tree-sitter skeletonizer stay. skeleton: bool is replaced by mode.Resolution order for each file:
Last matching --rule wins.
Else a --focus glob forces full.
Else the global --mode is used (full by default).
--skeleton remains a shortcut for --mode skeleton.