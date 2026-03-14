--  1. Включает всем заголовкам первого уровня расположение "с новой страницы"
--  2. Заменяет маркер <!-- @new-page --> на разрыв страницы

function Header(el)
  if el.level == 1 then
    local format = FORMAT:match('%-%w+') or FORMAT
    
    if format == 'latex' or format == 'beamer' then
      -- Для LaTeX добавляем класс к заголовку
      -- В шаблоне LaTeX можно настроить стиль для этого класса:
      -- \usepackage{needspace}
      -- \let\oldsection\section
      -- \renewcommand{\section}{\needspace{5\baselineskip}\oldsection}
      -- Или использовать класс в шаблоне для настройки
      local classes = el.attr.classes
      table.insert(classes, 'page-break-before')
      -- Добавляем атрибут для LaTeX-шаблона
      local attr = el.attr
      attr.attributes['page-break'] = 'true'
      return pandoc.Header(el.level, el.content, attr)
    elseif format == 'html' or format == 'html5' or format == 'epub' then
      -- Для HTML добавляем стиль напрямую к заголовку
      local attr = el.attr
      local style = attr.attributes['style'] or ''
      if style ~= '' then style = style .. '; ' end
      style = style .. 'page-break-before: always;'
      attr.attributes['style'] = style
      return pandoc.Header(el.level, el.content, attr)
    elseif format == 'docx' or format == 'ooxml' then
      -- Для DOCX добавляем атрибут, который будет обработан Pandoc
      -- Используем класс, который можно настроить в reference.docx
      local classes = el.attr.classes
      table.insert(classes, 'page-break-before')
      -- Добавляем RawInline с OpenXML для разрыва страницы перед заголовком
      local header_content = el.content
      table.insert(header_content, 1, pandoc.RawInline('openxml', '<w:r><w:br w:type=\"page\"/></w:r>'))
      return pandoc.Header(el.level, header_content, el.attr)
    elseif format == 'odt' then
      -- Для ODT добавляем класс
      local classes = el.attr.classes
      table.insert(classes, 'page-break-before')
      return pandoc.Header(el.level, el.content, el.attr)
    else
      -- Для других форматов добавляем класс
      local classes = el.attr.classes
      table.insert(classes, 'page-break-before')
      return pandoc.Header(el.level, el.content, el.attr)
    end
  end
  return el
end

function RawBlock(el)
  -- Don't do anything if the output is TeX
  if FORMAT:match 'tex$' then
    return nil
  end
  
  if el.text:match("^%s*<!%-%-%s*@new%-page%s*%-%->") then
    local pagebreak = {
      asciidoc = '<<<\n\n',
      context = '\\page',
      epub = '<p style=\"page-break-after: always;\"> </p>',
      html = '<div style=\"page-break-after: always;\"></div>',
      html5 = '<div style=\"page-break-after: always;\"></div>',
      latex = '\\newpage{}',
      beamer = '\\newpage{}',
      ms = '.bp',
      ooxml = '<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>',
      odt = '<text:p text:style-name=\"Pagebreak\"/>',
      docx = pandoc.RawBlock('openxml', '<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>')
    }
    return pagebreak[FORMAT]
      or pandoc.RawBlock('html', '<div style=\"page-break-before:always\"></div>')
  end
  return el
end

