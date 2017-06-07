"""
Add text to images
"""
import os, glob
import re
import textwrap
from PIL import Image, ImageDraw, ImageFont


class Side(object):
    """Enumeration for 'side' of an image."""
    # outer
    TOP, RIGHT, BOTTOM, LEFT = 1, 2, 3, 4
    # inner
    NW, NE, SE, SW = 5, 6, 7, 8
    N, E, W, S = 9, 10, 11, 12

class Fonts(object):
    default_font_dirs = ['/usr/share/fonts',
                         os.path.join(os.environ['HOME'], '.fonts')]
    extensions = ['ttf', 'otf', 'TTF', 'OTF']

    def __init__(self, font_dirs=None):
        self._fd = font_dirs if font_dirs else self.default_font_dirs

    def __str__(self):
        paths = ', '.join(self._fd)
        extensions = ', '.join(self.extensions)
        return 'fonts with extensions ({e}) in paths: {p}'.format(e=extensions, p=paths)

    def find(self, name):
        for d1 in self._fd:
            path = self._find_name(d1, name)
            if path:
                return path
            for d2 in os.listdir(d1):
                d3 = os.path.join(d1, d2)
                if os.path.isdir(d3):
                    path = self._find_name(d3, name)
                    if path:
                        return path
        return None

    def _find_name(self, d, name):
        #print('DBG: look for fonts in "{}"'.format(d))
        for ext in self.extensions:
            target = os.path.join(d, '{name}.{ext}'.format(name=name ,ext=ext))
            if os.path.exists(target):
                return target
        return None

class CapImg(object):
    """Caption an image.

    Sample usage::

        from PIL import Image
        image = Image.open("kitties.jpg")
        cap = CapImg(image)
        cap.addtext("Hello darkness, ")
        cap.addtext("my old friend...")
        finnish_kitties = cap.finish()
        finnish_kitties.save("finkitties.jpg")
    """
    default_padding = 5
    default_text_fill = (0, 0, 0, 255)
    default_text_bg = (255, 255, 255, 255)
    paragraph_marker = '//'

    def __init__(self, im, side=Side.BOTTOM, space=0, font_size=16,
        text_fill=default_text_fill, text_bg=default_text_bg,
        padx=default_padding, pady=default_padding, font='DroidSansMono'):
        """Create and prepare for adding text

        Args:
            im (Image): Image to caption
            side (int): Side of the image for the caption
        """
        self._base = im
        self._text = []
        self._side = side
        self._padx = padx
        self._pady = pady
        self._fill = text_fill
        self._bg = text_bg
        self._spc = space
        self._words = None
        # find font
        fonts = Fonts()
        ffile = fonts.find(font)
        if ffile is None:
            raise ValueError('Cannot find font "{n}" in {f}'.format(
                n=font, f=fonts))
        self._font = ImageFont.truetype(ffile, font_size)

    def addtext(self, text):
        """

        Args:
            text (str): Text to add
        """
        self._text.append(text)

    def _wrap_text(self, w=0, h=0):
        # calculate height/width of single character
        draw = ImageDraw.Draw(Image.new('RGBA', (1000, 1000)))
        fx, fy = draw.multiline_textsize("The quick 'fox' "
                                         "jumps over the lazy dog.",
                                         font=self._font)
        fx /= 37
        #fy += 5
        text = ' '.join(self._text).strip()
        if w > 0:
            # known width
            wrap_width = w / fx
            # wrap the text
            lines = self._wrap(text, wrap_width)
        elif w == 0:
            if h < fy:
                raise ValueError('Image too small to fit one'
                                 'line of text next to it')
            # unknown width, need to calculate it
            # start with perfect wrapping and expand out
            n = len(text)
            lines, max_lines = [], h // fy
            wrap_width = max(n // max_lines, 8)
            while wrap_width < n:
                lines = self._wrap(text, wrap_width)
                # print('@@ wrap_width={} lines={} max_lines={}'
                #      .format(wrap_width, len(lines), max_lines))
                if len(lines) <= max_lines and not self._broken_words(text, lines):
                    break
                wrap_width += 1
        # calculate dimensions
        wrapped = '\n'.join(lines)
        fx, fy = draw.multiline_textsize(wrapped, font=self._font)
        return (wrapped, (fx, fy))

    def _wrap(self, text, width):
        """Wrap text in paragraphs."""
        if not self.paragraph_marker in text:
            return textwrap.wrap(text, width)
        lines = []
        for para in text.split(self.paragraph_marker):
            if para == '':
                lines.append('')
            else:
                lines.extend(textwrap.wrap(para, width))
        return lines

    def _broken_words(self, text, lines):
        if not self._words:
            self._words = re.findall('\w+', text)
            # print("@@ WORDS: {}".format(self._words))
        w = 0
        for line in lines:
            line_words = re.findall('\w+', line)
            for lw in line_words:
                if self._words[w] != lw:
                    # print('@@ bad line-word "{}" != next text word "{}"'
                    # .format(lw, self._words[w]))
                    return True
                w += 1
                if w == len(self._words):
                    return False
        return False

    def finish(self):
        """Finish the image by putting the caption on it.

        Text box (which may be on any side of img) is
        padded on top/bottom by 'pady' and left/right
        by 'padx' pixels.

        Returns:
            (Image) Captioned image
        """
        base_width, base_height = self._base.size
        if self._side in (Side.TOP, Side.BOTTOM):
            text_width = base_width - 2 * self._padx
            text_height = 0 if self._spc == 0 else self._spc - 2 * self._pady
            new_width = base_width
            new_height = self._base.size[1] + self._spc
            text_xoffs = self._padx
            if self._side == Side.TOP:
                text_yoffs = self._pady
            else:
                text_yoffs = self._base.size[1] + self._pady
        elif self._side in (Side.LEFT, Side.RIGHT):
            text_width = 0 if self._spc == 0 else self._spc - 2 * self._padx
            text_height = self._base.size[1] - 2 * self._pady
            new_width = base_width + self._spc
            new_height = self._base.size[1]
            text_yoffs = self._pady
            if self._side == Side.LEFT:
                text_xoffs = self._padx
            else:
                text_xoffs = base_width + self._padx
        elif self._side in (Side.NW, Side.NE, Side.SE, Side.SW):
            new_width, new_height = base_width, base_height
            text_width = base_width / 2 - 2 * self._padx
            text_height = base_height / 2
            if self._side == Side.NE:
                text_xoffs = base_width/2 + self._padx
                text_yoffs = self._pady
            elif self._side == Side.NW:
                text_xoffs = self._padx
                text_yoffs = self._pady
            elif self._side == Side.SE:
                text_xoffs = self._padx + base_width / 2
                text_yoffs = self._pady + base_height / 2
            elif self._side == Side.SW:
                text_xoffs = self._padx
                text_yoffs = self._pady + base_height / 2
        elif self._side in (Side.N, Side.E, Side.W, Side.S):
            new_width, new_height = base_width, base_height
            if self._side in (Side.N, Side.S):
                text_xoffs = self._padx
                text_height = base_height / 2 - 2 * self._pady
                text_width = base_width - 2 * self._padx
                if self._side == Side.N:
                    text_yoffs = self._pady
                else:
                    text_yoffs = self._pady + base_height / 2
            else:
                text_yoffs = self._pady
                text_width = base_width / 2 - 2 * self._padx
                text_height = base_height - 2 * self._pady
                if self._side == Side.W:
                    text_xoffs = self._padx
                else:
                    text_xoffs = self._padx + base_width / 2
        else:
            raise ValueError("size={} not understood".format(self._side))
        wrapped_text, text_dim = self._wrap_text(w=text_width, h=text_height)
        # auto-calculated text width or height
        if self._spc == 0:
            if self._side in (Side.TOP, Side.BOTTOM):
                new_height += text_dim[1] + 2 * self._pady
            elif self._side in (Side.LEFT, Side.RIGHT):
                new_width += text_dim[0] + 2 * self._padx
        bgcolor = self._bg
        cp = Image.new(mode='RGB', size=(new_width, new_height), color=bgcolor)
        # paste original image back in
        if self._side == Side.TOP:
            cp.paste(self._base, (0, new_height - base_height))
        elif self._side == Side.BOTTOM or self._side == Side.RIGHT:
            cp.paste(self._base, (0,0))
        elif self._side == Side.LEFT:
            cp.paste(self._base, (new_width - base_width, 0))
        elif self._side in (Side.NE, Side.NW, Side.SW, Side.SE, Side.N,
                            Side.E, Side.W, Side.S):
            cp.paste(self._base, (0, 0))
        else:
            raise ValueError('Bad value for side: {}'.format(self._side))
        # draw text
        draw = ImageDraw.Draw(cp)
        draw.multiline_text((text_xoffs, text_yoffs), wrapped_text,
                            font=self._font, fill=self._fill)
        return cp

