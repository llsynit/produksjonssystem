import re
from lxml import etree, html

def move_page_top_level(element):
    """
    Determines if the element should be moved to the top level.

    Args:
        element (Element): The XML element to check.

    Returns:
        bool: True if the element should be moved to the top level, False otherwise.
    """
    ancestors = element.xpath('ancestor::*')
    for ancestor in ancestors:
        if re.match(r'h[1-6]|table|th|td|p|li', ancestor.tag) or \
           (ancestor.tag == 'section' and types(ancestor) == 'toc' and ancestor.xpath('ol[@class="list-type-none"]')):
            return False
    return True

def move_page_before(element):
    """
    Determines if the element should be moved before the current position.

    Args:
        element (Element): The XML element to check.

    Returns:
        bool: True if the element should be moved before, False otherwise.
    """
    if re.match(r'h[1-6]|table|th|td', element.tag):
        return True
    ancestors = element.xpath('ancestor::section')
    for ancestor in ancestors:
        if types(ancestor) == 'toc' and ancestor.xpath('ol[@class="list-type-none"]'):
            return True
    return False

def types(element):
    """
    Tokenizes the @epub:type attribute of the element.

    Args:
        element (Element): The XML element to process.

    Returns:
        list: A list of tokens from the @epub:type attribute.
    """
    return re.split(r'\s+', element.get('epub:type', ''))

def classes(element):
    """
    Tokenizes the @class attribute of the element.

    Args:
        element (Element): The XML element to process.

    Returns:
        list: A list of tokens from the @class attribute.
    """
    return re.split(r'\s+', element.get('class', ''))

def create_pagebreak(element):
    """
    # match="*[not(self::p) and f:movePageBefore(.)=true() and (.//span[@epub:type = 'pagebreak'] or .//div[@epub:type = 'pagebreak']) and f:movePageTopLevel(.)=true()]"
    Creates a page break for the given element.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    # Determine the title value
    title = element.get('title', element.text)

    # Check if the title is a Roman numeral
    is_roman_numeral = bool(re.match(r'^[IVXLCDM]+$', title.upper()))

    # Determine the page number, treating it as a string
    page_number = title

    # Determine the starting page number from metadata
    start_from = int(element.xpath('string(//meta[@name="startPagenumberingFrom"]/@content)') or 0)

    # Only compare page-number as an integer if it is not a Roman numeral
    page_number_as_integer = int(page_number) if not is_roman_numeral else None

    # Determine the max page number
    max_page_number = element.xpath('(//div | //span)[f:types(.) = "pagebreak"][last()]/@title | (//div | //span)[f:types(.) = "pagebreak"][last()]/text()')
    max_page_number = max_page_number[0] if max_page_number else ''

    # Avoid specific ancestor elements
    if not element.xpath('ancestor::li/p | ancestor::figcaption/p | ancestor::figure[f:classes(.) = "image"]/aside/p | ancestor::caption/p'):
        p = etree.Element('p')
        element.addprevious(p)

    # Create the page break div based on conditions
    if not is_roman_numeral and page_number_as_integer is not None and page_number_as_integer >= start_from:
        div = etree.Element('div', attrib={'epub:type': 'pagebreak', 'title': page_number})
        div.text = f'--- {page_number} til {max_page_number}'
        element.addprevious(div)
    elif is_roman_numeral:
        div = etree.Element('div', attrib={'epub:type': 'pagebreak', 'title': page_number})
        div.text = f'--- {page_number} til {max_page_number}'
        element.addprevious(div)


def handle_pagebreak_elements(element):
    """
    # match="*[not(self::p) and f:movePageBefore(.)=true() and (.//span[@epub:type = 'pagebreak'] or .//div[@epub:type = 'pagebreak']) and f:movePageTopLevel(.)=true()]"
    Handles elements that are not <p> and have pagebreak spans or divs, and should be moved before and to the top level.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag != 'p' and move_page_before(element) and \
       (element.xpath('.//span[@epub:type="pagebreak"]') or element.xpath('.//div[@epub:type="pagebreak"]')) and \
       move_page_top_level(element):
        for pagebreak_element in element.xpath('.//span[@epub:type="pagebreak"] | .//div[@epub:type="pagebreak"]'):
            create_pagebreak(pagebreak_element)
        # Continue processing the next matching element
        next_match(element)

def next_match(element):
    """
    Simulates the behavior of <xsl:next-match /> by continuing to the next processing step.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    # Call the next processing function
    handle_other_elements(element)

def handle_other_elements(element):
    """
    Handles other elements that do not match the specific conditions for pagebreak elements.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    # Implement other processing logic here
    pass

def handle_comment(element):
    """
    # match="comment()"
    Handles comment nodes.

    Args:
        element (Element): The XML comment element to process.

    Returns:
        None
    """
    # In XSLT, this template does nothing for comments, so we can skip processing
    pass

def handle_span_answer(element):
    """
    # match="span[@class = 'answer']"
    Handles <span> elements with class 'answer'.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    # Replace the content of the element with '....'
    element.text = '....'

def handle_span_answer_1(element):
    """
    # match="span[@class = 'answer_1']"
    Handles <span> elements with class 'answer_1'.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    # Replace the content of the element with '_'
    element.text = '_'

def handle_div_list_enumeration_1(element):
    """
    # match="div[@class='list-enumeration-1']"
    Handles <div> elements with class 'list-enumeration-1'.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    p = etree.Element('p')
    spans = element.xpath('./p/span')

    for i, span in enumerate(spans):
        # Apply templates (process the span element)
        process_element(span)

        # Append the processed span to the new <p> element
        p.append(span)

        # Add appropriate text based on conditions
        if i != len(spans) - 1:
            if not re.match(r'\.$', span.text):
                p.text = (p.text or '') + ', '
            else:
                p.text = (p.text or '') + ' '

    # Replace the original <div> element with the new <p> element
    element.getparent().replace(element, p)

def handle_span_pagebreak_in_p(element):
    """
    # match="span[f:types(.) = 'pagebreak' and ancestor::p]"
    Removes <span> elements with type 'pagebreak' that are descendants of <p>.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if 'pagebreak' in types(element) and element.xpath('ancestor::p'):
        element.getparent().remove(element)

def handle_span_lic(element):
    """
    # match="span[@class='lic']"
    Handles <span> elements with class 'lic'.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    # Apply templates (process the span element)
    process_element(element)

    # Check if the next sibling is a <span> and add a space if true
    next_sibling = element.xpath('following-sibling::node()[1]')
    if next_sibling and re.match(r'span', next_sibling[0].tag):
        element.tail = (element.tail or '') + ' '
def handle_empty_table_cells(element):
    """
    # match="th[. =''] | thead//td[. =''] | td[. ='' and not(exists(ancestor::section[matches(@class, 'oppgaver1|task')]))]"
    Handles empty <th> and <td> elements, and <td> elements that are not descendants of sections with specific classes.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if (element.tag == 'th' and element.text == '') or \
       (element.tag == 'td' and element.text == '' and not element.xpath('ancestor::section[matches(@class, "oppgaver1|task")]')):
        # Copy the element and its attributes
        new_element = etree.Element(element.tag, attrib=element.attrib)
        new_element.text = '--'
        element.getparent().replace(element, new_element)
def handle_td_in_task_section(element):
    """
    # match="td[. ='' and exists(ancestor::section[matches(@class, '^(oppgaver1|task)$')]) and not(exists(ancestor::thead))]"
    Handles empty <td> elements that are descendants of sections with specific classes and not descendants of <thead>.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'td' and element.text == '' and \
       element.xpath('ancestor::section[matches(@class, "^(oppgaver1|task)$")]') and \
       not element.xpath('ancestor::thead'):
        # Copy the element and its attributes
        new_element = etree.Element(element.tag, attrib=element.attrib)
        new_element.text = '....'
        element.getparent().replace(element, new_element)

def handle_li_ol_ul(element):
    """
    # match="li/ol[not(exists(preceding-sibling::*) or preceding-sibling::node()[matches(., '[^\s]')])] | li/ul[not(exists(preceding-sibling::*) or preceding-sibling::node()[matches(., '[^\s]')])]"
    Handles <li> elements with <ol> or <ul> children that do not have preceding siblings or non-whitespace nodes.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if (element.tag == 'ol' or element.tag == 'ul') and \
       element.xpath('not(exists(preceding-sibling::*) or preceding-sibling::node()[matches(., "[^\\s]")])'):
        # Create a new <span> element with the specified class and text
        span = etree.Element('span', attrib={'class': 'dummyToIncludeNumbering'})
        span.text = 'STATPED_DUMMYTEXT_LI_OL'
        element.addprevious(span)
        # Continue processing the next matching element
        next_match(element)

def handle_heading_elements(element):
    """
    # match="*[matches(name(), 'h[1-6]') and not(ancestor::section[f:types(.) = 'toc'] or ancestor::aside[f:classes(.) = 'glossary'])]"
    Handles heading elements (h1-h6) that are not descendants of sections with type 'toc' or asides with class 'glossary'.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if re.match(r'h[1-6]', element.tag) and \
       not element.xpath('ancestor::section[f:types(.) = "toc"] or ancestor::aside[f:classes(.) = "glossary"]'):
        # Check conditions for adding a <p> element
        if not element.xpath('preceding-sibling::*[position() = last()][name() = "div" or name() = "span"][@class = "page-normal"] or preceding-sibling::*[1][matches(name(), "^h[1-6]$")] or ((count(preceding-sibling::*) = 0 and ../preceding-sibling::*[1][matches(name(), "^h[1-6]$")])) or child::span[f:types(.) = "pagebreak"]'):
            p = etree.Element('p')
            element.addprevious(p)

        # Copy the element and its attributes
        new_element = etree.Element(element.tag, attrib=element.attrib)
        new_element.text = 'xxx' + element.tag[1] + ' '

        # Append the children of the original element to the new element
        for child in element:
            new_element.append(child)

        element.getparent().replace(element, new_element)

def handle_non_p_elements_with_pagebreak(element):
    """
    # match="*[not(self::p) and f:movePageBefore(.)=true() and (.//span[@epub:type = 'pagebreak'] or .//div[@epub:type = 'pagebreak']) and f:movePageTopLevel(.)=true()]"
    Handles elements that are not <p> and have pagebreak spans or divs, and should be moved before and to the top level.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag != 'p' and move_page_before(element) and \
       (element.xpath('.//span[@epub:type="pagebreak"]') or element.xpath('.//div[@epub:type="pagebreak"]')) and \
       move_page_top_level(element):
        for pagebreak_element in element.xpath('.//span[@epub:type="pagebreak"] | .//div[@epub:type="pagebreak"]'):
            create_pagebreak(pagebreak_element)
        # Continue processing the next matching element
        next_match(element)

def handle_div_span_pagebreak(element):
    """
    # match="div[f:types(.) = 'pagebreak' and f:movePageBefore(parent::*)=false() and f:movePageTopLevel(parent::*)=true() and not(ancestor::li)] | span[f:types(.) = 'pagebreak' and f:movePageBefore(parent::*)=false() and f:movePageTopLevel(parent::*)=true() and not(ancestor::li or ancestor::p)]"
    Handles <div> and <span> elements with type 'pagebreak' that should not be moved before but should be moved to the top level, and are not descendants of <li> or <p>.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if 'pagebreak' in types(element) and not move_page_before(element.getparent()) and \
       move_page_top_level(element.getparent()) and not element.xpath('ancestor::li') and \
       (element.tag == 'div' or (element.tag == 'span' and not element.xpath('ancestor::p'))):
        create_pagebreak(element)


def handle_figcaption_figure_caption_p(element):
    """
    Handles <p> elements inside <figcaption>, <figure> with class 'image' and <aside>, and <caption> that should not be moved before.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if (element.tag == 'p' and element.xpath('parent::figcaption') and not move_page_before(element)) or \
       (element.tag == 'p' and element.xpath('parent::figure[classes(.) = "image"]/aside') and not move_page_before(element)) or \
       (element.tag == 'p' and element.xpath('parent::caption') and not move_page_before(element)):
        # Apply templates (process the element)
        process_element(element)

        # Check if a <br> element should be added
        if element.getparent().index(element) != len(element.getparent()) - 1 and \
           not element.xpath('following-sibling::*[1][self::ol or self::ul or self::table]'):
            br = etree.Element('br')
            element.addnext(br)

        # Process descendant pagebreak spans
        for pagebreak_element in element.xpath('descendant::span[types(.) = "pagebreak"]'):
            create_pagebreak(pagebreak_element)
def handle_li_with_pagebreak(element):
    """
    Handles <li> elements that should not be moved before, contain a pagebreak span, and do not contain nested <li> elements with pagebreak spans.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'li' and not move_page_before(element) and \
       element.xpath('.//span[@epub:type="pagebreak"]') and \
       not element.xpath('.//li//span[@epub:type="pagebreak"]'):
        # Copy the element and its attributes
        new_element = etree.Element(element.tag, attrib=element.attrib)

        # Apply templates (process the element)
        for child in element:
            new_element.append(child)

        # Process descendant pagebreak spans
        for pagebreak_element in new_element.xpath('descendant::span[types(.) = "pagebreak"]'):
            create_pagebreak(pagebreak_element)

        element.getparent().replace(element, new_element)


def handle_aside_div(element):
    """
     match="aside[f:classes(.) = 'sidebar'] | div[f:classes(.) = 'linegroup']">

    Handles <aside> elements with class 'sidebar' and <div> elements with class 'linegroup'.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if (element.tag == 'aside' and 'sidebar' in classes(element)) or \
       (element.tag == 'div' and 'linegroup' in classes(element)):
        # Add a <p> element before processing the next match
        p = etree.Element('p')
        element.addprevious(p)
        # Continue processing the next matching element
        next_match(element)


def handle_div_ramme_generisk_ramme(element):
    """
    Handles <div> elements with class 'ramme' or 'generisk-ramme'.

    # match="div[f:classes(.) = 'ramme'] | div[f:classes(.) = 'generisk-ramme']"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'div' and ('ramme' in classes(element) or 'generisk-ramme' in classes(element)):
        # Add a <p> element before processing the next match
        p_before = etree.Element('p')
        element.addprevious(p_before)
        # Continue processing the next matching element
        next_match(element)
        # Add a <p> element after processing the next match
        p_after = etree.Element('p')
        element.addnext(p_after)

def handle_aside_glossary_heading(element):
    """
    Handles heading elements (h1-h6) inside <aside> elements with class 'glossary'.

    # match="aside[f:classes(.) = 'glossary']/*[matches(name(), 'h[1-6]')]"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and 'glossary' in classes(element.getparent()):
        # Create a new <p> element
        p = etree.Element('p')

        # Add text before and after the content
        p.text = '_'
        for child in element:
            p.append(child)
        p.tail = '_'

        # Replace the original element with the new <p> element
        element.getparent().replace(element, p)
def handle_div_aside_ramdoc(element):
    """
    Handles <div> and <aside> elements with class 'ramdoc'.

    # match="div[f:classes(.) = 'ramdoc'] | aside[f:classes(.) = 'ramdoc']"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag in ['div', 'aside'] and 'ramdoc' in classes(element):
        # Add a <p> element before processing the next match
        p_before = etree.Element('p')
        element.addprevious(p_before)

        # Create a copy of the element
        new_element = etree.Element(element.tag, attrib=element.attrib)

        # Add a <p> element with a <span> inside the copied element
        p_inside = etree.Element('p')
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = 'Ramme:'
        p_inside.append(span)
        new_element.append(p_inside)

        # Apply templates (process the element)
        for child in element:
            new_element.append(child)

        # Replace the original element with the new element
        element.getparent().replace(element, new_element)
def img_alt(element):
    """
    Determines the alt text for an image element.

    Args:
        element (Element): The XML element to process.

    Returns:
        str: The alt text for the image.
    """
    alt = element.get('alt', '')
    alt_map = {
        'photo': 'foto',
        'illustration': 'illustrasjon',
        'figure': 'figur',
        'symbol': 'symbol',
        'map': 'kart',
        'drawing': 'tegning',
        'comic': 'tegneserie',
        'logo': 'logo'
    }
    return alt_map.get(alt, alt)

def handle_img(element):
    """
    Handles <img> elements by adding alt text in square brackets.
    match="img"
    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'img':
        alt_text = img_alt(element)
        element.text = f'[{alt_text}]'

def handle_figure_image_series(element):
    """
    Handles <figure> elements with class 'image-series'.

    # match="figure[f:classes(.) = 'image-series']"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'figure' and 'image-series' in classes(element):
        # Apply templates (process the element)
        for child in element:
            process_element(child)

def handle_figure_image(element):
    """
    Handles <figure> elements with class 'image'.
     match="figure[f:classes(.) = 'image']"
    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'figure' and 'image' in classes(element):
        # Add a <p> element before processing the next match
        p_before = etree.Element('p')
        element.addprevious(p_before)

        # Create a new <p> element with the image description
        p_inside = etree.Element('p', attrib={'lang': 'no', 'xml:lang': 'no'})
        p_inside.text = 'Bilde: ' + img_alt(element.find('img'))

        # Add the new <p> element inside the figure
        element.insert(0, p_inside)

        # Apply templates (process the aside and figcaption elements)
        for aside in element.findall('aside'):
            process_element(aside)
        for figcaption in element.findall('figcaption'):
            process_element(figcaption)

        # Add a <p> element after processing the next match
        p_after = etree.Element('p')
        element.addnext(p_after)

def handle_figure_image_aside(element):
    """
    Handles <aside> elements inside <figure> elements with class 'image'.

    # match="figure[f:classes(.) = 'image']/aside"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'aside' and 'image' in classes(element.getparent()):
        # Check if the content is not '¤' or '*'
        content = ''.join(element.itertext()).strip()
        if content not in ['¤', '*']:
            # Create a new <p> element with the explanation
            p = etree.Element('p', attrib={'lang': 'no', 'xml:lang': 'no'})
            p.text = 'Forklaring: '

            # Append the children of the original element to the new <p> element
            for child in element:
                p.append(child)

            # Replace the original element with the new <p> element
            element.getparent().replace(element, p)

def handle_figcaption(element):
    """
    Handles <figcaption> elements.

    # match="figcaption"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'figcaption':
        # Create a new <p> element with the caption text
        p = etree.Element('p', attrib={'lang': 'no', 'xml:lang': 'no'})
        p.text = 'Bildetekst: '

        # Append the children of the original element to the new <p> element
        for child in element:
            p.append(child)

        # Replace the original element with the new <p> element
        element.getparent().replace(element, p)


def handle_figure_image_series_figcaption(element):
    """
    Handles <figcaption> elements inside <figure> elements with class 'image-series'.

    # match="figure[f:classes(.) = 'image-series']/figcaption" priority="2"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'figcaption' and 'image-series' in classes(element.getparent()):
        # Add a <p> element before processing the next match
        p_before = etree.Element('p')
        element.addprevious(p_before)

        # Create a new <p> element with the series text
        p_inside = etree.Element('p')
        p_inside.text = 'Bildeserie: '

        # Append the children of the original element to the new <p> element
        for child in element:
            p_inside.append(child)

        # Replace the original element with the new <p> element
        element.getparent().replace(element, p_inside)


def handle_ol_toc(element):
    """
    Handles <ol> elements inside <section> elements with type 'toc'.

    # match="ol[parent::section[f:types(.) = 'toc']]" priority="10"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'ol' and 'toc' in types(element.getparent()):
        # Process descendant pagebreak spans
        for pagebreak_element in element.xpath('descendant::span[types(.) = "pagebreak"]'):
            create_pagebreak(pagebreak_element)

        # Create a copy of the element
        new_element = etree.Element(element.tag, attrib=element.attrib)

        # Apply templates (process the element)
        for attr in element.attrib:
            new_element.set(attr, element.get(attr))

        # Add a new <li> element with specific content
        li = etree.Element('li')
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = 'xxx1'
        li.append(span)
        a = etree.Element('a', attrib={'href': '#statped_merknad'})
        span_lic = etree.Element('span', attrib={'class': 'lic'})
        span_no = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span_no.text = 'Merknad'
        span_lic.append(span_no)
        a.append(span_lic)
        li.append(a)
        new_element.append(li)

        # Apply templates (process the element)
        for child in element:
            new_element.append(child)

        # Replace the original element with the new element
        element.getparent().replace(element, new_element)
def handle_ol_toc_nested(element):
    """
    **check**
    Handles <ol> elements inside <section> elements with type 'toc' and with at least two ancestor <li> elements.

    # match="ol[ancestor::section[f:types(.) = 'toc'] and count(ancestor::li) ge 2]"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'ol' and 'toc' in types(element.xpath('ancestor::section')[0]) and len(element.xpath('ancestor::li')) >= 2:
        # Remove the element
        element.getparent().remove(element)

def handle_li_toc(element):
    """
    Handles <li> elements inside <section> elements with type 'toc'.

    # match="li[ancestor::section[f:types(.) = 'toc']]"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'li' and 'toc' in types(element.xpath('ancestor::section')[0]):
        # Create a copy of the element
        new_element = etree.Element(element.tag, attrib=element.attrib)

        # Apply templates (process the attributes)
        for attr in element.attrib:
            new_element.set(attr, element.get(attr))

        # Add the concatenated text
        count_li = len(element.xpath('ancestor-or-self::li'))
        new_element.text = f'xxx{count_li} '

        # Apply templates (process the child nodes)
        for child in element:
            new_element.append(child)

        # Replace the original element with the new element
        element.getparent().replace(element, new_element)
def handle_li_toc_kolofon(element):
    """
    Handles <li> elements inside <section> elements with type 'toc' and text starting with 'Kolofon'.

    # match="li[ancestor::section[f:types(.) = 'toc'] and matches(., '^Kolofon')]" priority="2"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'li' and 'toc' in types(element.xpath('ancestor::section')[0]) and re.match(r'^Kolofon', ''.join(element.itertext()).strip()):
        # Remove the element
        element.getparent().remove(element)

def handle_body(element):
    """
    Handles the <body> element.

    # match="body"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'body':
        # Create a copy of the element
        new_element = etree.Element(element.tag, attrib=element.attrib)

        # Apply templates (process the attributes)
        for attr in element.attrib:
            new_element.set(attr, element.get(attr))

        # Extract variables
        title = element.xpath('/*/head/title/text()')[0] if element.xpath('/*/head/title/text()') else ''
        language = [re.sub(r'^(.*), *(.*)$', r'\2 \1', lang) for lang in element.xpath('/*/head/meta[@name = "dc:language"]/@content')]
        authors = [re.sub(r'^(.*), *(.*)$', r'\2 \1', author) for author in element.xpath('/*/head/meta[@name = "dc:creator"]/@content')]
        publisher_original = element.xpath('/*/head/meta[@name = "dc:publisher.original"]/@content')[0] if element.xpath('/*/head/meta[@name = "dc:publisher.original"]/@content') else ''
        publisher = element.xpath('/*/head/meta[@name = "dc:publisher"]/@content')[0] if element.xpath('/*/head/meta[@name = "dc:publisher"]/@content') else ''
        publisher_location = element.xpath('/*/head/meta[@name = "dc:publisher.location"]/@content')[0] if element.xpath('/*/head/meta[@name = "dc:publisher.location"]/@content') else ''
        issued = element.xpath('/*/head/meta[@name = "dc:date.issued"]/@content')[0] if element.xpath('/*/head/meta[@name = "dc:date.issued"]/@content') else ''
        issued_original = element.xpath('/*/head/meta[@name = "dc:issued.original"]/@content')[0] if element.xpath('/*/head/meta[@name = "dc:issued.original"]/@content') else ''
        edition_original = element.xpath('/*/head/meta[@name = "schema:bookEdition.original"]/@content')[0] if element.xpath('/*/head/meta[@name = "schema:bookEdition.original"]/@content') else ''
        edition_original = re.sub(r'^(\d+\.?)$', r'\1.utg.', edition_original)
        edition_original = re.sub(r'\.+', '.', edition_original)
        pagebreaks = element.xpath('(//div | //span)[f:types(.) = "pagebreak"]')
        first_page = pagebreaks[0].get('title') if pagebreaks and pagebreaks[0].get('title') else pagebreaks[0].text if pagebreaks else ''
        last_page = pagebreaks[-1].get('title') if pagebreaks and pagebreaks[-1].get('title') else pagebreaks[-1].text if pagebreaks else ''
        isbn = element.xpath('/*/head/meta[@name = "schema:isbn"]/@content')[0] if element.xpath('/*/head/meta[@name = "schema:isbn"]/@content') else ''

        # Create the <p> element with the extracted information
        p = etree.Element('p', attrib={'xml:lang': 'no', 'lang': 'no'})
        p.text = title
        if language:
            if len(language) > 1:
                p.text += ' - ' + ', '.join(language[:-1]) + '/' + language[-1]
            else:
                p.text += ' - ' + language[0]
        if first_page and last_page:
            p.text += f' (s. {first_page}-{last_page})'
        if authors:
            if len(authors) > 1:
                p.text += ' - ' + ', '.join(authors[:-1]) + ' og ' + authors[-1]
            else:
                p.text += ' - ' + authors[0]
        p.text += f' {publisher_original}'
        if issued_original:
            p.text += f' {issued_original}'
        if edition_original:
            p.text += f' - {edition_original}'
        if isbn:
            p.text += f' - ISBN: {isbn}'

        new_element.append(p)

        # Apply templates (process the section elements)
        for section in element.xpath('section[f:types(.) = "toc"]'):
            process_element(section)

        # Add the general note for Statped's books
        div = etree.Element('div')
        p = etree.Element('p')
        div.append(p)
        h1 = etree.Element('h1', attrib={'id': 'statped_merknad'})
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = 'xxx1 Generell merknad for Statpeds leselistbøker:'
        h1.append(span)
        div.append(h1)
        p = etree.Element('p')
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = 'Filen har en klikkbar innholdsfortegnelse.'
        p.append(span)
        div.append(p)
        p = etree.Element('p')
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = 'xxx innleder overskrifter. Overskriftsnivået vises med tall: xxx1, xxx2 osv.'
        p.append(span)
        div.append(p)
        p = etree.Element('p')
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = '--- innleder sidetallet.'
        p.append(span)
        div.append(p)
        p = etree.Element('p')
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = 'Uthevingstegnet er slik: _.'
        p.append(span)
        div.append(p)
        p = etree.Element('p')
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = 'Eksempel: _Denne setningen er uthevet._'
        p.append(span)
        div.append(p)
        p = etree.Element('p')
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = 'Ordforklaringer, gloser eller stikkord finner du etter hovedteksten og eventuelle bilder.'
        p.append(span)
        div.append(p)
        p = etree.Element('p')
        span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
        span.text = 'Eventuelle stikkordsregistre og kilder er utelatt. Kolofonen og baksideteksten finner du til slutt i denne filen.'
        p.append(span)
        div.append(p)
        new_element.append(div)

        # Apply templates (process the remaining elements)
        for child in element.xpath('* except section[f:types(.) = ("toc", "backmatter", "index", "colophon", "titlepage", "cover")]'):
            process_element(child)

        # Add the aftertext
        p = etree.Element('p')
        new_element.append(p)
        p = etree.Element('p')
        p.text = 'Ettertekst:'
        new_element.append(p)
        for section in element.xpath('section[f:types(.) = "backmatter" and not(f:types(.) = "index" or f:types(.) = "colophon")]'):
            process_element(section)
        p = etree.Element('p')
        new_element.append(p)
        p = etree.Element('p')
        p.text = 'Kolofon:'
        new_element.append(p)
        for section in element.xpath('section[f:types(.) = "colophon"]'):
            process_element(section)
        p = etree.Element('p')
        new_element.append(p)
        p = etree.Element('p')
        p.text = 'Baksidetekst:'
        new_element.append(p)
        for section in element.xpath('section[f:types(.) = "cover"]/section[f:classes(.) = "rearcover"]'):
            process_element(section)
        p = etree.Element('p')
        new_element.append(p)

        # Add the copyright notice
        if element.xpath("//meta[@name='dc:language']/@content = 'nn'"):
            p = etree.Element('p')
            span = etree.Element('span', attrib={'xml:lang': 'nn', 'lang': 'nn'})
            span.text = 'Opphavsrett Statped:<br>Denne boka er lagd til rette for elevar med synssvekking. Ifølgje lov om opphavsrett kan ho ikkje brukast av andre. Teksten er tilpassa for lesing med skjermlesar og leselist. Kopiering er berre tillate til eige bruk. Brot på desse avtalevilkåra, slik som ulovleg kopiering eller medverknad til ulovleg kopiering, kan medføre ansvar etter åndsverklova.</br>'
            p.append(span)
            new_element.append(p)
        else:
            p = etree.Element('p')
            span = etree.Element('span', attrib={'xml:lang': 'no', 'lang': 'no'})
            span.text = 'Opphavsrett Statped:<br>Denne boka er tilrettelagt for elever med synssvekkelse. Ifølge lov om opphavsrett kan den ikke brukes av andre. Teksten er tilpasset for lesing med skjermleser og leselist. Kopiering er kun tillatt til eget bruk. Brudd på disse avtalevilkårene, som ulovlig kopiering eller medvirkning til ulovlig kopiering, kan medføre ansvar etter åndsverkloven.</br>'
            p.append(span)
            new_element.append(p)

        # Replace the original element with the new element
        element.getparent().replace(element, new_element)
def handle_colophon_heading(element):
    """
    Handles heading elements (h1-h6) inside <section> elements with type 'colophon'.

    # match="section[f:types(.) = 'colophon']/*[matches(name(), 'h[1-6]')]"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and 'colophon' in types(element.getparent()):
        # Process the heading element as needed
        # For example, you can add a specific class or modify its content
        element.set('class', 'colophon-heading')


def handle_em_strong(element):
    """
    Handles <em> and <strong> elements by wrapping their content with underscores.

    # match="em | strong"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag in ['em', 'strong']:
        # Create a new text element with underscores
        new_element = etree.Element(element.tag)
        new_element.text = '_'

        # Append the children of the original element to the new element
        for child in element:
            new_element.append(child)

        # Add the closing underscore
        new_element.tail = '_'

        # Replace the original element with the new element
        element.getparent().replace(element, new_element)
def handle_table(element):
    """
    Handles <table> elements by inserting text and processing its content.

    # match="table"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'table':
        # Check if there are no descendant pagebreak spans
        if not element.xpath('descendant::span[types(.) = "pagebreak"]'):
            # Add a <p> element before the table
            p_before = etree.Element('p')
            element.addprevious(p_before)

        # Create a new <p> element with the table caption
        p_caption = etree.Element('p')
        p_caption.text = 'Tabell: '

        # Append the children of the caption element to the new <p> element
        caption = element.find('caption')
        if caption is not None:
            for child in caption:
                p_caption.append(child)

        # Add the new <p> element before the table
        element.addprevious(p_caption)

        # Create a new <table> element
        new_table = etree.Element('table')

        # Append the children of the original table except the caption to the new table
        for child in element:
            if child.tag != 'caption':
                new_table.append(child)

        # Replace the original table with the new table
        element.getparent().replace(element, new_table)
def handle_ol_ul(element):
    """
    **check next match**
    Handles <ol> and <ul> elements that are not nested inside other <ol> or <ul> elements.

    # match="ol[not(ancestor::ol or ancestor::ul)] | ul[not(ancestor::ol or ancestor::ul)]"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag in ['ol', 'ul'] and not element.xpath('ancestor::ol') and not element.xpath('ancestor::ul'):
        # Simulate <xsl:next-match /> by calling the next processing function
        next_match(element)

        # Add a <p> element after the list
        p_after = etree.Element('p')
        element.addnext(p_after)

def handle_ul_list_unstyled(element):
    """
    Handles <ul> elements with class 'list-unstyled'.

    # match="ul[f:classes(.) = 'list-unstyled']" priority="2"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'ul' and 'list-unstyled' in classes(element):
        # Process each <li> element inside the <ul>
        for li in element.findall('li'):
            p = etree.Element('p')
            if not li.xpath('ancestor::table'):
                p.text = 'STATPED_DUMMYTEXT_LIST_UNSTYLED'
            for child in li:
                p.append(child)
            li.addprevious(p)
            li.getparent().remove(li)

        # Add a <p> element if the <ul> is not inside a table, <ul>, or <ol>
        if not element.xpath('ancestor::table | ancestor::ul | ancestor::ol'):
            p_after = etree.Element('p')
            element.addnext(p_after)


def handle_head(element):
    """
    Handles <head> elements by copying their content and adding a <style> element.

    # match="head"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'head':
        # Create a new <head> element
        new_head = etree.Element('head', attrib=element.attrib)

        # Copy attributes
        for attr in element.attrib:
            new_head.set(attr, element.get(attr))

        # Copy child nodes
        for child in element:
            new_head.append(child)

        # Add a <style> element with specific content
        style = etree.Element('style')
        style.text = 'div.pagebreak {page-break-after:avoid;}'
        new_head.append(style)

        # Replace the original element with the new element
        element.getparent().replace(element, new_head)

def handle_p_before_dl(element):
    """
    Handles <p> elements that are not preceded by another <p> element and are followed by a <dl> element.

    # match="p[not(preceding-sibling::*[1][self::p]) and following-sibling::*[1][self::dl]]"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'p' and not element.xpath('preceding-sibling::*[1][self::p]') and element.xpath('following-sibling::*[1][self::dl]'):
        # Create a new <p> element with the specified text and apply templates
        new_p = etree.Element('p')
        new_p.text = 'STATPED_DUMMYTEXT_P_BEFORE_DL'

        # Append the children of the original <p> element to the new <p> element
        for child in element:
            new_p.append(child)

        # Replace the original <p> element with the new <p> element
        element.getparent().replace(element, new_p)

def handle_sub(element):
    """
    Handles <sub> elements by adding backslashes and parentheses based on the string length.

    # match="sub"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'sub':
        # Create a new text element with backslash
        new_element = etree.Element(element.tag)
        new_element.text = '\\'

        # Add opening parenthesis if string length is greater than 1
        if len(''.join(element.itertext())) > 1:
            new_element.text += '('

        # Append the children of the original element to the new element
        for child in element:
            new_element.append(child)

        # Add closing parenthesis if string length is greater than 1
        if len(''.join(element.itertext())) > 1:
            new_element.text += ')'

        # Replace the original element with the new element
        element.getparent().replace(element, new_element)

def handle_sup(element):
    """
    Handles <sup> elements by adding carets and parentheses based on the string length.

    # match="sup"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'sup':
        # Create a new text element with caret
        new_element = etree.Element(element.tag)
        new_element.text = '^'

        # Add opening parenthesis if string length is greater than 1
        if len(''.join(element.itertext())) > 1:
            new_element.text += '('

        # Append the children of the original element to the new element
        for child in element:
            new_element.append(child)

        # Add closing parenthesis if string length is greater than 1
        if len(''.join(element.itertext())) > 1:
            new_element.text += ')'

        # Replace the original element with the new element
        element.getparent().replace(element, new_element)
def handle_dt_dd_text(element):
    """
    Handles text nodes within <dt> and <dd> elements by applying a series of regex replacements.

    # match="dt//text() | dd//text()"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag is etree.ElementText:
        text_value = element
        # Apply the first regex replacement
        text_value = re.sub(r'\s/\S[^/]*?/', '', text_value)
        # Apply the second regex replacement
        text_value = re.sub(r'\s\[[^\]]*?\]', '', text_value)
        # Apply the third regex replacement
        text_value = re.sub(r':\s*$', ': ', text_value)
        # Apply the fourth regex replacement
        text_value = re.sub(r'\[[^\]]*?\]', '', text_value)

        # Replace the original text with the processed text
        parent = element.getparent()
        parent.text = text_value


def handle_dt(element):
    """
    Handles <dt> elements by renaming them to <span> and applying templates to their attributes and child nodes.

    # match="dt" priority="10"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'dt':
        # Create a new <span> element
        new_element = etree.Element('span')

        # Copy attributes
        for attr in element.attrib:
            new_element.set(attr, element.get(attr))

        # Copy child nodes
        for child in element:
            new_element.append(child)

        # Replace the original <dt> element with the new <span> element
        element.getparent().replace(element, new_element)

def handle_dd(element):
    """
    Handles <dd> elements by renaming them to <span> and applying templates to their attributes and child nodes.

    # match="dd" priority="10"

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if element.tag == 'dd':
        # Create a new <span> element
        new_element = etree.Element('span')

        # Copy attributes
        for attr in element.attrib:
            new_element.set(attr, element.get(attr))

        # Copy child nodes
        for child in element:
            new_element.append(child)

        # Replace the original <dd> element with the new <span> element
        element.getparent().replace(element, new_element)

def process_element(element):
    """
    Processes the given element to handle specific templates.

    Args:
        element (Element): The XML element to process.

    Returns:
        None
    """
    if isinstance(element, etree._Comment):
        handle_comment(element)
    elif element.tag == 'span' and 'class' in element.attrib:
        if element.attrib['class'] == 'answer':
            handle_span_answer(element)
        elif element.attrib['class'] == 'answer_1':
            handle_span_answer_1(element)
        elif element.attrib['class'] == 'lic':
            handle_span_lic(element)
    elif element.tag == 'div' and element.attrib.get('class') == 'list-enumeration-1':
        handle_div_list_enumeration_1(element)
    elif element.tag == 'span' and 'pagebreak' in types(element) and element.xpath('ancestor::p'):
        handle_span_pagebreak_in_p(element)
    elif element.tag in ['th', 'td']:
        handle_empty_table_cells(element)
    elif element.tag == 'td' and element.text == '' and \
         element.xpath('ancestor::section[matches(@class, "^(oppgaver1|task)$")]') and \
         not element.xpath('ancestor::thead'):
        handle_td_in_task_section(element)
    elif element.tag in ['ol', 'ul'] and element.xpath('ancestor::li'):
        handle_li_ol_ul(element)
    elif re.match(r'h[1-6]', element.tag):
        handle_heading_elements(element)
    elif element.tag != 'p' and (element.xpath('.//span[@epub:type="pagebreak"]') or element.xpath('.//div[@epub:type="pagebreak"]')):
        handle_non_p_elements_with_pagebreak(element)
    elif element.tag in ['div', 'span'] and 'pagebreak' in types(element):
        handle_div_or_span_pagebreak(element)
    elif element.tag == 'p' and move_page_top_level(element):
        handle_p_move_page_top_level(element)
    elif element.tag == 'p' and (element.xpath('parent::figcaption') or element.xpath('parent::figure[classes(.) = "image"]/aside') or element.xpath('parent::caption')):
        handle_figcaption_figure_caption_p(element)
    elif element.tag == 'li' and not move_page_before(element) and \
         element.xpath('.//span[@epub:type="pagebreak"]') and \
         not element.xpath('.//li//span[@epub:type="pagebreak"]'):
        handle_li_with_pagebreak(element)
    elif (element.tag == 'aside' and 'sidebar' in classes(element)) or \
         (element.tag == 'div' and 'linegroup' in classes(element)):
        handle_aside_div(element)
    elif element.tag == 'div' and ('ramme' in classes(element) or 'generisk-ramme' in classes(element)):
        handle_div_ramme_generisk_ramme(element)
    elif element.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and 'glossary' in classes(element.getparent()):
        handle_aside_glossary_heading(element)
    elif element.tag in ['div', 'aside'] and 'ramdoc' in classes(element):
        handle_div_aside_ramdoc(element)
    elif element.tag == 'img':
        handle_img(element)
    elif element.tag == 'figure' and 'image-series' in classes(element):
        handle_figure_image_series(element)
    elif element.tag == 'figure' and 'image' in classes(element):
        handle_figure_image(element)
    elif element.tag == 'aside' and 'image' in classes(element.getparent()):
        handle_figure_image_aside(element)
    elif element.tag == 'figcaption':
        handle_figcaption(element)
    elif element.tag == 'figcaption' and 'image-series' in classes(element.getparent()):
        handle_figure_image_series_figcaption(element)
    elif element.tag == 'ol' and 'toc' in types(element.getparent()):
        handle_ol_toc(element)
    elif element.tag == 'ol' and 'toc' in types(element.xpath('ancestor::section')[0]) and len(element.xpath('ancestor::li')) >= 2:
        handle_ol_toc_nested(element)
    elif element.tag == 'li' and 'toc' in types(element.xpath('ancestor::section')[0]):
        handle_li_toc(element)
    elif element.tag == 'li' and 'toc' in types(element.xpath('ancestor::section')[0]) and re.match(r'^Kolofon', ''.join(element.itertext()).strip()):
        handle_li_toc_kolofon(element)
    elif element.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and 'colophon' in types(element.getparent()):
        handle_colophon_heading(element)
    elif element.tag in ['em', 'strong']:
        handle_em_strong(element)
    elif element.tag == 'table':
        handle_table(element)
    elif element.tag in ['ol', 'ul'] and not element.xpath('ancestor::ol') and not element.xpath('ancestor::ul'):
        handle_ol_ul(element)
    elif element.tag == 'ul' and 'list-unstyled' in classes(element):
        handle_ul_list_unstyled(element)
    elif element.tag == 'head':
        handle_head(element)
    elif element.tag == 'dl':
        handle_dl(element)
    elif element.tag == 'p' and not element.xpath('preceding-sibling::*[1][self::p]') and element.xpath('following-sibling::*[1][self::dl]'):
        handle_p_before_dl(element)
    elif element.tag is etree.ElementText and element.getparent().tag in ['dt', 'dd']:
        handle_dt_dd_text(element)
    elif element.tag == 'sub':
        handle_sub(element)
    elif element.tag == 'sup':
        handle_sup(element)
    elif element.tag == 'dt':
        handle_dt(element)
    elif element.tag == 'dd':
        handle_dd(element)
    handle_pagebreak_elements(element)
    # Add other processing logic if needed

def process_html_file(file_path):
    """
    Processes an HTML file and returns the processed content.

    Args:
        file_path (str): The path to the HTML file.

    Returns:
        str: The processed HTML content.
    """
    # Parse the HTML document
    tree = html.parse(file_path)
    root = tree.getroot()

    # Process each element in the document
    for elem in root.iter():
        process_element(elem)

    # Return the processed HTML content
    return etree.tostring(root, pretty_print=True, method="html").decode()

# Example usage
if __name__ == "__main__":
    processed_html = process_html_file('example.html')
    print(processed_html)