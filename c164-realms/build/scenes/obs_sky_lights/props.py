"""The models this scene shows: those of the lines whose build() it calls for the real building (the
main line's, if it has any, and the props line's: the lamps, the wall wash's projector among them)."""
from scenes.obs import main, props


def build_models():
    return {**(main.models() or {}), **(props.models() or {})}
