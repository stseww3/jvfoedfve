"""The models this scene shows: those of the lines whose build() it calls for the real building (the
main line's, if it has any, and the props line's: the lamps, the wall wash's projector among them)
and those of the lines whose machines and rooms stand inside it (machines, interiors)."""
from scenes.obs import interiors, machines, main, props


def build_models():
    return {**(main.models() or {}), **(machines.models() or {}), **(interiors.models() or {}),
            **(props.models() or {})}
