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

    @classmethod
    def is_inner(cls, v):
        return v >= cls.NW


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
                 padx=default_padding, pady=default_padding,
                 shiftx=0, shifty=0, font='DroidSansMono', line_spacing=4,
                 balloon=False, balloon_tail=(0, 0), balloon_fill=False):
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
        self._shiftx = shiftx
        self._shifty = shifty
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
        self._font_spc = line_spacing
        if balloon and Side.is_inner(self._side):
            self._balloon = True
            self._tailx, self._taily = balloon_tail
            self._bfill = balloon_fill
        else:
            self._balloon = False

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
                                         font=self._font,
                                         spacing=self._font_spc)
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
        text_xoffs, text_yoffs = 0, 0
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
            text_xoffs += self._shiftx
            text_yoffs += self._shifty
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
            text_xoffs += self._shiftx
            text_yoffs += self._shifty
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
                text_yoffs = base_height - self._pady - text_height
            elif self._side == Side.SW:
                text_xoffs = self._padx
                text_yoffs = self._pady + base_height / 2
            text_xoffs += self._shiftx
            text_yoffs += self._shifty
        elif self._side in (Side.N, Side.E, Side.W, Side.S):
            new_width, new_height = base_width, base_height
            if self._side in (Side.N, Side.S):
                text_xoffs = self._padx
                text_height = base_height / 2 - 2 * self._pady
                text_width = base_width - 2 * self._padx
                if self._side == Side.N:
                    text_yoffs = self._pady
                else:
                    text_yoffs = base_height / 2 + self._pady 
            else:
                text_yoffs = self._pady
                text_width = base_width / 2 - 2 * self._padx
                text_height = base_height - 2 * self._pady
                if self._side == Side.W:
                    text_xoffs = self._padx
                else:
                    text_xoffs = self._padx + base_width / 2
            text_xoffs += self._shiftx
            text_yoffs += self._shifty
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
        elif self._side in (Side.NE, Side.NW, Side.N, Side.E, Side.W, Side.S, Side.SE, Side.SW):
            cp.paste(self._base, (0, 0))
        else:
            raise ValueError('Bad value for side: {}'.format(self._side))
        # get ready to draw text
        draw = ImageDraw.Draw(cp)
        if self._side in (Side.S, Side.SE, Side.SW):
            text_yoffs += (base_height / 2) - text_dim[1] - 2 * self._pady
        # draw box
        if self._balloon:
            tp = 5
            self._draw_balloon(draw, text_xoffs - tp, text_yoffs - tp,
                               text_dim[0] + tp * 2, text_dim[1] + tp * 2,
                               self._tailx, self._taily)
        # draw text
        draw.multiline_text((text_xoffs, text_yoffs), wrapped_text,
                            font=self._font, fill=self._fill,
                            spacing=self._font_spc)
        return cp

    def _draw_balloon(self, draw, x, y, w, h, tx, ty):
        """Draw balloon around the text, with tail to (tx, ty).

        Args:
            draw (PIL.ImageDraw.Draw): Drawing object
            x (int): upper-left corner x
            y (int): upper-left corner y
            w (int): width
            h (int): height
            tx (int): Tail end x
            ty (int): Tail end y

        Returns:
            None
        """
        fill, wid = self._fill, 2
        # tail
        seg, seg_side = self._calc_tail(x, y, w, h, tx, ty)
        if seg:
            if self._bfill:
                # draw filled polygon for tail
                draw.polygon([seg[0], seg[1], (tx, ty)], fill=self._bg,
                             outline=self._bg)
            else:
                # draw 2 lines for tail
                for i in (0, 1):
                    draw.line([seg[i], (tx, ty)], fill=fill, width=wid)
        # calculate rounded corners
        if w > 50 and h > 50:
            rr_x, rr_y = 10, 10
        elif w > 20 and h > 20:
            rr_x, rr_y = 5, 5
        else:
            rr_x, rr_y = 0, 0
        rr_x2, rr_y2 = rr_x // 2, rr_y // 2
        if self._bfill:
            # 2 filled rectangles
            draw.rectangle((x, y + rr_y2, x + w, y + h - rr_y2), fill=self._bg)
            draw.rectangle((x + rr_x2, y, x + w - rr_x2, y + h), fill=self._bg)
        else:
            # 2 vertical lines
            for xoffs in (0, w):
                if (seg_side == Side.LEFT and xoffs == 0) or \
                        (seg_side == Side.RIGHT and xoffs == w):
                    vtx = [[(x + xoffs, y + rr_y2), (x + xoffs, seg[0][1])],
                           [(x + xoffs, seg[1][1]), (x + xoffs, y - rr_y2 + h)]]
                else:
                    vtx = [[(x + xoffs, y + rr_y2), (x + xoffs, y - rr_y2 + h)]]
                for v in vtx:
                    draw.line(v, fill=fill, width=wid)
            # 2 horizontal lines
            for yoffs in (0, h):
                if (seg_side == Side.TOP and yoffs == 0) or \
                        (seg_side == Side.BOTTOM and yoffs == h):
                    vtx = [[(x + rr_x2, y + yoffs), (seg[0][0], y + yoffs)],
                           [(seg[1][0], y + yoffs), (x - rr_x2 + w, y + yoffs)]]
                else:
                    vtx = [[(x + rr_x2, y + yoffs), (x - rr_x2 + w, y + yoffs)]]
                for v in vtx:
                    draw.line(v, fill=fill, width=wid)
        # 4 rounded corners
        for xoffs, yoffs, sa in ((0, 0, 180),
                                 (w - rr_x, 0, 270),
                                 (w - rr_x, h - rr_y, 0),
                                 (0, h - rr_y, 90)):
            ea = (sa + 90) % 360
            if self._bfill:
                draw.pieslice((x + xoffs, y + yoffs,
                          x + xoffs + rr_x, y + yoffs + rr_y),
                         sa, ea, outline=self._bg, fill=self._bg)
            else:
                draw.arc((x + xoffs, y + yoffs,
                          x + xoffs + rr_x, y + yoffs + rr_y),
                         sa, ea, fill=fill)

    def _calc_tail(self, x, y, w, h, tx, ty):
        bb = (x - 20, y - 20, x + w + 20, y + h + 20)
        if bb[0] <= tx <= bb[2] and bb[1] <= ty <= bb[3]:
            seg, side = None, None
        else:
            tw, th = w // 8, h // 8  # tail width/height
            # two lines through the bounding box, diagonally
            m1, m2 = h / w, -h / w
            b1 = y - m1 * x
            b2 = y + h - m2 * x
            # print('@@ m1={}, b1={} ;; m2={} b2={}'.format(
            #    m1, b1, m2, b2))
            # figure out where tail end is relative to 4 areas
            # these 2 lines divide the plane into
            l1_y = m1 * tx + b1
            l1 = -1 if  1.0 * ty > l1_y else 1
            l2_y = m2 * tx + b2
            l2 = -1 if 1.0 * ty > l2_y else 1
            #print('@@ tx={}, ty={}, l1_y={}, l2_y={} :: l1={} l2={}'.format(
            #    tx, ty, l1_y, l2_y, l1, l2))
            # with -1 for below and 1 for above, get coords
            # for two points defining line segment for start of tail
            if l1 > 0 and l2 > 0:  # top
                seg = [(x + (w//2) - tw, y), (x + w//2 + tw, y)]
                side = Side.TOP
            elif l1 > 0 and l2 < 0:  # right
                seg = [(x + w, y + h//2 - th), (x + w, y + h//2 + th)]
                side = Side.RIGHT
            elif l1 <0 and l2 > 0:  # left
                seg = [(x, y + h//2 - th), (x, y + h // 2 + th)]
                side = Side.LEFT
            else:  # bottom
                seg = [(x + w // 2 - tw, y + h), (x + w // 2 + tw, y + h)]
                side = Side.BOTTOM
        return seg, side
