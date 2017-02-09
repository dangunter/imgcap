"""
Add text to images
"""
import textwrap
from PIL import Image, ImageDraw, ImageFont


class Side(object):
    """Enumeration for 'side' of an image."""
    TOP = 1
    RIGHT = 2
    BOTTOM = 3
    LEFT = 4

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
    font_file = "/usr/share/fonts/TTF/DroidSans.ttf"
    default_text_fill = (0, 0, 0, 255)
    default_text_bg = (255, 255, 255, 255)
    paragraph_marker = '//'

    def __init__(self, im, side=Side.BOTTOM, space=0, font_size=16,
        text_fill=default_text_fill, text_bg=default_text_bg,
        padx=default_padding, pady=default_padding):
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
        self._font = ImageFont.truetype(self.font_file, font_size)

    def addtext(self, text):
        """

        Args:
            text (str): Text to add
        """
        self._text.append(text)

    def _wrap_text(self, w=0, h=0):
        # calculate height/width of single character
        draw = ImageDraw.Draw(Image.new('RGBA', (1000, 1000)))
        fx, fy = draw.multiline_textsize('x', font=self._font)
        text = ' '.join(self._text).strip()
        if w > 0:
            # known width
            wrap_width = w / fx
            # wrap the text
            lines = self._wrap(text, wrap_width)
        elif w == 0:
            if h < fy:
                raise ValueError('Image too small to fit one line of text next to it')
            # unknown width, need to calculate it
            # start with perfect wrapping and expand out
            n = len(text)
            lines, max_lines = [], h // fy
            wrap_width = max(n // max_lines, 8)
            while wrap_width < n:
                #print('@@ wrap_width={} max_lines={}'.format(wrap_width, max_lines))
                lines = self._wrap(text, wrap_width)
                if len(lines) <= max_lines:
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
        else:
            text_width = 0 if self._spc == 0 else self._spc - 2 * self._padx
            text_height = self._base.size[1] - 2 * self._pady
            new_width = base_width + self._spc
            new_height = self._base.size[1]
            text_yoffs = self._pady
            if self._side == Side.LEFT:
                text_xoffs = self._padx
            else:
                text_xoffs = base_width + self._padx
        wrapped_text, text_dim = self._wrap_text(w=text_width, h=text_height)
        # auto-calculated text width or height
        if self._spc == 0:
            if self._side in (Side.TOP, Side.BOTTOM):
                new_height += text_dim[1] + 2 * self._pady
            else:
                new_width += text_dim[0] + 2 * self._padx
        cp = Image.new(mode='RGBA', size=(new_width, new_height),
                       color=self._bg)
        # paste original image back in
        if self._side == Side.TOP:
            cp.paste(self._base, (0, new_height - base_height))
        elif self._side == Side.BOTTOM or self._side == Side.RIGHT:
            cp.paste(self._base, (0,0))
        elif self._side == Side.LEFT:
            cp.paste(self._base, (new_width - base_width, 0))
        else:
            raise ValueError('Bad value for side')
        # draw text
        draw = ImageDraw.Draw(cp)
        draw.multiline_text((text_xoffs, text_yoffs), wrapped_text,
                            font=self._font, fill=self._fill)
        return cp

