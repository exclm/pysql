# Small utilities for detecting common image types based on the first
# few bytes of their content.

# by Ole Laursen, sponsored by IOLA 2009

def is_jpg(data):
    """True if data is the first 11 bytes of a JPEG file."""
    return data[:4] == '\xff\xd8\xff\xe0' and data[6:11] == 'JFIF\0'

def is_png(data):
    """True if data is the first 8 bytes of a PNG file."""
    return data[:8] == '\x89PNG\x0d\x0a\x1a\x0a'

def is_tiff(data):
    """True if data is the first 4 bytes of a TIFF file."""
    return data[:4] == 'MM\x00\x2a' or data[:4] == 'II\x2a\x00'

def is_gif(data):
    """True if data is the first 4 bytes of a GIF file."""
    return data[:4] == 'GIF8'

def extension_from_data(data):
    """Returns extension (like '.jpg') from first 11 bytes of image data.

    An empty string is returned if no match is found."""
    if is_jpg(data):
        return ".jpg"
    elif is_png(data):
        return ".png"
    elif is_tiff(data):
        return ".tif"
    elif is_gif(data):
        return ".gif"
    
    return ''

def extension_from_file(path):
    """Returns extension (like '.jpg') based on content of image file at path.

    An empty string is returned if no match is found."""
    f = file(path, 'r')
    ext = extension_from_data(f.read(11))
    f.close()
    return ext
    
