"""Direction prompts for every generated shot (single source, also copied into DIRECAO.md)."""

KEEP = (
    "KEEP EXACTLY AS IN THE FIRST FRAME, NOTHING MAY CHANGE, APPEAR OR DISAPPEAR: the tower's silhouette and "
    "height, the timber-lined crown, every floor slab with its warm timber soffit, the rhythm of single and "
    "double height bays, the tall dark vertical wall strip, the glass balustrades and the planting on each "
    "terrace, which windows are lit and which are dark, the sheer curtains, the neighbouring buildings, the red "
    "heliport pavilion and pier, the river, its reflections and the blue-hour sky. The surroundings only grow "
    "and slide out of frame as the camera advances."
)
DONT = (
    "DO NOT add or remove storeys, balconies, windows, trees or buildings; do not morph, melt, bend or redesign "
    "the facade; do not change the light, the time of day or the weather; no people appearing, no birds, boats, "
    "cars, text, logos or lens flares."
)

FLIGHT = {
    'loft4': (
        "One single continuous shot, no cuts and no transitions. A real camera move only: a perfectly stabilised "
        "drone flying straight in across the River Thames toward one home on the Nest Battersea tower, long lens. "
        "Image 1 is the first frame and image 2 is the last frame; they show the same building at the same moment, "
        "and the video travels from image 1 to image 2 by moving the camera only.\n"
        "CAMERA: starts still on image 1, then a smooth dolly-in along one straight line toward the target. Gentle "
        "acceleration during the first second, steady travel, soft deceleration during the last second, settling "
        "exactly on image 2 with no overshoot and no drift. It rises slightly so it arrives level with the target. "
        "No orbit, no sideways sweep, no roll, no shake, no zoom pumping. Verticals stay vertical. The target keeps "
        "growing steadily toward the centre of frame.\n"
        "TARGET: the double height garden terrace about two thirds of the way up the river-facing facade, in the "
        "column just right of the tall dark vertical wall strip: a small tree and a dark round parasol in front of "
        "floor-to-ceiling glazing with warm, glowing sheer curtains, two storeys tall with no slab in between.\n"
        + KEEP + "\n" + DONT
    ),
    'bung3': (
        "One single continuous shot, no cuts and no transitions. A real camera move only: a perfectly stabilised "
        "drone flying straight in across the River Thames toward one home on the Nest Battersea tower, long lens. "
        "Image 1 is the first frame and image 2 is the last frame; they show the same building at the same moment, "
        "and the video travels from image 1 to image 2 by moving the camera only.\n"
        "CAMERA: starts still on image 1, then a smooth dolly-in along one straight line toward the target, "
        "descending gently, because the target is in the lower half of the tower. Gentle acceleration during the "
        "first second, steady travel, soft deceleration during the last second, settling exactly on image 2 with "
        "no overshoot and no drift. No orbit, no sideways sweep, no roll, no shake, no zoom pumping. Verticals stay "
        "vertical. The target keeps growing steadily toward the centre of frame.\n"
        "TARGET: a single storey planted garden terrace in the lower half of the river-facing facade, in the column "
        "just right of the tall dark vertical wall strip: a dark parasol, a small tree and full planters behind a "
        "glass balustrade, in front of warm, glowing floor-to-ceiling glazing.\n"
        + KEEP + "\n" + DONT
    ),
}

INSIDE = {
    'loft4': (
        "One continuous shot, no cuts, no fades, no transitions. The camera moves only. From the outside view of the "
        "home in image 1 it glides straight forward at eye level, across the planted terrace past the small tree, "
        "through the open floor-to-ceiling glass door between the sheer curtains, and into the double height "
        "living room, ending exactly on image 2, which looks into the room. Slow, smooth, perfectly stabilised, "
        "like a gimbal walk-in. The facade, the terrace, the planting, the curtains and the room keep their shape; "
        "they only pass by the camera. Warm evening light inside, blue hour outside. No people, no text, no flicker, "
        "no change of light."
    ),
    'bung3': (
        "One continuous shot, no cuts, no fades, no transitions. The camera moves only. From the outside view of the "
        "home in image 1 it glides straight forward at eye level, under the parasol and between the planters of the "
        "garden terrace, through the open sliding glass door between the sheer curtains, and into the living and "
        "dining room, ending exactly on image 2, which looks into the room. Slow, smooth, perfectly stabilised, like "
        "a gimbal walk-in. The facade, the terrace, the planting, the curtains and the room keep their shape; they "
        "only pass by the camera. Warm evening light inside, blue hour outside. No people, no text, no flicker, no "
        "change of light."
    ),
}

if __name__ == '__main__':
    for d in (FLIGHT, INSIDE):
        for k, v in d.items():
            print(k, len(v))
