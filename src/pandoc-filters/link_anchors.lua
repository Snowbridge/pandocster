-- заменяет @anchor на якорь в html

function RawBlock(el)

    if el.format ~= "html" then
        return nil
    end

    -- ищет маркер <!-- @anchor=\"10-solution%2F90-adr%2FADR-001-non-idempotent-only.md\" -->
    local anchor_id = el.text:match("^%s*<!%-%-%s*@anchor=\"([^%s]+)\"%s*%-%->")
    if anchor_id ~= nil then
        local anchor_block
        local writer = PANDOC_WRITER or FORMAT or ""
        if writer == "latex" then
            anchor_block = pandoc.RawBlock("latex", "\\label{" .. anchor_id .. "}")
        elseif writer == "markdown" or writer == "gfm" or writer:match("markdown") then
            -- Для markdown‑семейства вставляем сырой HTML‑якорь, чтобы избежать синтаксиса `[]{#id}`
            anchor_block = pandoc.RawBlock("html", '<span id=\"' .. anchor_id .. '\"></span>')
        else
            -- Для других форматов — пустой span с id (например, для HTML, DOCX)
            anchor_block = pandoc.Span({}, { id = anchor_id })
        end
        return anchor_block
    end
    return nil
        
end

