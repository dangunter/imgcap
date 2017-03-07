"""
Command-line program functions
"""
import argparse
import sys

from PIL import Image
from imageio import mimsave

from . import addtext, anim

class Caption(object):
    sides = {'t': addtext.Side.TOP, 'b': addtext.Side.BOTTOM,
             'l': addtext.Side.LEFT, 'r': addtext.Side.RIGHT}

    def __init__(self):
        default_pad = addtext.CapImg.default_padding
        self.p = argparse.ArgumentParser(description="Add a caption to an image")
        self.p.add_argument('inp', help='Input image file')
        self.p.add_argument('out', help='Output image file')
        self.p.add_argument('txt', help='Caption text (use \'-\' for standard input)')
        self.p.add_argument('-a', '--anim', help='Animated image',
                            action='store_true', dest='anim')
        self.p.add_argument('-f', '--font', help='Font name', dest='fname', default='arial')
        self.p.add_argument('--hpad', dest='padh', type=int, default=default_pad,
                            metavar='PX',
                            help='Horizontal padding, in pixels (default=%(default)s)')
        self.p.add_argument('--vpad', dest='padv', type=int, default=default_pad,
                            metavar='PX',
                            help='Vertical padding, in pixels (default=%(default)s)')
        self.p.add_argument('-r', '--reverse', dest='rev', action='store_true',
                            help='White text on black background')
        self.p.add_argument('-s', '--side', dest='side', default='b',
                            help='Side of image to caption: (t)op, (b)ottom, (l)eft, (r)ight. '
                                 'Default is bottom.')
        self.p.add_argument('-z', '--font-size', dest='fsize', type=int, default=16,
                            help='Font size, in points. Default is 16pt.')

    def main(self, args):
        a = self.p.parse_args(args)
        opts = {}
        try:
            opts['side'] = self.sides[a.side.lower()[0]]
        except IndexError:
            self.p.error('-s/--side must be t,b,l, or r')
        if a.rev:
            opts['text_fill'] = (255, 255, 255, 255)
            opts['text_bg'] = (0, 0, 0, 255)
        else:
            opts['text_fill'] = (0, 0, 0, 255)
            opts['text_bg'] = (255, 255, 255, 255)
        opts['font_size'] = a.fsize
        opts['padx'] = a.padh
        opts['pady'] = a.padv
        opts['font'] = a.fname
        if a.txt == '-':
            text = sys.stdin.read()
        else:
            text = a.txt
        if a.anim:
            caption_sequence(a.inp, text, a.out, opts)
        else:
            caption_one(a.inp, text, a.out, opts)

def caption_one(input_path, caption_text, output_path, options):
    image = Image.open(input_path)
    output_image = _add_caption(image, caption_text, options)
    output_image.save(output_path)

def caption_sequence(input_path, caption_text, output_path, options):
    image = Image.open(input_path)
    sequence = anim.process_frames(image, lambda im: _add_caption(im, caption_text, options))
    mimsave(output_path, sequence)

def _add_caption(image, caption_text, options):
    cap = addtext.CapImg(image, **options)
    cap.addtext(caption_text)
    return cap.finish()

