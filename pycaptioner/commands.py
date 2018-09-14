"""
Command-line program functions
"""
import argparse
import sys

from PIL import Image, ImageColor
from imageio import mimsave

from . import addtext, anim


class Caption(object):
    sides = {'t': addtext.Side.TOP, 'b': addtext.Side.BOTTOM,
             'l': addtext.Side.LEFT, 'r': addtext.Side.RIGHT,
             'nw': addtext.Side.NW, 'ne': addtext.Side.NE,
             'se': addtext.Side.SE, 'sw': addtext.Side.SW,
             'n': addtext.Side.N, 'e': addtext.Side.E,
             'w': addtext.Side.W, 's': addtext.Side.S,
             }

    def __init__(self):
        default_pad = addtext.CapImg.default_padding
        self.p = argparse.ArgumentParser(description="Add a caption to an image")
        self.p.add_argument('inp', help='Input image file')
        self.p.add_argument('out', help='Output image file')
        self.p.add_argument('txt', help='Caption text. '
                                        'Use \'-\' for standard input, '
                                        '@filename for an input file.')
        self.p.add_argument('-a', '--anim', help='Animated image',
                            action='store_true', dest='anim')
        self.p.add_argument('-b', '--background', help='Background color, for '
                                                       'outside captions.',
                            default=None, dest='bg')
        self.p.add_argument('-c', '--color', help='Text color', default=None,
                            dest='fg')
        self.p.add_argument('-e', '--effect', action='append', dest='effects',
                            help='Text effect (repeatable), use -E for help')
        self.p.add_argument('-E', action='store_true', dest='show_effects',
                            help='Show details on adding text effects')
        self.p.add_argument('-f', '--font', help='Font name', dest='fname', default='arial')
        self.p.add_argument('--hpad', dest='padh', type=int, default=default_pad,
                            metavar='PX',
                            help='Horizontal padding, in pixels (default=%(default)s)')
        self.p.add_argument('--vpad', dest='padv', type=int, default=default_pad,
                            metavar='PY',
                            help='Vertical padding, in pixels (default=%(default)s)')
        self.p.add_argument('--hshift', dest='shiftx', type=int, default=0,
                            metavar='SX', help='Shift horizontal (ignored if'
                                               'side is t, b, l, or r)'),
        self.p.add_argument('--vshift', dest='shifty', type=int, default=0,
                            metavar='SY', help='Shift vertical (ignored if'
                                               'side is t, b, l, or r)')
        self.p.add_argument('-l', '--line-spacing', dest='linespc', type=int,
                            default=4, help='Line spacing (default=4)',
                            metavar='POINTS')
        self.p.add_argument('-r', '--reverse', dest='rev', action='store_true',
                            help='White text on black background')
        self.p.add_argument('-s', '--side', dest='side', default='b',
                            help='Side of image to caption. Either '
                                 'outside (t)op, (b)ottom, (l)eft, (r)ight, or '
                                 'inside nw, ne, se, sw quadrant, or on '
                                 '(n)orth, (e)ast, (w)est, or (s)outh side. '
                                 'Default is (b)ottom.')
        self.p.add_argument('-u', '--bubble', dest='bubble',
                            metavar='COORD', default='',
                            help='Add text bubble and tail. '
                                 'Tail coordinates "<x>,<y>" in '
                                 'pixels from origin in upper-left corner. '
                                 'Optionally, add :<n> to create an internal '
                                 'margin of <n> pixels (default=5). '
                                 'Optionally, add "+" at end to fill bubble '
                                 'with background color.')
        self.p.add_argument('-z', '--font-size', dest='fsize', type=int, default=16,
                            help='Font size, in points. Default is 16pt.')

    def main(self, args):
        a = self.p.parse_args(args)
        if a.show_effects:
            print('Add text effects as <code>:<option>,<option>,...\n'
                  'Available effects:\n'
                  '  Drop shadow: code=d options=[pixels,color-code]\n'
                  '    Examples:\n'
                  '      -e  d:2,red           -- 2-pixel red shadow\n'
                  '      --effect=d:4,#ffffff  -- 4-pixel white shadow\n'
                  '  Outline: code=o options=[pixels,color-code]\n'
                  '    Examples:\n'
                  '      -e  o:1,red           -- 1-pixel red outline\n'
                  '      --effect=o:4,#ffffff  -- 4-pixel white outline'
                  )
            return 0
        opts = {}
        try:
            skey = a.side.lower()
            if len(skey) != 2:
                skey = skey[0]
            opts['side'] = self.sides[skey]
        except KeyError:
            self.p.error('-s/--side must be one of: t, b, l, r, n, e, w, s, '
                         'nw, ne, se, sw')
        if a.rev:
            if a.bg:
                self.p.error('-r/--reverse and -b/--background conflict')
            if a.fg:
                self.p.error('-r/--reverse and -c/--color conflict')
            opts['text_fill'] = (255, 255, 255, 255)
            opts['text_bg'] = (0, 0, 0, 255)
        else:
            if a.bg:
                try:
                    color_tuple = _parse_color(a.bg)
                except ValueError as err:
                    self.p.error('Bad value for -b/--background: {}'.format(err))
                opts['text_bg'] = color_tuple
            else:
               opts['text_bg'] = (255, 255, 255, 255)
            if a.fg:
                try:
                    color_tuple = _parse_color(a.fg)
                except ValueError as err:
                    self.p.error(
                        'Bad value for -c/--color: {}'.format(err))
                opts['text_fill'] = color_tuple
            else:
                opts['text_fill'] = (0, 0, 0, 255)

        opts['font_size'] = a.fsize
        opts['padx'] = a.padh
        opts['pady'] = a.padv
        opts['shiftx'] = a.shiftx
        opts['shifty'] = a.shifty
        opts['font'] = a.fname
        opts['line_spacing'] = a.linespc
        opts['balloon'] = False
        opts['balloon_tail'] = None
        opts['text_effects'] = []
        for eff in a.effects:
            code, eopt = None, None
            try:
                code, eopt = eff.split(':')
            except ValueError:
                self.p.error('Bad value for -e/--effect: {}'.format(eff))
            eopts = eopt.split(',')
            opts['text_effects'].append((code, eopts))
        if a.bubble:
            a.bubble = a.bubble.strip()
            try:
                if a.bubble.endswith('+'):
                    a.bubble = a.bubble[:-1]
                    opts['balloon_fill'] = True
                parts = a.bubble.split(',')
                if ':' in parts[1]:
                    parts[1], bbm = parts[1].split(':')
                    try:
                        bbm = int(bbm)
                    except ValueError:
                        self.p.error('Bad value for balloon margin in "{}"'
                                     .format(a.bubble))
                else:
                    bbm = 5
                tx, ty = map(int, parts)
                opts['balloon'] = True
                opts['balloon_tail'] = (tx, ty)
                opts['balloon_margin'] = bbm
            except ValueError:
                self.p.error('Bad value for -u/--')
        if a.txt == '-':
            text = sys.stdin.read()
        elif a.txt[0] == '@':
            filename = a.txt[1:].strip()
            try:
                infile = open(filename)
            except FileNotFoundError:
                self.p.error('Cannot find text input file "{}"'
                             .format(filename))
            except PermissionError:
                self.p.error('Permission denied for text input file "{}"'
                             .format(filename))
            text = infile.read()
        else:
            text = a.txt
        if a.anim:
            caption_sequence(a.inp, text, a.out, opts)
        else:
            caption_one(a.inp, text, a.out, opts)


def _parse_color(s):
    result = ImageColor.getrgb(s)
    if len(result) == 3:
        result = tuple(list(result) + [255])
    return result


def caption_one(input_path, caption_text, output_path, options):
    image = Image.open(input_path)
    output_image = _add_caption(image, caption_text, options)
    output_image.save(output_path)


def caption_sequence(input_path, caption_text, output_path, options):
    image = Image.open(input_path)
    sequence = anim.process_frames(image,
                                   lambda im: _add_caption(im, caption_text,
                                                           options))
    mimsave(output_path, sequence)


def _add_caption(image, caption_text, options):
    cap = addtext.CapImg(image, **options)
    cap.addtext(caption_text)
    return cap.finish()

