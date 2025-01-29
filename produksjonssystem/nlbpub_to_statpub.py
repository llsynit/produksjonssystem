'''
This script converts an epub conforming to the
"Nordic Guidelines for the Production of Accessible EPUB 3" to an
epub conforming to the "Statped Mark-up Requirements" specification.

Discuss: should EPUB for Education Structural Semantics be
better integrated into the script?
https://idpf.org/epub/profiles/edu/structure/
'''

# IMPORTS
# =======

from logging        import getLogger
from argparse       import ArgumentParser
from bs4            import BeautifulSoup, NavigableString
from lxml           import etree
from io             import StringIO, BytesIO
from glob           import glob
from zipfile        import ZipFile, ZIP_DEFLATED
from shutil         import rmtree, copytree, copyfile, make_archive, move
from os             import path, mkdir, getcwd, walk, remove, rename
from pathlib        import Path
from nltk.tokenize  import word_tokenize
from ipapy          import is_valid_ipa
from epubcheck      import EpubCheck

import string, re, nltk, cv2, subprocess #spacy,

import xml.etree.ElementTree    as ET
import numpy                    as np
import pandas                   as pd
import matplotlib.pyplot        as plt
import csv
try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract

#nltk.download('punkt_tab')

# VARIBLES
# ========

TMP_DIR = 'tmp'

xhtml_string = ' '.join([
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<!DOCTYPE html>',
    '<html>',
    '<head>',
    '<meta charset="UTF-8"/>',
    '<meta content="863500" name="dc:identifier"/>',
    '<meta content="width=device-width" name="viewport"/>',
    '<link href="css/ebok.css" rel="stylesheet" type="text/css"/>',
    '</head>',
    '</html',])

correct_html_tag = ' '.join([
    '<html',
    'xmlns="http://www.w3.org/1999/xhtml"',
    'xmlns:xml="http://www.w3.org/XML/1998/namespace"',
    'xmlns:epub="http://www.idpf.org/2007/ops"',
    'epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/#"',
    ])

correct_package_tag = ' '.join([
    '<package',
    'xmlns="http://www.idpf.org/2007/opf"',
    'xmlns:dc="http://purl.org/dc/elements/1.1/"',
    'xmlns:epub="http://www.idpf.org/2007/ops"',
    'prefix="nordic: http://www.mtm.se/epub/"',
    'version="3.0"',
    'xml:lang="no"',
    'unique-identifier="pub-identifier"',
    '>'])

xslt_file = 'html-to-nav.xsl'

PUNCTUATION = string.punctuation

SYMBOLS     = [
        '§',
        '$',
        '£',
        '€',
        '¥',
        ]

# https://idpf.org/epub/profiles/edu/structure/#h.ipobyxqoqtux
ASSESSMENTS = [
            'assessment',
            'assessments',
            'fill-in-the-blank-problem',
            'general-problem',
            'match-problem',
            'multiple-choice-problem',
            'practice',
            'practices',
            'qna',
            'true-false-problem']

NUMBERS = { # TODO: This list should be common to 2.4.1.2
            'no' : {
                'en'    : 1,
                'to'    : 2,
                'tre'   : 3,
                'fire'  : 4,
                'fem'   : 5,
                'seks'  : 6,
                'sju'   : 7,
                'åtte'  : 8,
                'ni'    : 9,
                'ti'    : 10},
            'nb' : {
                'en'    : 1,
                'to'    : 2,
                'tre'   : 3,
                'fire'  : 4,
                'fem'   : 5,
                'seks'  : 6,
                'sju'   : 7,
                'åtte'  : 8,
                'ni'    : 9,
                'ti'    : 10},
            'nn' : {
                'en'    : 1,
                'to'    : 2,
                'tre'   : 3,
                'fire'  : 4,
                'fem'   : 5,
                'seks'  : 6,
                'sju'   : 7,
                'åtte'  : 8,
                'ni'    : 9,
                'ti'    : 10},
            'en' : {
                'one'   : 1,
                'two'   : 2,
                'three' : 3,
                'four'  : 4,
                'five'  : 5,
                'six'   : 6,
                'seven' : 7,
                'eight' : 8,
                'nine'  : 9,
                'ten'   : 10},
            'de' : {
                'eins'  : 1,
                'zwei'  : 2,
                'drei'  : 3,
                'vier'  : 4,
                'fünf'  : 5,
                'sechs' : 6,
                'sieben': 7,
                'acht'  : 8,
                'neun'  : 9,
                'zehn'  : 10},
            'fr' : {
                'un'    : 1,
                'deux'  : 2,
                'trois' : 3,
                'quatre': 4,
                'cinq'  : 5,
                'six'   : 6,
                'sept'  : 7,
                'huit'  : 8,
                'neuf'  : 9,
                'dix'   : 10}
            }

BULLETS = ['•',
           '‣',
           '⁃',
           '⁌',
           '⁍',
           '∙',
           '○',
           '●',
           '◘',
           '◦',
           '☙',
           '❥',
           '❧',
           '⦾',
           '⦿',
           '-']

HEADINGS = {
        'en' : 'Glossary',
        'nn' : 'Ordforklaringar',
        'nb' : 'Ordforklaringer',
        'no' : 'Ordforklaringer'}

PAGES = {
        'da' : 'Side',
        'nl' : 'Bladzijde',
        'en' : 'Page',
        'fi' : 'Sivu',
        'fr' : 'Page',
        'is' : 'Síðu',
        'it' : 'Pagina',
        'la' : 'Pagina',
        'no' : 'Side',
        'nb' : 'Side',
        'nn' : 'Side',
        'sv' : 'Sida'}

BLOCK_ELEMENTS = [
        'address',
        'article',
        'aside',
        'blockquote',
        'canvas',
        'dd',
        'div',
        'dl',
        'dt',
        'fieldset',
        'figcaption',
        'figure',
        'footer',
        'form',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'header',
        'hr',
        'li',
        'main',
        'nav',
        'noscript',
        'ol',
        'p',
        'pre',
        'section',
        'table',
        'tfoot',
        'ul',
        'video']

# https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
# https://spacy.io/models
# These need to be installed with 'python -m spacy download <model>'
LANGUAGE_MODELS = {
    'ca' : 'ca_core_news_trf',          # 'ca_core_news_sm',
    'zh' : 'zh_core_web_trf',           # 'zh_core_web_sm',
    'hr' : 'hr_core_news_lg',           # 'hr_core_news_sm',
    'da' : 'da_core_news_trf',          # 'da_core_news_sm',
    'nl' : 'nl_core_news_lg',           # 'nl_core_news_sm',
    'en' : 'en_core_web_trf',           # 'en_core_web_sm',
    'fi' : 'fi_core_news_lg',           # 'fi_core_news_sm',
    'fr' : 'fr_dep_news_trf',           # 'fr_core_news_sm',
    'de' : 'de_dep_news_trf',           # 'de_core_news_sm',
    'el' : 'el_core_news_lg',           # 'el_core_news_sm',
    'it' : 'it_core_news_lg',           # 'it_core_news_sm',
    'ja' : 'ja_core_news_trf',          # 'ja_core_news_sm',
    'ko' : 'ko_core_news_lg',           # 'ko_core_news_sm',
    'lt' : 'lt_core_news_lg',           # 'lt_core_news_sm',
    'mk' : 'mk_core_news_lg',           # 'mk_core_news_sm',
    'no' : 'nb_core_news_lg',           # 'nb_core_news_sm',
    'nb' : 'nb_core_news_lg',           # 'nb_core_news_sm',
    'nn' : 'nb_core_news_lg',           # 'nb_core_news_sm',
    # TODO: provide language model for nn
    # https://github.com/ltgoslo/norne
    'pl' : 'nb_core_news_lg',           # 'pl_core_news_sm',
    'pt' : 'pt_core_news_lg',           # 'pt_core_news_sm',
    'ro' : 'ro_core_news_lg',           # 'ro_core_news_sm',
    'ru' : 'ru_core_news_lg',           # 'ru_core_news_sm',
    'es' : 'es_dep_news_trf',           # 'es_core_news_sm',
    'sv' : 'sv_core_news_lg',           # 'sv_core_news_sm',
    #'uk' : 'uk_core_news_sm',
    'multi-language' : 'xx_sent_ud_sm'} # 'xx_ent_wiki_sm'}

# FUNCTIONS
# =========

is_task         = lambda tag: 'epub:type' in tag.attrs.keys() and tag['epub:type'] in ASSESSMENTS
is_part_of_task = lambda tag: any([('epub:type' in parent.attrs.keys() and parent['epub:type'] in ASSESSMENTS) for parent in tag.parents])
has_subtasks    = lambda tag: tag.find(attrs={'epub:type':ASSESSMENTS})
get_tasks       = lambda soup: list(soup(attrs={'class': re.compile(r'^assignment')})) + list(soup(attrs={'epub:type':ASSESSMENTS}))
get_answers     = lambda soup: list(soup(attrs={'epub:type':'answer'})) + list(soup(attrs={'epub:type':'answers'}))

def find_xhtml(production_number, epub_folder):
    for root, _, files in walk(epub_folder):
        for file in [f for f in files if f.endswith('.xhtml')]:
            if file == f'{production_number}.xhtml':
                return path.join(root, file)
    #logger.error('No xhtml file found in the temporary directory.')
    print('No xhtml file found in the temporary directory.')
    quit()

def find_folder(start_dir, target_folder):
    for root, dirs, files in walk(start_dir):
        if target_folder in dirs:
            return path.join(root, target_folder)
    return None

# TODO: This does not really work. FIX
def find_header_level(tag):
    for element in [tag] + list(tag.parents):
        for sibling in list(element.find_previous_siblings()) + list(element.find_next_siblings()):
            if (h := sibling.find(re.compile(r'^h[1-6]$'))):
                return h.name[1] if element == tag else str(int(h.name[1]) + 1) if h.name[1] != '6' else '6'
    return '2' # TODO: find proper heading level

def original_page(tag, soup):
    page        = '?'
    decrement   = -1
    pagebreak   = None
    if (pagebreak   := tag.find_previous(attrs = {'epub:type':'pagebreak'})):
        decrement = 0
    elif (pagebreak := tag.find_next(attrs = {'epub:type':'pagebreak'})):
        decrement = 1

    if pagebreak:
        if 'title' in pagebreak.attrs.keys():
            page =  str(int(pagebreak['title']) - decrement)
        elif 'id' in pagebreak.attrs.keys():
            # TODO: check pagebreak['id'] for other languages
            # page =  str(int(pagebreak['id'].split('-')[-1]).group() - decrement)
            return '?'
        else:
            pbs = 0
            for soup in nordic.content:
                for pb in soup(attrs = {'epub:type':'pagebreak'}):
                    pbs += 1
                    if pb == pagebreak:
                        page = str(pbs)
    return page

def get_heading(tag, soup):
    # The specification only gives two option, but here we have the
    # possibility to expand the range of languages, thus:
    #   page = pages[soup.html['lang']] if soup.html['lang'] in pages.keys() else pages['en']

    page = PAGES['en'] if soup.html['lang'] == 'en' else PAGES['no']
    return page + ' ' + original_page(tag, soup) + ':'


def figure_to_table(docs, soup, figure):
    try:
        # =====================================================================
        # This part of the method is implemented using this article as a basis:
        # https://towardsdatascience.com/a-table-detection-cell-recognition-and-text-extraction-algorithm-to-convert-tables-to-excel-files-902edcf289ec
        # - viewed 04.05.2023

        # Reading file
        img = cv2.imread(docs + figure.img['src'], 0)
        img.shape

        # Thresholding the image to a binary image
        thresh,img_bin = cv2.threshold(img,128,255,cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # Inverting the image
        img_bin = 255-img_bin

        # countcol(width) of kernel as 100th of total width
        kernel_len  = np.array(img).shape[1]//100
        # Defining a vertical kernel to detect all vertical lines of image
        ver_kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
        # Defining a horizontal kernel to detect all horizontal lines of image
        hor_kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
        # A kernel of 2x2
        kernel      = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))

        #Use vertical kernel to detect and save the vertical lines in a jpg
        image_1         = cv2.erode(img_bin, ver_kernel, iterations=3)
        vertical_lines  = cv2.dilate(image_1, ver_kernel, iterations=3)

        #Use horizontal kernel to detect and save the horizontal lines in a jpg
        image_2             = cv2.erode(img_bin, hor_kernel, iterations=3)
        horizontal_lines    = cv2.dilate(image_2, hor_kernel, iterations=3)

        # Combine horizontal and vertical lines in a new third image, with both having same weight.
        img_vh          = cv2.addWeighted(vertical_lines, 0.5, horizontal_lines, 0.5, 0.0)
        img_vh          = cv2.erode(~img_vh, kernel, iterations=2)
        thresh, img_vh  = cv2.threshold(img_vh,128,255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        bitxor          = cv2.bitwise_xor(img,img_vh)
        bitnot          = cv2.bitwise_not(bitxor)

        # Detect contours for following box detection
        contours, hierarchy = cv2.findContours(img_vh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        def sort_contours(cnts, method='left-to-right'):
            # handle if we need to sort in reverse
            reverse = True  if method in ['right-to-left', 'bottom-to-top'] else False
            # handle if we are sorting against the y-coordinate rather than
            # the x-coordinate of the bounding box
            i       = 1     if method in ['top-to-bottom', 'bottom-to-top'] else 0

            # construct the list of bounding boxes and sort them from top to
            # bottom
            boundingBoxes           = [cv2.boundingRect(c) for c in cnts]
            (cnts, boundingBoxes)   = zip(*sorted(
                zip(cnts, boundingBoxes),
                key=lambda b:b[1][i], reverse=reverse))


            # return the list of sorted contours and bounding boxes
            return (cnts, boundingBoxes)

        # Sort all the contours by top to bottom.
        contours, boundingBoxes = sort_contours(contours, method='top-to-bottom')

        #Creating a list of heights for all detected boxes
        heights = [boundingBoxes[i][3] for i in range(len(boundingBoxes))]

        #Get mean of heights
        mean = np.mean(heights)

        #Create list box to store all boxes in
        box = []
        # Get position (x,y), width and height for every contour and show the contour on image
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if (w<1000 and h<500):
                image = cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),2)
                box.append([x,y,w,h])

        #Creating two lists to define row and column in which cell is located
        row     = []
        column  = []
        j       = 0

        #Sorting the boxes to their respective row and column
        for i in range(len(box)):
            if i == 0:
                column.append(box[i])
                previous = box[i]
            else:
                if(box[i][1] <= previous[1] + mean/2):
                    column.append(box[i])
                    previous = box[i]
                    if i == len(box)-1:
                        row.append(column)
                else:
                    row.append(column)
                    column      = []
                    previous    = box[i]
                    column.append(box[i])

        #calculating maximum number of cells
        countcol = 0
        for i in range(len(row)):
            countcol = len(row[i])
            if countcol > countcol:
                countcol = countcol

        #Retrieving the center of each column
        center = [int(row[i][j][0]+row[i][j][2]/2) for j in range(len(row[i])) if row[0]]
        center = np.array(center)
        center.sort()

        #Regarding the distance to the columns center, the boxes are arranged in respective order
        finalboxes = []
        for i in range(len(row)):
            lis = []
            for k in range(countcol):
                lis.append([])
            for j in range(len(row[i])):
                diff        = abs(center-(row[i][j][0]+row[i][j][2]/4))
                minimum     = min(diff)
                indexing    = list(diff).index(minimum)
                lis[indexing].append(row[i][j])
            finalboxes.append(lis)

        #from every single image-based cell/box the strings are extracted via pytesseract and stored in a list
        outer = []
        for i in range(len(finalboxes)):
            for j in range(len(finalboxes[i])):
                inner = ''
                if(len(finalboxes[i][j])==0):
                    outer.append(' ')
                else:
                    for k in range(len(finalboxes[i][j])):
                        y = finalboxes[i][j][k][0]
                        x = finalboxes[i][j][k][1]
                        w = finalboxes[i][j][k][2]
                        h = finalboxes[i][j][k][3]

                        finalimg    = bitnot[x:x+h, y:y+w]
                        kernel      = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
                        border      = cv2.copyMakeBorder(finalimg,2,2,2,2, cv2.BORDER_CONSTANT,value=[255,255])
                        resizing    = cv2.resize(border, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                        dilation    = cv2.dilate(resizing, kernel,iterations=1)
                        erosion     = cv2.erode(dilation, kernel,iterations=2)

                        out = pytesseract.image_to_string(erosion)
                        if(len(out)==0):
                            out = pytesseract.image_to_string(erosion, config='--psm 3')
                        inner = inner + ' ' + out
                    outer.append(inner)

        #Creating a dataframe of the generated OCR list
        arr     = np.array(outer)
        df      = pd.DataFrame(arr.reshape(len(row), countcol))
        data    = df.style.set_properties(align='left')

        # End of quoted method
        # =====================================================================

        table = BeautifulSoup(df.to_html(), 'html.parser')

        # TODO: Find better test
        return table if len(table('td', text=True)) * 4 > len(table('td', text=False)) else None

    except Exception as e: # work on python 3.x
        return None

def apply_requirements(soup, logger):

    # 2.1.1 CSS
    logger.info('2.1.1 - Copying css/ebok.css')
    if (css := soup.head.find('link', {'rel': 'stylesheet'})):
        css['href'] = 'css/ebok.css'
    else:
        soup.head.append(BeautifulSoup('<link rel="stylesheet" href="css/ebok.css">', features='lxml'))
        logger.warning('2.1.1 - Missing css/ebok.css')
    #copyfile(path.join(folders['static'], 'ebok.css'), path.join(folders['epub'], 'css', 'ebok.css'))

    # 2.1.2 Relocation of elements
    # TODO: This specification is unclear

    # 2.1.3 Uppercase text
    # TODO: Named entities
    # TODO: "Skriv! Reklame" becomes "skriv! Reklame"
    # TODO: "Å påstå at noe er «falske nyheter»" becomes "Å pÅstÅ at noe er «falske nyheter»"
    for h in soup(re.compile('^h[1-6]$')):
        if h.string:
            old = h.string
            h.string = h.string.lower()
            logger.info(f'2.1.3 - Uppercase: "{old}" -> "{h.string}"')
            for word in h.text.split():
                if word.isalpha():
                    if len(word)>1:
                        h.string = h.string.replace(word, word[0].upper() + word[1:])
                    else:
                        h.string = h.string.replace(word, word.upper())
                    break

    # 2.1.4 Blank pages in the original source
    for pagebreak in soup('div', attrs = {'epub:type':'pagebreak'}):
        logger.info(f'2.1.4 - Inserting "Blank side" before {pagebreak.get("id")}')
        if ((previous := pagebreak.find_previous_sibling()) and
            previous.name == 'div' and
            'epub:type' in previous.attrs.keys() and
            previous['epub:type'] == 'pagebreak'):
            p = soup.new_tag('p')
            p.append('Blank side.')
            pagebreak.insert_before(p)

    # 2.1.5 Blank pages where elements have been moved
    # TODO: Specify. No content has been moved yet

    # 2.1.6 Use of <em> and <strong>

    # 2.1.6.1 Do not use double emphasis
    for emphasis in soup(['em', 'strong']):
        parents = emphasis.parents
        emphs = [emphasis]
        logger.info(f'2.1.6.1 - Unwrapping double emphasis: {emphs}')
        for parent in emphasis.parents:
            if parent.name in ['em', 'strong']:
                emphs.append(parent)
        emphs.reverse()
        if len(emphs)>1:
            for emph in emphs[1:]:
                emph.unwrap()

    # 2.1.6.2 Headings in <em> or <strong>
    for h in soup(re.compile('^h[1-6]$')):
        for emphasis in h(['em', 'strong']):
            logger.info(f'2.1.6.2 - Unwrapping emphasis in {h}: {emphasis}')
            emphasis.unwrap()

    # 2.1.6.3 Use of <em> or <strong> in words and expressions
    # TODO:Check emphasis across punctuation
    for emphasis in soup(['em', 'strong']):
        # Move end punctuation outside emphasis
        if (emphasis.children and
            (last_child := list(emphasis.children)[-1]) and
            isinstance(last_child, NavigableString) and
            last_child.string and
            last_child.string[-1] in PUNCTUATION and
            len(last_child.string)>1):

            logger.info(f'2.1.6.3 - Moving punctuation outside emphasis: {emphasis}')
            punctuation = last_child.string[-1]
            last_child.string.replace_with(last_child.string[:-1])
            emphasis.insert_after(punctuation)

    # 2.1.6.4 Paragraphs in <em> or <strong>
    for emphasis in soup(['em', 'strong']):
        if emphasis.parent.name == 'p':
            if ((len(list(emphasis.parent.children)) == 1) or
                (len(list(emphasis.parent.children)) == 2 and
                 list(emphasis.parent.children)[-1].text in PUNCTUATION)):
                    # Because 2.1.6.3 already moves punctuation outside emphasis
                    logger.info(f'2.1.6.4 - Unwrapping emphasis in paragraph: {emphasis}')
                    emphasis.unwrap()

    # 2.1.6.5 Avoid use of <em> or <strong> in description lists
    for dl in soup('dl'):
        for emphasis in dl(['em', 'strong']):
            logger.info(f'2.1.6.5 - Unwrapping emphasis in description list: {emphasis}')
            emphasis.unwrap()

    # 2.1.6.6 Avoid use of <em> or <strong> in table headings
    for th in soup('th'):
        for emphasis in th(['em', 'strong']):
            logger.info(f'2.1.6.6 - Unwrapping emphasis in table heading: {emphasis}')
            emphasis.unwrap()

    # 2.1.6.7 Avoid use of <em> or <strong> in figures and figcaptions
    for figcaption in soup('figcaption'):
        for emphasis in figcaption(['em', 'strong']):
            logger.info(f'2.1.6.7 - Unwrapping emphasis in figcaption: {emphasis}')
            emphasis.unwrap()
    # See Nordic Guidelines 3.4.3.1
    for aside in soup('aside', attrs = {'class':'fig-desc'}):
        for emphasis in aside(['em', 'strong']):
            logger.info(f'2.1.6.7 - Unwrapping emphasis in aside: {emphasis}')
            emphasis.unwrap()

    # 2.1.7 Non-breaking space
    for element in soup(string=True):
        if (not 'class' in element.parent.attrs.keys() or
            not element.parent.attrs['class'] == 'asciimath'):
            if (len(element.string)>1 and
                set(SYMBOLS).intersection(set(element.string))):
                i = 0
                for c in element.string[:-1]:
                    if c in SYMBOLS and element.string[i+1] !='\u00A0':
                        logger.info(f'2.1.7 - Inserting non-breaking space: {element.string}')
                        element.string = element.string[:i] + c + '&#160;' + element.string[i+1:]
                    i += 1

    # 2.1.8 Table of contents
    # TODO: check where 'frontmatter toc' comes from
    if (toc := soup.find('section', attrs = {'epub:type':'frontmatter toc'})):
        logger.info('2.1.8 - Table of contents')
        for figure in toc('figure'):
            # TODO: check what to do with figures
            toc.insert_after(figure)
        for table in toc('table'):
            # TODO: make list
            pass
        for element in toc(string=True):
            element.string = element.string.lower()
        # TODO: check where '<span class="lic">' comes from
        for li in toc('li'):
            if len(list(li.children)) == 1:
                if (a := li.find('a')):
                    words = a.text.split()
                    if len(words)>1 and words[-1].isnumeric():
                        a.string = ''

                        second_span = soup.new_tag('span', attrs = {'class':'lic'})
                        second_span.string = words[-1]
                        a.insert(0, second_span)

                        first_span = soup.new_tag('span', attrs = {'class':'lic'})
                        first_span.string = ' '.join(words[:-1]) + ' '
                        a.insert(0, first_span)

    # 2.1.8.1 TOC at the beginning of the book
    for toc in soup(attrs={'epub:type':'toc'}):
        logger.info(f'2.1.8.1 - TOC at the beginning of the book')
        # Markup for table of content
        if toc.ol:
            toc.ol['class'] = 'list-type-none'
            toc.ol['style'] = 'list-style-type: none;'

        # Removing double whitespaces
        for tag in toc(text=True):
            re.sub(r'[ \t]{2,}', ' ', tag)

        # Single spaces between <span> elements
        for span in toc('span'):
            if (second_sibling := span.next_sibling):
                if second_sibling.text:
                    if (third_sibling := second_sibling.next_sibling):
                        if third_sibling.name == 'span':
                            second_sibling = ' '

    # 2.1.8.2 TOC at the beginning of each chapter
    # This requirement is covered by the implementation of SMR 2.1.8.1

    # 2.1.9 Backmatter

    # 2.1.9.1 Indexes and registers
    # TODO: Remove list of image credits
    for tag in soup(attrs={'epub:type':['index']}):
        # TODO: Other categories than index
        # TODO: For now it assumes that the markup is good
        if tag.table:
            tag.table.name   = 'ol'
            for tr in tag.table('tr'):
                tr.insert(0, (new_ol := soup.new_tag('ol')))
                for th in reversed(tr('th')):
                    th.name = 'li'
                    new_ol.insert(0, th.extract())
                tr.name = 'li'


    # 2.1.9.2 Answer sections for tasks
    # "...any reference sections that follow" is not clear
    if (backmatter := soup.find(attrs={'epub:type':'backmatter'})):
        for tag in backmatter(attrs={'epub:type':True}):
            if not tag['epub:type'] in ['answer', 'answer']:
                pass # TODO: move


    # 2.1.10 Layout challenges
    # This requirement not implementable

    # 2.1.11 Use of <hr> or <br>
    for tag in soup(['hr', 'br']):
        if not {'ol', 'ul'}.intersection(set([parent.name for parent in tag.parents])):
            tag.decompose()

    '''
    # 2.1.11.1 Use of <br> in mathematics books
    if args.mathematics:
        for tag in soup(text=True):
            if tag.next_sibling and tag.next_sibling.name == 'math':
                tag.insert_after(soup.new_tag('br'))
    '''

    # 2.1.12 OCR
    # This requirement is not implementable

    # 2.2 Thematic grouping of content

    # 2.2.1 Use of section within tasks
    # TODO: check <p epub:type="bridgehead">Oppgaver</p> as in 863500
    for tag in soup(attrs={'epub:type':ASSESSMENTS}):
        if tag.name != 'section':
            for parent in tag.parents:
                if parent.name == 'section':
                    if (parent.find(re.compile(r'^h[1-6]$')) and
                        len(parent(attrs={'epub:type':assessments}))>1):
                        tag.wrap(soup.new_tag('section', attrs={'epub:type':tag['epub:type']}))
                    break

    # 2.3 Figures/Images

    # 2.3.1 Alt tag
    # This requirement is a replica of NG 3.4.3.2,
    # and hence not implemented here.

    # 2.3.2 Extraction of text in figures
    # "...graphs, images of webpages or pictures of pages from books" are
    # difficult to identify without markup
    for img in soup('img', {'alt':['photo', 'map']}):
        if (img.parent.name == 'figure' and
            (aside := parent.find('aside', attrs={'class':'fig-desc'}))):
            aside.decompose()

    '''
    # 2.3.2.1 Extraction of text from figures in mathematics books
    if args.mathematics:
        for img in soup('img'):
            if (img.parent.name == 'figure' and
                (aside := parent.find('aside', attrs={'class':'fig-desc'}))):
                aside.decompose()
    '''

    # 2.3.3 Aside element for image description to be added later
    for figure in soup('figure', attrs={'alt':True}):
        aside = soup.new_tag('aside', attrs = {
            'class'     : 'prodnote',
            'epub:type' : 'z3998:production',
            'id'        : 'desc(x)'})
        aside.append('¤')
        figure.append(aside)

    # 2.3.4 Figcaptions
    for figcaption in soup('figcaption'):
        for tag in figcaption(['strong', 'em']):
            tag.unwrap()
        # Only one <p> in <figcaption> is here
        # defined as unnecessary
        if len(figcaption('p')) == 1:
            figcaption.p.unwrap()

    '''
    # 2.3.5 Placement of figure elements
    if not args.mathematics and not args.science:
        for figure in soup('figure'):
            if not is_task(figure) and 'relocated' not in figure.attrs.keys(): # TODO: is_task
                for parent in figure.parents:
                    if (h := parent.find(re.compile(r'^h[1-6]$'))):
                        if (figure.find_previous_sibling(h.name) and
                            figure.find_previous_sibling(h.name) == h):
                            children = parent(recursive=False)
                            children.reverse()
                            for child in children:
                                if not 'relocated' in child.attrs.keys() and child != figure:
                                    figure['relocated'] = True
                                    child.insert_after(figure)
                                    break
                            break
                        else:
                            pass # See SMR 2.3.5.1


    # 2.3.5.1 Figures at the start of each chapter, placed before the chapter heading
    if not args.mathematics and not args.science:
        for figure in soup('figure'):
            if 'relocated' not in figure.attrs.keys():
                for parent in figure.parents:
                    if ((h := parent.find(re.compile(r'^h[1-6]$'))) and
                        (figure.find_previous_sibling(h.name) and
                         figure.find_next_sibling(h.name) == h) and
                        (pb_h_before := h.find_previous_sibling(attrs={'epub:type':'pagebreak'})) and
                        (pb_figure_after := figure.find_next_sibling(attrs={'epub:type':'pagebreak'})) and
                        pb_h_before == pb_figure_after and
                        (pb_h_after := h.find_next_sibling(attrs={'epub:type':'pagebreak'}))):
                        figure['relocated'] = True
                        pb_h_after.insert_before(figure)
                        p = soup.new_tag('p')
                        p.append('Kapittelbildet er flyttet til neste side.')
                        h.insert_before(p)
    '''

    # 2.3.6 Figures in science books
    # Implemented in 2.3.5

    '''

    # 2.3.7 Figures in mathematics books
    # Mostly implemented by 2.3.2.1
     # Extracting text from <figure> tags and placing
    # it in a <p> before.
    if args.mathematics:
        for figure in soup('figure', text=True):
            p = soup.new_tag('p')
            p.insert(figure.text)
            figure.insert_before(p)

    # 2.3.7.1 Spreadsheets
    if args.mathematics:
        for figure in soup('figure'): # [:3]: #, attrs={'class':'image'}):
            if figure.find('img'):
                if (table := figure_to_table(nordic.docs, soup, figure)):
                    figure.insert_after(table)
    '''

    # 2.3.8 Comics, comic strips and graphic novels
    # TODO: Decide format and/or recognize format on source material
    # Possible format:
    #   - https://www.xml.com/pub/a/2001/04/18/comicsml.html
    # Category detection (comics) should be done elsewhere

    # 2.4 Lists

    for ol in soup('ol'):
        lis = ol('li', text=True)
        if len(ol('li')) == len(lis): # If not, the <ol> is not relevant
            first_words = [word_tokenize(li.get_text())[0] for li in lis]

            # 2.4.1 Ordered lists <ol>
            if len(first_words)>1 and first_words == (r := [str(n+1) for n in range(len(first_words))]):
                for li in lis:
                    if (tag := li.find(string=True)):
                        tag.string.replace_with(tag.string[len(first_words[lis.index(li)]):])

            if soup.html['lang'] in NUMBERS.keys():
                limit       = 5

                # 2.4.1.1 Lists with missing sequential values
                words = first_words if len(first_words)>limit else first_words[:limit]
                if all(word.lower() in NUMBERS[soup.html['lang']].keys() for word in words):
                    for li in lis:
                        # Setting EVERY value of <li> element for consistency
                        li['value'] = NUMBERS[soup.html['lang']][first_words[lis.index(li)]]

                # 2.4.1.2 Lists with reversed order
                word_numbers = list(NUMBERS[soup.html['lang']])
                if len(list(set(first_words))) == len(first_words) and set(first_words).issubset(word_numbers):
                    if (word_numbers := word_numbers[:word_numbers.index(first_words[0])]):
                        word_numbers.reverse()
                        if (word_numbers := word_numbers[:word_numbers.index(first_words[0])]):
                            ol['reversed'] = True

    # 2.4.1.3 List with non-standard numbering
    # This paragraph would already be implemented in the original file

    # 2.4.1.4 Jointly given answers in lists
    # Suggested way to solve:
    # If two identical list points are detected,
    # they are put together. TODO: check if this
    # is a good solution.

    # 2.4.2 Unordered lists <ul>
    for ul in soup('ul'):
        if all([li.text for li in ul('li')]):
            ul_bullets = [li.text[0] in BULLETS for li in ul('li')]
            if len(set(ul_bullets)) == 1 and ul_bullets[0] in BULLETS:
                ul['class'] = 'bullet'
                for tag in [tag in li(text=True) for li in ul('li')]:
                    tag.string.replace_with(tag.string[1:])
            if 'class' not in ul.attrs.keys() or ul['class'] != 'bullet':
                ul['class'] = 'list-unstyled'

    # 2.4.3 Avoid the use of <p> as children of <li> elements
    for list_tag in soup(['ol', 'ul']):
        for li in list_tag('li'):
            if len(li('p')) > 1:
                for p in li('p'):
                    p.insert_after(soup.new_tag('br'))
                    p.name = 'div'
            elif (p := li.find('p')):
                p.name = 'div'

    # 2.4.4 Description Lists
    for dl in soup('dl'):
        aside = None
        for parent in dl.parents:
            if parent.name == 'aside':
                aside = parent
                break
            elif parent.name in ('div', 'span'):
                parent.name = 'aside'
                aside       = parent
                break
        if aside:
            aside['class'] = 'glossary' # TODO: make other categories
            if not aside.find(re.compile(r'^h[1-6]$')):
                for parent in aside.parents:
                    if (parent_h := parent.find(re.compile(r'^h[1-5]$'))): # h6 would make overflow
                        h = soup.new_tag('h' + str(int(parent_h.name[1])+1))
                        if soup.html['lang'] in HEADINGS.keys():
                            heading = HEADINGS[soup.html['lang']]
                        else:
                            heading = HEADINGS['no']
                        h.append(heading)
                        aside.insert(0, h)
                        break

    # 2.4.4.1 Phonetics in description lists
    for dl in soup('dl'):
        for text in dl(text=True):
            ipa = re.search(r'\S+', text)  # Match one or more non-whitespace characters
            if ipa and is_valid_ipa(ipa.group(0)) and 'dt' not in [parent.name for parent in text.parents]:
                for parent in text.parents:
                    if parent.name == 'dl':
                        if (dt := parent.find('dt')):
                            if (dt_text := dt.find(string=True)):
                                dt_text.string.replace_with(dt_text.string + ' ' + ipa.group(0))
                                # TODO: Remove ipa from text
                                # TODO: Test

    # 2.4.4.2 Relocation of description lists
    for dl in soup('dl'):
        aside = None
        if 'aside' not in [parent.name for parent in dl.parents]:
            dl.wrap((aside := soup.new_tag('aside', attrs={'class':'glossary'})))
        else:
            for parent in dl.parents:
                if parent.name == 'aside':
                    aside = parent

        # TODO: Place these description lists together in a single <aside> at
        # the end of the appropriate section

        if 'class' not in aside.attrs.keys():
            aside['class'] = 'glossary'

        if not is_task(aside) and 'relocated_from' not in aside.attrs.keys():
            if not (h := aside.find(re.compile(r'^h[1-6]$'))):
                aside.insert(0, (h := soup.new_tag('h' + find_header_level(aside))))

            heading = get_heading(aside, soup)
            h.append(soup.new_tag('br')) if h.text else '' # TODO: check newline in html
            h.append(heading)

            aside['relocated'] = True
            for parent in aside.parents:
                if parent.name == 'section': # TODO: open up for other structures
                    aside['relocated']      = True
                    aside['relocated_from'] = original_page(aside, soup)
                    # TODO: Note! In cases where a glossary list belongs exclusively to a box...
                    '''
                    if not nordic.box_related:
                        nordic.relocate_before_tasks(parent, aside)
                    '''

    # 2.5 Tasks
    for task in soup(ASSESSMENTS): # ?
        for parent in task.parents:
            if parent.name == 'section':
                if 'class' not in parent.attrs.keys():
                    parent['class'] = 'task'
                else:
                    task.wrap((section := soup.new_tag('section', attrs={'class':'task'})))

    # 2.5.1 Specialized task mark-up

    # 2.5.1.1 Main task headings
    for task in get_tasks(soup):
        h = soup.new_tag('h' + find_header_level(task))
        h.append(get_heading())
        task.insert(0, h)
        # TODO: This method follows the specification, but
        # it is not optimal. Maybe a revision would do good.

    # 2.5.1.2 Individual task headings
    for task in get_tasks(soup):
        for list_tag in task(re.compile(r'^[ou]l$')): # TODO: check other patterns for ind. tasks
            if (h := list_tag.find(re.compile(r'^h[1-6]$'))):
                h.insert(0, get_heading() + ': ')
            else:
                h = soup.new_tag('h' + find_header_level(list_tag))
                h.append(get_heading())
                list_tag.insert(0, h)

    # 2.5.1.3 Subordinate task headings
    tasks = 0
    for task in get_tasks(soup):
        for list_tag in task(re.compile(r'^[ou]l$')):
            tasks += 1
            subtasks = 96 # Because chr(97) == 'a'
            if list_tag.name != 'ol':
                for li in list_tag('li'):
                    subtasks += 1
                    if (h := li.find(re.compile(r'^h[1-6]$'))):
                        h.insert(0, get_heading() + ' ' + str(tasks) + chr(subtasks) + ': ')
                    else:
                        li.insert(0, (h := soup.new_tag('h' + find_header_level(li))))
                        h.append(get_heading() + ' ' + str(tasks) + chr(subtasks) + ':')

    # 2.5.1.4 Use of section-elements in tasks
    for task in get_tasks(soup):
        if task.parent.name != 'section':
            task.wrap(soup.new_tag('section', attrs = {'class':'task'}))
    for answer in get_answers(soup):
        answer['class'] = 'key'

    # 2.5.1.5 Symbols for task types
    for task in get_tasks(soup):
        pass # TODO: implement as interface

    # 2.5.1.6 Match problems
    for tag in soup(attrs={'epub:type':'match-problem'}):
        for h in tag(re.compile(r'^h[1-6]$')):
            h.name = 'p'
            if not h.find('strong'):
                strong = soup.new_tag(strong)
                for content in reversed(h.contents):
                    strong.insert(0, content.extract())
        for ul in tag('ul'):
            ul['class'] = 'list-unstyled'

    # 2.5.1.7 Fill-in-the-blank tasks
    for tag in soup(attrs={'epub:type':'fill-in-the-blank-problem'}):
        for subtag in tag(string=True):
            subtag.string.replace_with(re.sub('_{2,}', '....', subtag.string))

    # 2.5.1.8 Fill in the correct form – words given
    for tag in soup(attrs={'epub:type':'fill-in-the-blank-problem'}):
        if (answer := tag.find(attrs={'epub:type':'answer'})):
            if (question := tag.find(attrs={'epub:type':'question'})):
                question.insert(len(question.content), ' (')
                question.insert(len(question.content), answer)
                question.insert(len(question.content), ' )')

    # 2.5.1.9 Tasks which include lines for answers
    # TODO: Check practices for how lines for answers are notated

    # 2.5.1.10 Crossword puzzles
    # TODO: check how crosswords are marked up in original

    # 2.5.1.11 Tables with one letter in each cell (Word search)
    for table in soup('table'):
        if all([(th.string and len(str(th.string)) == 1) for th in table('td')]):
            table.name = 'figure'
            for tr in table('tr'):
                tr.name = 'p'
                for cell in tr(['th', 'td']):
                    tr.append(cell.string + ' ')
                    cell.decompose()
                tr.string = str(tr.string).strip()

    # 2.5.1.12 Tasks with figures
    # Follows from SMR 2.1.2, SMR 2.3.5 and SMR 2.4.4.2

    # 2.5.1.13 Tasks designed as boardgames
    # TODO: check formatting in source

    # 2.5.1.14 Unformatted lists without bullets within tasks <ul class=”list-unstyled”>
    for task in soup(attrs={'epub:type':ASSESSMENTS}):
        for ul in task('ul'):
            ul['class'] = 'list-unstyled'
        # TODO: check consecutive <p> elements and convert to <ul>

    # 2.5.1.15 Lists of tasks with non-standard numbering
    for list_element in soup(['ol', 'ul']):
        if is_task(list_element) or is_part_of_task(list_element):
            if nordic.is_non_standard_list(list_element):
                list_element['class'] = 'list-type-none'
                list_element['style'] = 'list-style-type: none;'

    # 2.5.1.16 Tasks where examples of answers are given
    for list_element in soup('ol', 'ul'):
        if is_task(list_element) or is_part_of_task(list_element):
            pass
            # TODO: check format

    # 2.5.1.17 Tasks with ticking boxes
    # TODO: Check formatting

    # 2.5.1.18 Tasks with tables better represented as lists
    # TODO: make parameter option

    # 2.5.1.19 Tasks with text between subtasks
    for task in soup(attrs={'epub:type':ASSESSMENTS}):
        for subtask in task(attrs={'epub:type':ASSESSMENTS}):
            if subtask.previous_sibling and not is_task(subtask.previous_sibling):
                subtask.previous_sibling.wrap((div := soup.new_tag('div', attrs={'class':'extra-text'})))
                subtask.insert(0, div)

    '''
    # 2.5.2 Tasks in mathematics books
    if args.mathematics:
        for task in soup(attrs={'epub:type':ASSESSMENTS}):
            for subtask in task(attrs={'epub:type':ASSESSMENTS}):
                subtask.wrap((section := soup.new_tag('section', attrs={'class':'task'})))
                section.insert(0, (h := soup.new_tag('h' + find_header_level(subtask))))
    '''

    # 2.6 Sidebars, text boxes etc.
    for aside in soup('aside'):
        aside['class'] = 'generisk-ramme'

    '''
    # 2.6.1 Boxes in mathematics books
    if args.mathematics:
        for aside in soup('aside'):
            aside.name = 'div'
    '''

    # 2.7 Comments in the margin
    # TODO: find examples and original markup

    # 2.8 Texts with specific styles

    # 2.8.1 Plays and screenplays
    # TODO: find formatting. Make interactive

    # 2.9 Page breaks
    pagebreaks = (list(soup('span', attrs={'epub:type':'pagebreak'})) +
                  list(soup('span', attrs={'role':'doc-pagebreak'})))
    for pagebreak in pagebreaks:
        for parent in pagebreak.parents:
            if not parent.name in BLOCK_ELEMENTS:
                pagebreak.name          = 'div'
                pagebreak['epub:type']  = 'pagebreak'

    # 2.9.1 Relocation of page breaks
    for pagebreak in soup(attrs={'epub:type':'pagebreak'}):

        # Lists
        if {'ol','ul'}.intersection(set([parent.name for parent in pagebreak.parents])):
            for parent in reversed(list(pagebreak.parents)):
                if parent.name in ['ol', 'ul']:
                    parent.insert_before(pagebreak)
                    break

        # Paragraphs
        if 'p' in [parent.name for parent in pagebreak.parents]:
            for parent in pagebreak.parents:
                if parent.name == 'p':
                    parent.insert_after(pagebreak)
                    break

        # Headings
        elif [parent for parent in pagebreak.parents if parent.name and re.compile(r'^h[1-6]$').match(parent.name)]:
            for parent in pagebreak.parents:
                if re.compile(r'^h[1-6]$').match(parent.name):
                    parent.insert_before(pagebreak)
                    break

        # Sentences
        # NOTE: This bit alters slightly the specification
        # by moving the pagebreak to the beginning of the
        # paragraph, rather than the end of the sentence.
        elif pagebreak.parent.name == 'p':
            pagebreak.parent.insert(0, pagebreak)

    # 2.10 Tables
    for table in soup('table'):
        if not table.find(['thead','tbody']):
            thead = soup.new_tag('thead')
            tbody = soup.new_tag('tbody')
            table.append(thead)
            table.append(tbody)
            for tr in table('tr'):
                if tr.find('th'):
                    thead.insert(len(thead.contents), tr)
                else:
                    tbody.insert(len(tbody.contents), tr)

    # 2.10.1 Table titles
    for table in soup('table'):

        # Convert title attribute to <caption>
        if 'title' in table.attrs.keys() and not table.find('caption'):
            table.insert(0, (caption := soup.new_tag('caption')))
            caption.append(table['title'])

        # Move <caption> to the beginning of <table>
        if (caption := table.find('caption')):
            table.insert(0, caption)

        # Convert initial one-cell row to caption
        max_cells = 0
        for tr in table('tr'):
            if len(tr(['th', 'td'])) > max_cells:
                max_cells = len(tr(['th', 'td']))
        if max_cells > 1:
            if ((first_row := table.find('tr'))(['th', 'td'])) == 1:
                first_row.name = 'caption'
                first_row.find(['th', 'td']).unwrap()
                del first_row['colspan']
                table.insert(0, first_row)

        # "Flag cell"
        tr = table.find('tr')
        if len(tr(['th', 'td'])) == 2 and tr.find(attrs={'style':'visibility: collapse'}):
            for cell in tr(['th', 'td']):
                if 'style' not in cell.attrs.keys() or cell['style'] != 'visibility: collapse':
                    cell.name = 'caption'
                    table.insert(0, cell)
                    tr.decompose()

    # 2.10.2 Tables without clear boundaries between rows or columns
    # This does not apply in electronic books

    # 2.10.3 Avoid use of <em> or <strong> in <th>
    for table in soup('table'):
        for em in table(['em', 'strong']):
            em.unwrap()

    # 2.10.4 Avoid use of <p> within table cells
    for cell in soup(['th', 'td']):
        # Only one <p> is deemed redundant. TODO: check other options
        if len(cell('p')) == 1:
            # cell.p.unwrap()
            pass # The <p> might be necessary for the spine

    # 2.10.5 Lists within tables
    # Already implemented by SMR 2.4

    # 2.10.6 Tables where all table cells are empty
    # TODO: Check lists marked up as figures?
    for table in soup('table'):
        if (all([not cell.text or re.compile(r' +').match(cell.text) for cell in table('td')]) and
            (ths := table('th', text=True))):
            figure      = soup.new_tag('figure')
            headings    = [th.string for th in table('th')]
            ol          = soup.new_tag('ol')
            for th in ths:
                ol.append((li := soup.new_tag('li')))
                li.append(th.get_text())
            figure.append(ol)
            table.insert_before(figure)
            table.decompose()

    # 2.10.7 Do not use tables purely as a formatting tool
    # TODO: The conversion of table to list should be done interactively

    # 2.10.8 Spreadsheets as tables
    # This requirement should be covered by SMR 2.3.7.1

    # 2.11 Quotations, blockquotes, sources
    for blockquote in soup('blockquote'):
        if not blockquote.parent.find('cite'):
            pass # TODO: Deal with this interactively

    # 2.12 Footnotes and endnotes

    # 2.12.1 Footnotes
    for fn in list(soup('fn')) + list(soup(attrs={'epub:type':'footnote'})):
        for parent in fn.parents:
            if parent.name == 'section':
                parent.insert(len(parent.contents), fn)
                while fn.previous_sibling.name in ['glossary', 'dl']:
                    fn.previous_sibling.insert_before(fn)
                break

    # 2.12.2 Endnotes and chapter notes
    endnotes = soup(attrs={'epub:type':'endnotes'})
    if len(endnotes) == 1:
        for parent in reversed(list(endnotes[0].parents)):
            if parent.name == 'section':
                parent.insert(len(parent.contents), endnotes[0])
                break
    else:
        for endnote in endnotes:
            for parent in endnote.parents:
                if (parent.name == 'section' and
                    'epub:type' in parent.attrs.keys() and
                    parent['epub:type'] == 'bodymatter chapter'):
                    parent.insert(len(parent.contents), endnote)

    '''
    all_endnotes = []

    for endnotes in soup(attrs={'epub:type':'endnotes'}):
        all_endnotes.append(endnotes)
        if not endnotes.name == 'section':
            endnotes.wrap((endnotes :=soup.new_tag('section', attrs={'epub:type':'endnotes'})))
        for parent in reversed(list(endnotes.parents)):
            if parent.name == 'section':
                parent.insert(len(parent.contents), endnotes)
                endnotes['relocated']       = True
                endnotes['relocated_from']  = original_page(endnotes, soup)

    if not all_endnotes:
        last_soup       = nordic.content[-1]
        upper_section   = last_soup.find('section')
        endnotes        = last_soup.new_tag('section', attrs={'epub:type':'endnotes'})
        if not upper_section == endnotes:
            upper_section.insert(len(section.contents), endnotes)
        for soup in nordic.content:
            for endnote in soup(attrs={'epub:type':'endnote'}):
                endnotes.insert(len(endnotes.contents), endnote)
    '''

    # 2.13 Grammar

    # 2.13.1 Sentence analysis
    # TODO: Find common formatting. Here is one example from 861800

    # 2.13.2 Conjugation tables
    # TODO: The only relevant thing here is turning the table into
    # a list. Make interactive.

    # 2.14 Poems
    # TODO: Check original formats. This needs to be interactive

    '''

    # 2.15 Inline language markup
    word_limit  = 4 # Single word tests are too insecure
    languages   = {}

    languages[soup.html['lang']] = spacy.load(LANGUAGE_MODELS[soup.html['lang']])
    languages[soup.html['lang']].add_pipe('language_detector')

    # This must be done first to establish given languages
    for tag in soup(attrs={'lang':True}):
        if tag['lang'] not in languages.keys():
            languages[tag['lang']] = spacy.load(nordic.language_models[tag['lang']])
            languages[tag['lang']].add_pipe('language_detector')

    for tag in soup(string=True):
        if (string := str(tag.string).strip()):
            parent_tag  = None
            language    = soup.html['lang']

            for parent in list(tag.parents)[:-3]: # body, html and [document] should not be altered
                if 'lang' in parent.attrs.keys():
                    language = parent['lang']
                    break

            if len(str(tag.string).split(' ')) > word_limit:
                doc = languages[language](str(tag.string))
                if language != doc._.language: # TODO: and not {language, doc._.language} == {'nb', 'no'}:
                    if doc._.language in languages.keys():
                        if parent == tag.parent:
                            parent['lang'] = doc._.language
                        else:
                            tag.parent['lang'] = doc._.language

    # TODO: detect unspecified languages

    '''

    '''
    # 2.16 Mathematics
    if args.mathematics or args.science:
        pass # TODO: This section is deprecated, given that MathML is the new standard
        # TODO: Await new mathematics standard

    return soup
    '''

def run_xslt(input_xml, stylesheet, output_xml):
    print("Running XSLT transformation...")
    saxon_command = [
        'java', '-jar', 'saxon/saxon-he-10.5.jar',
        '-s:' + input_xml,
        '-xsl:' + stylesheet,
        '-o:' + output_xml,
    ]

    try:
        subprocess.run(saxon_command, check=True)
        print("XSLT transformation successful.")
    except subprocess.CalledProcessError as e:
        print("XSLT transformation failed:", e)

def convert_epub(args, logger):

    production_number   = path.splitext(path.basename(args.input))[0]
    output_file         = path.join(getcwd(), f'{production_number}.epub')
    old_xhtml_files = []

    # Set up structure
    # ----------------

    # Open the epub file and extract all the files
    # into a temporary directory
    #with ZipFile(args.input, 'r') as epub:
    tmp = path.join(getcwd(), 'tmp')
    folders = {
            'cwd'       : getcwd(),
            'result'    : path.join(getcwd(), 'result'),
            'output'    : path.join(getcwd(), 'result', production_number),
            'static'    : path.join(getcwd(), 'static'),
            'tmp'       : tmp,
            'source'    : path.join(tmp, 'source'),
            'target'    : path.join(tmp, 'target'),
            'root'      : path.join(tmp, 'target'),
            'epub'      : path.join(tmp, 'target', 'EPUB'),
            }

    output_folder = path.join(folders['result'], production_number)
    rmtree(folders['result'], ignore_errors=True)
    rmtree(folders['tmp'], ignore_errors=True)
    mkdir(folders['result'])
    mkdir(folders['output'])
    mkdir(folders['tmp'])
    mkdir(folders['source'])

    #epub.extractall(folders['source'])
    copytree(args.input, folders['source'], dirs_exist_ok=True)
    rmtree(path.join(folders['source'], '__MACOSX'), ignore_errors=True)
    copytree(path.join(folders['source']), folders['target'])

    # Create the soup object
    xhtml_path = find_xhtml(production_number, folders['epub'])
    with open(xhtml_path, 'r') as xhtml:
        soup = BeautifulSoup(xhtml.read(), 'xml')

    # Apply Statped Mark-up Requirements
    # ----------------------------------
    soup = apply_requirements(soup, logger, folders, args)

    # Clean up the soup object
    # ------------------------

    # Remove wrapping sections
    for section in [s for s in soup('section') if s.attrs == {}]:
        section.unwrap()

    # Set pagebreak title
    for pagebreak in soup(attrs={'epub:type':'pagebreak'}):
        pagebreak['title'] = pagebreak['aria-label']

    # Remove "relocated" attributes
    for tag in soup(attrs={'relocated':True}):
        del tag['relocated']

    # Remove "relocated_from" attributes
    for tag in soup(attrs={'relocated_from':True}):
        del tag['relocated_from']

    '''
    # Remove <li> wrapping <li>
    for li in soup('li'):
        if li.li:
            li.li.unwrap()
    '''

    # Create a new epub file
    # ----------------------

    output      = args.output if args.output else path.join(folders['result'], f'{production_number}.epub')
    language    = f'''lang="{soup.html['lang']}" xml:lang="{soup.html['lang']}"'''

    # Save soup into a new xhtml file
    del soup.html['lang']
    with open(path.join(folders['epub'], f'{production_number}.xhtml'), 'w') as content:
        content.write(str(soup).replace('<html>', f'<html {correct_html_tag} {language}>'))

    '''
    # Create epub file
    with ZipFile(output_file, 'w') as epub:
        epub.write(path.join(folders['root'], 'mimetype'), 'mimetype')
        for root, _, files in walk(path.join(folders['root'])):
            for file in files:
                if path.join(root, file) != path.join(folders['root'], 'mimetype'):
                    epub.write(path.join(root, file),
                               path.relpath(path.join(root, file), folders['root']),
                               compress_type=ZIP_DEFLATED)
    '''

    # Create nav.xhtml
    # ----------------
    run_xslt(path.join(folders['epub'], f'{production_number}.xhtml'),
             path.join(folders['static'], 'html-to-nav.xsl'),
             path.join(folders['epub'], 'nav.xhtml'))

    # Move the new epub file to the result folder
    #move(f'{production_number}.epub', folders['result'])
    copytree(folders['epub'], folders['output'], dirs_exist_ok=True)

    '''
    # Validate epub
    # -------------
    result = EpubCheck(f'result/{output_file}')
    print(result.valid)
    print(result.messages)
    '''

# MAIN
# ====

def main():
    # Parse command line arguments
    parser = ArgumentParser(description='''
        Convert an epub conforming to the Nordic Guidelines for the
        Production of Accessible EPUB 3 to an epub conforming to the
        Statped Mark-up Requirements specification.
        ''')

    parser.add_argument('input',
                        help = 'The input folder')
    parser.add_argument('-o',
                        '--output',
                        help = 'The output epub file')
    parser.add_argument('-m',
                        '--mathematics',
                        help = 'The epub is a mathematics book',
                        action = 'store_true')
    parser.add_argument('-s',
                        '--science',
                        help = 'The epub is a sience book',
                        action = 'store_true')
    parser.add_argument('-v',
                       '--verbose',
                       help = 'Increase output verbosity',
                       action = 'store_true')

    args = parser.parse_args()

    # Set up logger
    logger = getLogger(__name__)

    # Convert epub
    convert_epub(args, logger)


if __name__ == '__main__':
    main()
