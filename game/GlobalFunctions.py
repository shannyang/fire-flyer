import pygame
import os

def reverse(l):
    # Readable function to reverse lists
    return l[::-1]

# From Pete Shinner's line-by-line Chimp tutorial
# http://www.pygame.org/docs/tut/chimp/ChimpLineByLine.html

def load_image(name, colorkey=None):
    try:
        image = pygame.image.load(name)
    except pygame.error, message:
        print 'Cannot load image:', name
        raise SystemExit, message
    image = image.convert()
    if colorkey is not None:
        if colorkey is -1:
            colorkey = image.get_at((0,0))
        image.set_colorkey(colorkey)
    return image, image.get_rect()

def load_sound(path):
    class NoneSound(object):
        def play(self): pass
    if not pygame.mixer:
        # Sounds are disabled, return a dummy object to prevent crashing
        return NoneSound()
    try: sound = pygame.mixer.Sound(path)
    except pygame.error, message:
        print "Cannot load sound:", path
        raise SystemExit, message
    return sound
