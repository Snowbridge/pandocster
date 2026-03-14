-- смещает уровень всех заголовков на значение, указанное в @header-offset

local current_offset = 0

function RawBlock(el)
    -- Ищем маркер <!-- @header-offset: N -->
    if el.format == "html" and el.text:match("^%s*<!%-%-%s*@header%-offset%:%s*(%d+)%s*%-%->") then
        local depth = tonumber(el.text:match("@header%-offset%:%s*(%d+)"))
        current_offset = depth or 0
        -- Возвращаем nil, чтобы удалить эту строку из вывода
        return {}
    end
    return nil
        
end

function Header(header)
    -- Увеличиваем уровень заголовка на current_offset
    header.level = header.level + current_offset - 1
    return header
end

