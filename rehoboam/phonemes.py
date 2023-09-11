import re
import random

from phonemizer import phonemize

# Phoneme Dictionary
Dict = {
    'm': ['m', 'mm', 'chm', 'gm', 'lm', 'mb', 'mbe', 'me', 'mh', 'mme', 'mn', 'monde', 'mp', 'sme', 'tm'],
    'n': ['n', 'nn', 'cn', 'dn', 'gn', 'gne', 'hn', 'kn', 'ln', 'mn', 'mp', 'nd', 'ne', 'ng', 'nh', 'nne', 'nt', 'pn', 'sn',
     'sne'],
    'ŋ': ['ng', 'n', 'nc', 'nd', 'ngh', 'ngue'],
    'p': ['p', 'pp', 'gh', 'pe', 'ph', 'ppe'],
    'b': ['b', 'bb', 'be', 'bh', 'pb'],
    't': ['t', 'tt', 'bt', 'cht', 'ct', 'd', 'dt', 'ed', 'ght', 'kt', 'pt', 'phth', 'st', 'te', 'th', 'tte'],
    'd': ['d', 'dd', 'ddh', 'bd', 'de', 'dh', 'ed', 'ld', 't', 'tt'],
    'k': ['c', 'k', 'cc', 'cch', 'ch', 'ck', 'cq', 'cqu', 'cque', 'cu', 'ke', 'kh', 'kk', 'lk', 'q', 'qh', 'qu', 'que', 'x'],
    'ɡ': ['g', 'gg', 'ckg', 'gge', 'gh', 'gu', 'gue'],
    'f': ['f', 'ff', 'fe', 'ffe', 'ft', 'gh', 'lf', 'ph', 'phe', 'pph'],
    'v': ['v', 'vv', 'f', 'lve', 'ph', 'u', 've', 'w', 'zv', 'b', 'bh', 'mh'],
    'θ': ['th', 'the', 'chth', 'phth', 'tth', 'h'],
    'ð': ['th', 'the', 'dd', 'dh', 'y'],
    's': ['s', 'ss', 'c', 'cc', 'ce', 'ps', 'sc', 'sce', 'sch', 'se', 'sh', 'sse', 'sses', 'st', 'sth', 'sw', 't', 'th',
         'ts', 'tsw', 'tzs', 'tz', 'z'],
    'z': ['z', 'zz', 'cz', 'ds', 'dz', 's', 'sc', 'se', 'sh', 'sp', 'ss', 'sth', 'ts', 'tz', 'x', 'ze', 'zh', 'zs'],
    'ʃ': ['sh', 'c', 'ce', 'ch', 'che', 'chi', 'chsi', 'ci', 's', 'sc', 'sch', 'sche', 'schsch', 'sci', 'sesh', 'she', 'shh',
         'shi', 'si', 'sj', 'ss', 'ssi', 'ti', 'psh', 'zh', 'x'],
    'ʒ': ['ci', 'g', 'ge', 'j', 's', 'si', 'ssi', 'ti', 'z', 'zh', 'zhe', 'zi'],
    'h': ['h', 'wh', 'j', 'ch', 'x'],
    'ɹ': ['r', 'rr', 'l', 're', 'rh', 'rre', 'rrh', 'rt', 'wr'],
    'ɾ': ['tt', 'dd', 't', 'd'],
    'l': ['l', 'll', 'le', 'lh', 'lle', 'gl', 'sle'],
    'j': ['y', 'h', 'i', 'j', 'l', 'll', 'z', 'r'],
    'w': ['w', 'ww', 'u', 'o', 'ou', 'hu', 'hw', 'ju', 'wh'],
    't͡ʃ': ['ch', 'tch', 'c', 'cc', 'cch', 'che', 'chi', 'cs', 'cz', 't', 'tche', 'te', 'th', 'ti', 'ts', 'tsch', 'tsh', 'tz', 'tzs', 'tzsch', 'q'],
    'd͡ʒ': ['g', 'j', 'ch', 'd', 'dg', 'dge', 'di', 'dj', 'dzh', 'ge', 'gg', 'gi', 'jj', 't'],
    'k͡s': ['x', 'xx', 'cast', 'cc', 'chs', 'cks', 'cques', 'cs', 'cz', 'kes', 'ks', 'lks', 'ques', 'xc', 'xe', 'xs', 'xsc', 'xsw'],
    'i͡ː': ['e', 'i', 'a ', 'ae', 'aoi', 'ay', 'ea', 'ee', "e'e", 'ei', 'eo', 'ey', 'eye', 'ie', 'is', 'ix', 'oe', 'oi', 'ue', 'ui', 'uy', 'y'],
    'ɪ͡ɹ': ['ere', 'aer', "e're", 'ea', 'ear', 'eare', 'eer', 'eere', 'ehr', 'eir', 'eor', 'er', 'ers', 'eyr', 'ier', 'iere', 'ir', 'oea', 'yer'],
    'ɪ': ['i', 'y', 'a', 'ai', 'e', 'ea', 'ee', 'ei', 'ey', 'eye', 'ia', 'ie', 'ii', 'o', 'oe', 'oi', 'u', 'ue', 'ui', 'uy'],
    'u͡ː': ['u', 'oo', 'eew', 'eu', 'ew', 'ieu', 'ioux', 'o', 'oe', 'oeu', 'ooe', 'ou', 'ough', 'ougha', 'oup', 'ue', 'uh', 'ui', 'uo', 'w', 'wo'],
    'ʊ': ['oo', 'u', 'o', 'or', 'ou', 'oul', 'w'],
    'e͡ɪ': ['a', 'aa', 'ae', 'ai', 'aig', 'aigh', 'ais', 'al', 'alf', 'ao', 'au', 'ay', 'aye', 'é', 'e', 'ea', 'eg', 'ee', 'ée', 'eh', 'ei', 'eig', 'eigh', 'eighe', 'er', 'ere', 'es', 'et', 'ete', 'ey', 'eye', 'ez', 'ie', 'oeh', 'ue', 'uet'],
    'ɛ͡ɹ': ['are', 'aer', 'air', 'aire', 'ar', 'ayer', 'ayor', 'ayre', "e'er", 'eah', 'ear', 'ehr', 'eir', 'eor', 'er', 'ere', 'err', 'erre', 'ert', "ey're", 'eyr', 'ahr'],
    'ɛ': ['e', 'a', 'ae', 'ai', 'ay', 'ea', 'eh', 'ei', 'eo', 'ie', 'ieu', 'oe', 'u', 'ue', 'ee'],
    'ə': ['a', 'e', 'i', 'o', 'u', 'y', 'ae', 'ah', 'ai', 'anc', 'ath', 'au', 'ea', 'eau', 'eh', 'ei', 'eig', 'eo', 'eou', 'eu', 'gh', 'ie', 'oa', 'oe', 'oh', 'oi', 'oo', 'op', 'ou', 'ough', 'ua', 'ue', 'ui', 'uo'],
    'ɜ͡ː': ['er', 'ir', 'ur', 'ar', 'ear', 'ere', 'err', 'erre', 'eur', 'eure', 'irr', 'irre', 'oeu', 'olo', 'or', 'our', 'ueur', 'uhr', 'urr', 'urre', 'yr', 'yrrh'],
    'o͡ʊ': ['o', 'aoh', 'au', 'aux', 'eau', 'eaue', 'eo', 'ew', 'oa', 'oe', 'oh', 'oo', 'ore', 'ot', 'ou', 'ough', 'oughe', 'ow', 'owe', 'w'],
    'ʌ': ['u', 'o', 'oe', 'oo', 'ou', 'uddi', 'wo', 'a', 'au'],
    'ɔ͡ː': ['o', 'a', 'al', 'au', 'augh', 'aughe', 'aw', 'awe', 'eo', 'oa', 'oh', 'oo', 'oss', 'ou', 'ough', 'u', 'uo'],
    'ɔ͡ː͡ɹ': ['or', 'ore', 'aor', 'ar', 'aur', 'aure', 'hors', 'oar', 'oare', 'oor', 'oore', 'our', 'oure', 'owar', 'ure'],
    'æ': ['a', 'aa', 'ag', 'ah', 'ai', 'al', 'ar', 'au', 'e', 'ea', 'ei', 'i', 'ua'],
    'ɑ͡ː': ['a', 'aa', 'aae', 'aah', 'aahe', 'ag', 'ah', 'au', 'i'],
    'ɑ͡ː͡ɹ': ['ar', 'aar', 'ahr', 'alla', 'are', 'arr', 'arre', 'arrh', 'ear', 'er', 'uar'],
    'ɒ': ['a', 'o', 'ach', 'au', 'eau', 'oh', 'ou', 'ow', 'e', 'eo'],
    'j͡u͡ː': ['u', 'ew', 'eau', 'eo', 'eu', 'ewe', 'ieu', 'iew', 'ou', 'ue', 'ueue', 'ugh', 'ui', 'ut', 'uu', 'you'],
    'a͡ɪ': ['ae', 'ai', 'aie', 'aille', 'ais', 'ay', 'aye', 'ei', 'eigh', 'eu', 'ey', 'eye', 'i', 'ia', 'ic', 'ie', 'ig', 'igh', 'ighe', 'is', 'oi', 'oy', 'ui', 'uy', 'uye', 'y', 'ye'],
    'ɔ͡ɪ': ['oi', 'oy', 'eu', 'oll', 'ooi', 'oye', 'ui', 'uoy', 'uoye', 'awy'],
    'a͡ʊ': ['ou', 'ow', 'ao', 'aou', 'aow', 'aowe', 'au', 'aw', 'odh', 'ough', 'oughe', 'owe', 'iao', 'iau', 'eo']
}
# s = ""
# print(s.split(', '))

text = "discord"
def process_text(text: str=None):
    phonemed = phonemize(text, tie=True)

    return phonemed

def split(phonemed: str=None):
    split_phonemes = re.split("", phonemed)

    return split_phonemes

def tied(text: list=None):
    for i in reversed(range(len(text))):
        if text[i] == "͡":
            tie = text[i-1] + "͡" + text[i+1]
            text[i+1] = ""

            # Corrections
            if tie == "ə͡l":
                tie = "ə"
                text[i+1] = "l"

            text[i] = tie
            text[i-1] = ""

    reduced_list = list(filter(None, text))
    return reduced_list

def make_digraph(text: list=None):
    for i in range(len(text)):
        # Triples
        if text[i] == "o" and text[i + 1] == "ː" and text[i + 2] == "͡" and text[i + 3] == "ɹ":
            digraph = "ɔ͡ː͡ɹ"
            text[i] = digraph
            text[i+1] = ""
            text[i+2] = ""
            text[i+3] = ""
        if text[i] == "ɔ" and text[i + 1] == "ː" and text[i + 2] == "͡" and text[i + 3] == "ɹ":
            digraph = "ɔ͡ː͡ɹ"
            text[i] = digraph
            text[i+1] = ""
            text[i+2] = ""
            text[i+3] = ""
        if text[i] == "ɔ" and text[i + 1] == "ː" and text[i + 2] == "ɹ":
            digraph = "ɔ͡ː͡ɹ"
            text[i] = digraph
            text[i+1] = ""
            text[i+2] = ""
        if text[i] == "ɑ" and text[i + 1] == "ː" and text[i + 2] == "͡" and text[i + 3] == "ɹ":
            digraph = "ɑ͡ː͡ɹ"
            text[i] = digraph
            text[i+1] = ""
            text[i+2] = ""
            text[i+3] = ""
        if text[i] == "j" and text[i + 1] == "u" and text[i + 2] == "ː":
            digraph = "j͡u͡ː"
            text[i] = digraph
            text[i+1] = ""
            text[i+2] = ""

        # Doubles
        if text[i] == "ɜ" and text[i + 1] == "ː":
            digraph = "ɜ͡ː"
            text[i] = digraph
            text[i + 1] = ""
        if text[i] == "ɛ" and text[i + 1] == "ɹ":
            digraph = "ɛ͡ɹ"
            text[i] = digraph
            text[i + 1] = ""
        if text[i] == "k" and text[i + 1] == "s":
            digraph = "k͡s"
            text[i] = digraph
            text[i + 1] = ""
        if text[i] == "i" and text[i + 1] == "ː":
            digraph = "i͡ː"
            text[i] = digraph
            text[i + 1] = ""
        if text[i] == "u" and text[i + 1] == "ː":
            digraph = "u͡ː"
            text[i] = digraph
            text[i + 1] = ""
        if text[i] == "ɔ" and text[i + 1] == "ː":
            digraph = "ɔ͡ː"
            text[i] = digraph
            text[i + 1] = ""
        if text[i] == "ɑ" and text[i + 1] == "ː":
            digraph = "ɑ͡ː"
            text[i] = digraph
            text[i + 1] = ""

        # Replacements
        if text[i] == "ɚ":
            text[i] ="ɜ͡ː"
        if text[i] == "ᵻ":
            text[i] = "ɛ"
        if text[i] == "ɐ":
            text[i] = "ə"

    reduced_list = list(filter(None, text))
    return reduced_list

global links
def replace_ipa(orig_text: list=None):
    replaced_text = [x for x in orig_text]
    choices_and_none = []
    links = ""
    for ipa in range(len(orig_text)):
        try:
            phoneme_options = Dict[replaced_text[ipa]]
            phoneme_choice = random.choice(phoneme_options)
            replaced_text[ipa] = phoneme_choice
        except:
            phoneme_choice = "None"

        choices_and_none.append(phoneme_choice)
    linkslist = []
    for x in reversed(range(len(orig_text))):
        if choices_and_none[x] == "None":
            choices_and_none.pop(x)
            orig_text.pop(x)
            continue
        linkslist.append(f'{orig_text[x]} - {choices_and_none[x]}')

    for link in reversed(linkslist):
        links += f"{link}\n"

    values = [replaced_text, links]
    return values

def make_phrase(text: list=None):
    phrase = ""
    for phoneme in range(len(text)):
        phrase = phrase + text[phoneme]

    return phrase

# print(text)
# print(process_text(text))
# print(split(process_text(text)))
# print(make_digraph(split(process_text(text))))
# replace_ipa(tied(make_digraph(split(process_text(text)))))
# print(make_phrase(replace_ipa(tied(make_digraph(split(process_text(text)))))[0]))
# print(replace_ipa(tied(make_digraph(split(process_text(text)))))[1])