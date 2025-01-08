'''
This script converts MathML to StatpedMath format.
It can be used as a module taking a MathML tag as input and returning a StatpedMath tag as output,
or as a standalone script taking an EPUB file as input and returning a StatpedMath file as output.

Usage:
    python mathml2statpedmath.py -i math_text.xhtml -o math_text.xhtml

Arguments:
    -i, --input     Input file
    -o, --output    Output file

Sources:

    https://developer.mozilla.org/en-US/docs/Web/MathML/Element
    https://www.statped.no/laringsressurser/syn/matematikk-med-leselist-8.13.-trinn/
    https://www.w3.org/TR/mathml4/
    https://developer.mozilla.org/en-US/docs/Web/MathML

Exceptions:

    3.2.3 Streker under svar

Specifications:

    - Matematikk med leselist, Metodisk veiledning for lærere til elever på 8. – 13. trinn som bruker punktskrift (MML)
    - notasjon Veileder 8-punkts (NV8)
'''

# TODO: Logging
# TODO: Error handling
# TODO: Tallmengder
# TODO: Greek letters - also as indicators
# TODO: Double underline for answers

# TODO: VALIDATION - should be done in the DTValidator
'''
from lxml import etree

# MathML DTD URL
mathml_dtd_url = "https://www.w3.org/Math/DTD/mathml3/mathml3.dtd"

# Last inn MathML-DTD
dtd = etree.DTD(mathml_dtd_url)

# MathML-eksempel
mathml = """
<math xmlns="http://www.w3.org/1998/Math/MathML">
    <mi>x</mi>
    <mo>=</mo>
    <mn>5</mn>
</math>
"""

# Last MathML som XML
xml_doc = etree.XML(mathml)

# Valider mot DTD
if dtd.validate(xml_doc):
    print("MathML is valid!")
else:
    print("MathML is invalid!")
    print(dtd.error_log)

# ... or locally

from lxml import etree

# Last inn MathML-DTD fra lokal fil
dtd_path = "C:/mathml_schemas/mathml3.dtd"
with open(dtd_path, 'rb') as f:
    dtd = etree.DTD(f)

# MathML-eksempel
mathml = """
<!DOCTYPE math SYSTEM "mathml3.dtd">
<math xmlns="http://www.w3.org/1998/Math/MathML">
    <mi>x</mi>
    <mo>=</mo>
    <mn>5</mn>
</math>
"""

# Parse MathML som XML
xml_doc = etree.XML(mathml)

# Valider mot DTD
if dtd.validate(xml_doc):
    print("MathML is valid!")
else:
    print("MathML is invalid!")
    print(dtd.error_log)
'''

# IMPORTS
# =======

from sys        import argv
from os         import path
from bs4        import BeautifulSoup, Tag
from argparse   import ArgumentParser, RawDescriptionHelpFormatter
from textwrap   import dedent
from re         import sub
from logging    import basicConfig, getLogger, INFO


# VARIABLES
# =========

testfile = path.join('files', 'math.xhtml')

# Logging
basicConfig(level = INFO)
logger = getLogger(__name__)

BRACKETS = ['(', ')', '[', ']', '{', '}']

OPERATORS = {
        # Uncommon operators, not in the unicode table, but used by India
        '…' : ' ....',
        '□' : ' ....',

        # Common operators, not in the unicode table
        '+' : ' +',
        '*' : ' *',
        '·' : ' *',
        '×' : ' xx',
        '/' : '/',
        ':' : ' :',
        '<' : ' <',
        '>' : ' >',
        '=' : ' =',
        '±' : ' +-',
        '¬' : ' not ',
        '!' : '!',
        '~' : ' ~',
        '%' : ' %',
        '‰' : ' ‰',

        # Invisible operators
        '\u2061' : '', # Function application
        '\u2062' : '', # Invisible times
        '\u2063' : '', # Invisible separator

        # Other unicode operators
        '\u2190'    : ' <- ', # Leftwards arrow
        '←'         : ' <- ', # Leftwards arrow
        '\u2191'    : ' ^ ', # Upwards arrow
        '\u2192'    : ' -> ', # Rightwards arrow
        '→'         : ' -> ', # Rightwards arrow
        '\u2193'    : ' v ', # Downwards arrow
        '\u2194'    : ' <-> ', # Left right arrow
        '↔'         : ' <-> ', # Left right arrow
        '\u21D2'    : ' => ', # Rightwards double arrow
        '⇒'         : ' => ', # Rightwards double arrow
        '\u21CF'    : ' !=> ', # Rightwards double arrow
        '⇏'         : ' !=> ', # Rightwards double arrow
        '\u21D0'    : ' <= ', # Leftwards double arrow
        '⇐'         : ' <= ', # Leftwards double arrow
        '\u21CD'    : ' !<= ', # Leftwards double arrow
        '⇍'         : ' !<= ', # Leftwards double arrow
        '\u21D4'    : ' <=> ', # Left right double arrow
        '⇔'         : ' <=> ', # Left right double arrow
        '\u21CE'    : ' !<=> ', # Left right double arrow
        '⇎'         : ' !<=> ', # Left right double arrow
        '\u2032'    : "'", # Prime
        '\u2033'    : "''", # Double prime
        '\u2034'    : "'''", # Triple prime
        '\u03C3'    : '`s', # Sigma - Standard deviation

        # Enclosures - not strictly operators
        '(' : '(',
        ')' : ')',
        '[' : '[',
        ']' : ']',
        '{' : '{',
        '}' : '}',
        '|' : ' | ',

        # Comma - for vectors, etc.
        ','     : ', ',
        ',...'  : ',... ',
        
        # Refer to https://www.unicode.org/charts/PDF/U2200.pdf
        '∀' : ' AA',
        '∁' : '',
        '∂' : '',
        '∃' : ' EE',
        '∄' : '',
        '∅' : 'O/', # Could also be tagged as <mi>∅</mi>
        '∆' : ' /_\\',
        '∇' : '',
        '∈' : ' in',   
        '∉' : ' !in',
        '∊' : '',
        '∋' : '',
        '∌' : '',
        '∍' : '',
        '∎' : '',
        '∏' : '',
        '∐' : '',
        '∑' : '',
        '−' : ' \u2212',
        '∓' : ' \u2212+',
        '∔' : '',
        '∕' : ' /',
        '∖' : ' \\ ',
        '∗' : ' *',
        '∘' : '',
        '∙' : ' *',
        '√' : '',
        '∛' : '',
        '∜' : '',
        '∝' : ' prop ',
        '∞' : 'oo',
        '∟' : '',
        '∠' : ' /_',
        '∡' : '',
        '∢' : '',
        '∣' : '',
        '∤' : '',
        '∥' : ' ||',
        '∦' : ' !||',
        '∧' : ' ^^ ',
        '∨' : ' vv ',
        '∩' : ' nn ',
        '∪' : ' uu ',
        '∫' : '',
        '∬' : '',
        '∭' : '',
        '∮' : '',
        '∯' : '',
        '∰' : '',
        '∱' : '',
        '∲' : '',
        '∳' : '',
        '∴' : '',
        '∵' : '',
        '∶' : '',
        '∷' : '',
        '∸' : '',
        '∹' : '',
        '∺' : '',
        '∻' : '',
        '∼' : '',
        '∽' : '',
        '∾' : '',
        '∿' : '',
        '≀' : '',
        '≁' : '',
        '≂' : '',
        '≃' : '',
        '≄' : '',
        '≅' : ' ~=',
        '≆' : '',
        '≇' : '',
        '≈' : ' ~~',
        '≉' : '',
        '≊' : '',
        '≋' : '',
        '≌' : '',
        '≍' : '',
        '≎' : '',
        '≏' : '',
        '≐' : '',
        '≑' : '',
        '≒' : '',
        '≓' : '',
        '≔' : '',
        '≕' : '',
        '≖' : '',
        '≗' : '',
        '≘' : '',
        '≙' : '',
        '≚' : '',
        '≛' : '',
        '≜' : '',
        '≝' : '',
        '≞' : '',
        '≟' : '',
        '≠' : ' !=',
        '≡' : ' \u2212=',
        '≢' : '',
        '≣' : '',
        '≤' : ' <=',
        '≥' : ' >=',
        '≦' : '',
        '≧' : '',
        '≨' : '',
        '≩' : '',
        '≪' : '',
        '≫' : '',
        '≬' : '',
        '≭' : '',
        '≮' : '',
        '≯' : '',
        '≰' : '',
        '≱' : '',
        '≲' : '',
        '≳' : '',
        '≴' : '',
        '≵' : '',
        '≶' : '',
        '≷' : '',
        '≸' : '',
        '≹' : '',
        '≺' : '',
        '≻' : '',
        '≼' : '',
        '≽' : '',
        '≾' : '',
        '≿' : '',
        '⊀' : '',
        '⊁' : '',
        '⊂' : ' subset',
        '⊃' : ' supset',
        '⊄' : ' !subset',
        '⊅' : ' !supset',
        '⊆' : ' subseteq',
        '⊇' : '',
        '⊈' : ' !subseteq',
        '⊉' : '',
        '⊊' : '',
        '⊋' : '',
        '⊌' : '',
        '⊍' : '',
        '⊎' : '',
        '⊏' : '',
        '⊐' : '',
        '⊑' : '',
        '⊒' : '',
        '⊓' : '',
        '⊔' : '',
        '⊕' : '',
        '⊖' : '',
        '⊗' : '',
        '⊘' : '',
        '⊙' : '',
        '⊚' : '',
        '⊛' : '',
        '⊜' : '',
        '⊝' : '',
        '⊞' : '',
        '⊟' : '',
        '⊠' : '',
        '⊡' : '',
        '⊢' : '',
        '⊣' : '',
        '⊤' : '',
        '⊥' : ' _|_',
        '⊦' : '',
        '⊧' : '',
        '⊨' : '',
        '⊩' : '',
        '⊪' : '',
        '⊫' : '',
        '⊬' : '',
        '⊭' : '',
        '⊮' : '',
        '⊯' : '',
        '⊰' : '',
        '⊱' : '',
        '⊲' : '',
        '⊳' : '',
        '⊴' : '',
        '⊵' : '',
        '⊶' : '',
        '⊷' : '',
        '⊸' : '',
        '⊹' : '',
        '⊺' : '',
        '⊻' : '',
        '⊼' : '',
        '⊽' : '',
        '⊾' : '',
        '⊿' : '',
        '⋀' : '',
        '⋁' : '',
        '⋂' : '',
        '⋃' : '',
        '⋄' : '',
        '⋅' : '',
        '⋆' : '',
        '⋇' : '',
        '⋈' : '',
        '⋉' : '',
        '⋊' : '',
        '⋋' : '',
        '⋌' : '',
        '⋍' : '',
        '⋎' : '',
        '⋏' : '',
        '⋐' : '',
        '⋑' : '',
        '⋒' : '',
        '⋓' : '',
        '⋔' : '',
        '⋕' : '',
        '⋖' : '',
        '⋗' : '',
        '⋘' : '',
        '⋙' : '',
        '⋚' : '',
        '⋛' : '',
        '⋜' : '',
        '⋝' : '',
        '⋞' : '',
        '⋟' : '',
        '⋠' : '',
        '⋡' : '',
        '⋢' : '',
        '⋣' : '',
        '⋤' : '',
        '⋥' : '',
        '⋦' : '',
        '⋧' : '',
        '⋨' : '',
        '⋩' : '',
        '⋪' : '',
        '⋫' : '',
        '⋬' : '',
        '⋭' : '',
        '⋮' : '',
        '⋯' : '',
        '⋰' : '',
        '⋱' : '',
        '⋲' : '',
        '⋳' : '',
        '⋴' : '',
        '⋵' : '',
        '⋶' : '',
        '⋷' : '',
        '⋸' : '',
        '⋹' : '',
        '⋺' : '',
        '⋻' : '',
        '⋼' : '',
        '⋽' : '',
        '⋾' : '',
        '⋿' : '',
        }


ROMAN_NUMERALS = {
        'I' : 1,
        'V' : 5,
        'X' : 10,
        'L' : 50,
        'C' : 100,
        'D' : 500,
        'M' : 1000,
        }

NON_SPACE_SYMBOLS = [
        '%',
        '%%',
        "'",
        "''",
        'n',
        ] # TODO: check if degrees vs angle

# FUNCTIONS
# =========

def number_to_string(number):
    # TODO: review in accordance to what comes from India
    # For now '.' as decimal separator is assumed and
    # nothing else
    parts = number.split('.')
    new_parts = []

    part = parts[0]
    if len(part) > 4:
        new_part = ''
        i = 0
        for c in part[::-1]:
            new_part += c
            i += 1
            if i == 3 and len(new_part) != part:
                new_part += '.'
                i = 0
        new_parts.append(new_part[::-1])
    else:
        new_parts.append(part)

    if len(parts)>1:
        part = parts[1]
        if len(part) > 4:
            new_part = ''
            i = 0
            for c in part:
                new_part += c
                i += 1
                if i == 3 and len(new_part) != part:
                    new_part += '.'
                    i = 0
            new_parts.append(new_part)
        else:
            new_parts.append(part)

    return ','.join(new_parts)

def parse(element):
    if isinstance(element, Tag):
        match element.name.replace('m:', ''): # This way both namespaces and non-namespaces are handled
            # https://developer.mozilla.org/en-US/docs/Web/MathML/Element
            case 'math':
                # https://www.w3.org/TR/mathml4/#interf_toplevel
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/math
                return ''.join([parse(child) for child in element.children])
            case 'maction':
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/maction
                return ''.join([parse(child) for child in element.children]) # Deprecated
            case 'annotation': # Returns the text content of the annotation element only if text/plain TODO: check
                # https://www.w3.org/TR/mathml4/#mixing_elements_annotation
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/annotation
                if element.get('encoding') == 'text/plain':
                    return ''.join([parse(child) for child in element.children])
                else:
                    return ''
            case 'annotation-xml':
                # https://www.w3.org/TR/mathml4/#mixing_elements_annotation_xml
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/annotation-xml
                return ''.join([parse(child) for child in element.children]) # TODO: xml formats
            case 'menclose': # Non-standard. Layout - not relevant
                # https://www.w3.org/TR/mathml4/#presm_menclose
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/menclose
                return ''.join([parse(child) for child in element.children]) # TODO:
            case 'merror':
                # https://www.w3.org/TR/mathml4/#presm_merror
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/merror
                return ''.join([parse(child) for child in element.children]) # TODO: check if ok
            case 'mfenced': # Deprecated and non-standard. TODO: deal with parentheses if not present
                # https://www.w3.org/TR/mathml4/#presm_mfenced
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mfenced
                if (open_fence := element.get('open')) and (close_fence := element.get('close')):
                    return f'{open_fence}{"".join([parse(child) for child in element.children])}{close_fence}'
                else:
                    return f'({"".join([parse(child) for child in element.children])})'
            case 'mfrac': 
                # https://www.w3.org/TR/mathml4/#presm_mfrac
                # <mfrac> numerator denominator </mfrac>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mfrac
                children    = [child for child in element.children if isinstance(child, Tag)]
                numerator   = parse(children[0])
                denominator = parse(children[1])

                if 'mfrac' in [parent.name for parent in element.parents]:
                    return f'({numerator}/{denominator})'
                elif element.find(['mrow', 'mo']):
                    return f';{numerator} / {denominator};'
                else:
                    return f'{numerator}/{denominator}'
            case 'mi': # TODO: check pi
                # https://www.w3.org/TR/mathml4/#presm_mi
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mi
                if (previous_element := element.find_previous_sibling()) and previous_element.name.replace('m:','') == 'mi':
                    return ''.join([parse(child) for child in element.children])
                elif element.string in NON_SPACE_SYMBOLS:
                    return ''.join([parse(child) for child in element.children])
                else:
                    return ''.join([parse(child) for child in element.children]) # TODO: check
            case 'mmultiscripts':
                # https://www.w3.org/TR/mathml4/#presm_mmultiscripts
                # <mmultiscripts>
                #   base
                #   (subscript superscript)*
                #   [ <mprescripts/> (presubscript presuperscript)* ]
                # </mmultiscripts>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mmultiscripts
                children    = [child for child in element.children if isinstance(child, Tag)]
                base        = children[0]
                postscripts = []
                prescripts  = []

                if (pre := element.find(['m:mprescripts','mprescripts'])) and len(children) == 6:
                    prescripts_start    = children.index(pre)
                    regular_scripts     = children[1:prescripts_start]
                    prescripts          = children[prescripts_start + 1:]
                else:
                    regular_scripts     = children[1:]

                regular_pairs   = list(zip(regular_scripts[::2], regular_scripts[1::2]))
                prescript_pairs = list(zip(prescripts[::2], prescripts[1::2]))
                output          = ""

                for presubscript, presuperscript in prescript_pairs:
                    output += f'^{presuperscript.get_text()}\\{presubscript.get_text()}'

                output += base.get_text()

                for subscript, superscript in regular_pairs:
                    output += f'\\{subscript.get_text()}^{superscript.get_text()}'
                
                return output
            case 'mn': # MML 3.2.5
                # https://www.w3.org/TR/mathml4/#presm_mn
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mn
                number = ''
                if sub('[,.]','', element.string).isnumeric():
                    number = number_to_string(element.string)
                elif set(element.string.lower()) <= set(''.join(ROMAN_NUMERALS.keys()).lower()):
                    number = str(element.string)
                else:
                    print('Warning: non-numeric number', element.string)
                # MML 3.2.6
                if (next_element := element.find_next_sibling()) and next_element.name == 'mfrac':
                    number += '#'
                return number
            case 'mo': # MML 3.2.1
                # https://www.w3.org/TR/mathml4/#presm_mo
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mo
                # TODO: Consider validation elsewhere
                element.string = element.string.replace('-', '−') # Trying to catch minus sign errors
                element.string = element.string.replace('-', '−') # Trying to catch minus sign errors
                if element.string.strip() in OPERATORS:
                    return OPERATORS[element.string]
                else:
                    # logger.warning('Unknown operator', element.string) # TODO: log unknown operators
                    return 'UNKNOWN_OPERATOR'
            case 'mover': # MML11.1.2 
                # https://www.w3.org/TR/mathml4/#presm_mover
                # <mover> base overscript </mover>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mover
                children    = [child for child in element.children if isinstance(child, Tag)]
                base        = parse(children[0])
                overscript  = parse(children[1])
                return f'§-{base}' # TODO: check other cases
            case 'mpadded': # Irrelevant layout
                # https://www.w3.org/TR/mathml4/#presm_mpadded
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mpadded
                return ''.join([parse(child) for child in element.children])
            case 'mphantom': # # Irrelevant layout
                # https://www.w3.org/TR/mathml4/#presm_mphantom
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mphantom
                return ''.join([parse(child) for child in element.children])
            case 'mprescripts': # Placeholder - see mmultiscripts
                # https://www.w3.org/TR/mathml4/#presm_mmultiscripts
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mprescripts
                return ''
            case 'mroot': # Changed in NV8. Affects parentheses in <mrow>
                # https://www.w3.org/TR/mathml4/#presm_mroot
                # <mroot> base index </mroot>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mroot
                children    = [child for child in element.children if isinstance(child, Tag)]
                base        = parse(children[0])
                index       = parse(children[1])
                return f'root({index})({base})'
            case 'mrow':
                # https://www.w3.org/TR/mathml4/#presm_mrow
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mrow
                if element.parent.name in ['mfrac', 'munder', 'munderover']: # TODO: check list. NOT sqrt or root
                    return f'({"".join([parse(child) for child in element.children])})'
                else:
                    return ''.join([parse(child) for child in element.children]) # TODO: deal with parenthesis
            case 'ms': # String literal. Might be useful for fill-in tasks
                # https://www.w3.org/TR/mathml4/#presm_ms
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/ms
                return ''.join([parse(child) for child in element.children])
            case 'semantics': # Semantic annotation - not relevant
                # https://www.w3.org/TR/mathml4/#presm_semantics
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/semantics
                return ''.join([parse(child) for child in element.children])
            case 'mspace': # https://www.w3.org/TR/mathml4/#acc_spacing
                # https://www.w3.org/TR/mathml4/#presm_mspace
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mspace
                # "In general, the spacing elements <mspace>, <mphantom>,
                # and <mpadded> should not be used to convey meaning."
                return ''
            case 'msqrt': # Changed in NV8. Affects parentheses in <mrow>
                # https://www.w3.org/TR/mathml4/#presm_mroot
                # <msqrt> base </msqrt>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/msqrt
                return 'sqrt(' + ''.join([parse(child) for child in element.children]) + ')'
            case 'mstyle': # Style change - not relevant
                # https://www.w3.org/TR/mathml4/#presm_mstyle
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mstyle
                return ''.join([parse(child) for child in element.children])
            case 'msub':
                # https://www.w3.org/TR/mathml4/#presm_msub
                # <msub> base subscript </msub>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/msub
                children = [child for child in element.children if isinstance(child, Tag)]
                base        = parse(children[0])
                subscript   = parse(children[1])
                return f'{base}_{subscript}'
            case 'msup': # MML 3.2.11
                # https://www.w3.org/TR/mathml4/#presm_msup
                # <msup> base superscript </msup>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/msup
                children = [child for child in element.children if isinstance(child, Tag)]
                base        = parse(children[0])
                superscript = parse(children[1])
                return f'{base}^{superscript}' if "'" in superscript else f'{base}^{superscript}'
            case 'msubsup':
                # https://www.w3.org/TR/mathml4/#presm_msubsup
                # <msubsup> base subscript superscript </msubsup>
                #https://developer.mozilla.org/en-US/docs/Web/MathML/Element/msubsup
                children    = [child for child in element.children if isinstance(child, Tag)]
                base        = parse(children[0])
                subscript   = parse(children[1])
                superscript = parse(children[2])
                return f'{base}_{subscript}^{superscript}'
            case 'mtable': # Changed in NV8. Affects parentheses in <mrow>
                # https://www.w3.org/TR/mathml4/#presm_mtable
                # <mtable> rows </mtable>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mtable
                # TODO: check other uses of mtable than matrices, binomials, and determinants
                output          = '' 
                bracket_open    = '('
                bracket_close   = ')'
                if element.parent.name in ['mfenced']:
                    bracket_open    = '[' if element.parent.get('open') == '[' else '('
                    bracket_close   = ']' if element.parent.get('close') == ']' else ')'
                elif (element.parent.name in ['mrow'] and
                      (previous_element := element.find_previous_sibling()) and
                      (next_element := element.find_next_sibling()) and
                      previous_element.name == next_element.name == 'mo'):
                    bracket_open    = previous_element.string if previous_element.string in BRACKETS else '('
                    bracket_close   = next_element.string if next_element.string in BRACKETS else ')'

                for row in element.find_all('mtr'):
                    output += bracket_open + ','.join([parse(child) for child in row.children]) + bracket_close
                return f'{bracket_open}{output}{bracket_close}'
            case 'mtd': # Handled in mtable
                # https://www.w3.org/TR/mathml4/#presm_mtd
                # <mtd> cell </mtd>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mtd
                return ','.join([parse(child) for child in element.children])
            case 'mtext': # TODO: check layout consequences
                # https://www.w3.org/TR/mathml4/#presm_mtext
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mtext
                return ' ' + ''.join([parse(child) for child in element.children]).strip() + ' ' # TODO: check
            case 'mtr': # Handled in mtable TODO: see mtable
                # https://www.w3.org/TR/mathml4/#presm_mtr
                # <mtr> cells </mtr>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/mtr
                return ','.join([parse(child) for child in element.children if isinstance(child, Tag)])
            case 'munder': # MML 11.1.7-9 TODO: handle parentheses
                # https://www.w3.org/TR/mathml4/#presm_munder
                # <munder> base underscript </munder>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/munder
                children    = [child for child in element.children if isinstance(child, Tag)]
                base        = parse(children[0])
                underscript = parse(children[1])
                return f'{base}_{underscript}'
            case 'munderover': # MML 11.1.8 TODO: handle parentheses
                # https://www.w3.org/TR/mathml4/#presm_munderover
                # <munderover> base underscript overscript </munderover>
                # https://developer.mozilla.org/en-US/docs/Web/MathML/Element/munderover
                children    = [child for child in element.children if isinstance(child, Tag)]
                base        = parse(children[0])
                underscript = parse(children[1])
                overscript  = parse(children[2])
                return f'{base}_{underscript}^{overscript}'
            case _: 
                logger.warning('Unknown element', element.name)
                return str(element).strip().replace('\n', '')
    else:
        return str(element).strip().replace('\n', '')

# MAIN
# ====

if __name__ == '__main__':

    # Arguments
    parser = ArgumentParser(
            formatter_class = RawDescriptionHelpFormatter,
            description     = dedent('''
            This script converts MathML to StatpedMath format.
                '''),
            epilog          = 'Example: python mathml2statpedmath.py -i math_text.xhtml -o math_text.xhtml' )

    parser.add_argument('-i', '--input',  type = str, help = 'Input file')
    parser.add_argument('-o', '--output', type = str, help = 'Output file')
    args = parser.parse_args()

    # Input
    if args.input:
        with open(args.input, 'r') as file:
            soup = BeautifulSoup(file, 'html.parser')
    else:
        with open(testfile, 'r') as file:
            soup = BeautifulSoup(file, 'html.parser')

    # Conversion
    for math in soup(['math', 'm:math']):
        # TODO: block vs inline
        div         = soup.new_tag('div', attrs={'class':'math'})
        math_string = parse(math).strip()
        div.string  = math_string
        math.insert_after(div)
        math.decompose()

    # Output
    if args.output:
        with open(args.output, 'w') as file:
            file.write(str(soup))
    else:
        pass #print(soup.prettify())
