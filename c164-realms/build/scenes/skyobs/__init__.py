"""Sky observatory: an original floating-island scene used to test how far scripted art can go."""
from artkit.canvas import Canvas

from . import terrain


def build():
    c = Canvas()
    terrain.build(c)
    return c
