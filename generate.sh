#!/usr/bin/bash

pandoc $(find . -wholename "./build/*.md" | sort) --toc --toc-depth=4 --output=out/pandocster.docx --to=docx --lua-filter=filters/header_offset.lua --lua-filter=filters/link_anchors.lua --resource-path=src/assets
pandoc $(find . -wholename "./build/*.md" | sort) --toc --toc-depth=4 --output=out/pandocster.epub --to=epub --lua-filter=filters/header_offset.lua --lua-filter=filters/link_anchors.lua --resource-path=src/assets
pandoc $(find . -wholename "./build/*.md" | sort) --toc --toc-depth=4 --output=out/pandocster.md --to=markdown --lua-filter=filters/header_offset.lua --lua-filter=filters/link_anchors.lua --resource-path=src/assets
pandoc $(find . -wholename "./build/*.md" | sort) --toc --toc-depth=4 --output=out/pandocster.latex --to=latex --lua-filter=filters/header_offset.lua --lua-filter=filters/link_anchors.lua --resource-path=src/assets
