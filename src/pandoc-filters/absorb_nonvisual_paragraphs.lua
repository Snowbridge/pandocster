-- Объединяет визуально пустые параграфы (например, с якорем-Span)
-- со следующим блоком, чтобы убрать лишние пустые абзацы.

local utils = pandoc.utils

--- Возвращает true, если блок Para/Plain не содержит видимого текста.
---@param block pandoc.Para|pandoc.Plain
local function is_visually_empty_block(block)
  if not (block.t == "Para" or block.t == "Plain") then
    return false
  end

  -- stringify учитывает вложенные инлайны; если нет непробельных символов,
  -- блок визуально пуст (например, только span с id).
  local s = utils.stringify(block)
  return not s:match("%S")
end

--- Объединяет визуально пустые параграфы со следующим блоком.
---@param blocks pandoc.Blocks
---@return pandoc.Blocks
local function merge_empty_paragraphs(blocks)
  local result = pandoc.Blocks({})
  local i = 1

  while i <= #blocks do
    local current = blocks[i]

    if (current.t == "Para" or current.t == "Plain")
        and is_visually_empty_block(current)
        and i < #blocks then

      local next_block = blocks[i + 1]

      -- Объединяем с последующим Para/Plain: переносим инлайны якоря в начало.
      if next_block.t == "Para" or next_block.t == "Plain" then
        local merged_inlines = current.content .. next_block.content
        local merged

        if next_block.t == "Para" then
          merged = pandoc.Para(merged_inlines)
        else
          merged = pandoc.Plain(merged_inlines)
        end

        result:insert(merged)
        i = i + 2

      -- Объединяем с Header, чтобы якорь попал внутрь заголовка.
      elseif next_block.t == "Header" then
        local merged_inlines = current.content .. next_block.content
        local merged = pandoc.Header(next_block.level, merged_inlines, next_block.attr)

        result:insert(merged)
        i = i + 2

      else
        -- Тип следующего блока нам не подходит: не трогаем текущий,
        -- чтобы не потерять якорь в нестандартных случаях.
        result:insert(current)
        i = i + 1
      end
    else
      result:insert(current)
      i = i + 1
    end
  end

  return result
end

function Pandoc(doc)
  doc.blocks = merge_empty_paragraphs(doc.blocks)
  return doc
end

