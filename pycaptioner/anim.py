"""
Functions for animated images.
"""
from PIL import Image
import numpy

def process_frames(img, func, mode='P'):
    """Process an animated image, applying func() to each frame.

    Args:
        img (ImageSequence): Animated image (i.e. GIF)
        func: Function taking an Image and returning an Image

    Returns:
        (list) List of numpy arrays that can be saved by imageio.mimsave()

    """
    sequence, frame_num = [], 0
    while True:
        try:
            img.seek(frame_num)
        except EOFError:
            break
        new_img = img.copy()
        new_img.paste(img)
        mod_img = func(new_img)
        np_img = numpy.array(mod_img)
        sequence.append(np_img)
        frame_num += 1
    return sequence

