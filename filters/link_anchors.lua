-- заменяет @anchor на якорь в html

function RawBlock(el)

    if el.format ~= "html" then
        return nil
    end

    -- ищет маркер <!-- @anchor="10-solution%2F90-adr%2FADR-001-non-idempotent-only.md" -->
    local anchor_id = el.text:match("^%s*<!%-%-%s*@anchor=\"([^%s]+)\"%s*%-%->")
    if anchor_id ~= nil then
        local anchor_block
        if PANDOC_WRITER == "latex" then
            anchor_block = pandoc.RawBlock("latex", "\\label{" .. anchor_id .. "}")
        else
            -- Для других форматов — пустой span с id (например, для HTML)
            anchor_block = pandoc.Div({ pandoc.Span({}, { id = anchor_id }) }, {})
        end
        return anchor_block
    end
    return nil
        
end
