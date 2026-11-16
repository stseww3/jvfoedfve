"""Test scene of the work package site/viaduct (plan/packages/site/viaduct.md): the stone viaduct that
takes the railway from the foot of the incline round to the south and down into the cloud.

The hill as it stands in the master scene, built the way the cable station's test scene builds it
(scenes.obs_site_cablecar: the site line whole, the main building, the machines, the props and the
sky line with its sea of cloud), so the pictures keep up with the lines as their packages are
merged. Nothing in this scene stands in for anything.

The views (shots.json): the sweep from the lower platform's edge, from the head of the grand stair
and from the platform's south end; where the iron incline meets the stone; the inner face of the
curve from the air, level with the deck; one arch from ten blocks and the parapet from two (the
card's two distances); what a traveller sees coming up the far straight and round the curve; and
one from above.
"""
from scenes import obs_site_cablecar as _hill

BIOME = _hill.BIOME
BIOME_MARGIN = 120
BIOME_MARGIN_Y = _hill.BIOME_MARGIN_Y
LINES = _hill.LINES
TIME = _hill.TIME

build = _hill.build
build_models = _hill.build_models
write_pack = _hill.write_pack
