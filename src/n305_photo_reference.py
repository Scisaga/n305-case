"""Manually reviewed pixel traces from the original N305 case photographs.

These are image-plane observations, not motherboard coordinates.  Keeping
them separate prevents a photographed aperture center from being mistaken for
the functional center of a connector on the PCB.
"""

from __future__ import annotations


BOARD_01_SOURCE = "pics/01-n305-mainboard-component-side-overall-width-measurement.jpg"
BOARD_01_CROP_PX = (700, 850, 2400, 2700)

# PCB corners in source pixels, ordered 07/04, 07/06, 05/06, 05/04 for
# conversion to (-50,+52.75), (+50,+52.75), (+50,-52.75), (-50,-52.75).
BOARD_01_PCB_QUAD_PX = (
    (809, 913),
    (2350, 910),
    (2351, 2638),
    (810, 2637),
)

# Manually reviewed outer sheet-metal/volute outline in the same source photo.
# This raw evidence is converted once to the PCB-aligned millimetre profile in
# n305_mainboard_reference.py; the CAD builder does not read these pixels.
BOARD_01_BLOWER_OUTLINE_PX = (
    (1130, 1505),
    (1200, 1505),
    (1270, 1560),
    (1390, 1490),
    (1545, 1450),
    (1695, 1465),
    (1830, 1535),
    (1925, 1655),
    (1970, 1810),
    (1960, 1970),
    (1900, 2110),
    (1805, 2220),
    (1715, 2305),
    (1660, 2330),
    (1130, 2330),
)
BOARD_01_FAN_CENTER_PX = (1576, 1831)


CASE_04_SOURCE = "pics/机箱盒子04.jpg"
CASE_04_CROP_PX = (480, 1500, 3380, 2240)

# ``bbox_px`` is the visible main opening at full 4096 x 3072 resolution.
# RJ45's 15 x 10 mm bbox is deliberately the main window only; its relief is
# an extra 4.5 x 1 mm feature below that window.
CASE_04_PHOTO_TRACES = (
    {
        "name": "dc",
        "bbox_px": (602, 1890, 801, 2089),
        "shape": "circle",
        "confirmed_size_mm": (5.9, 5.9),
    },
    {
        "name": "hdmi_1",
        "bbox_px": (953, 1908, 1465, 2095),
        "shape": "photo_polygon",
        "confirmed_size_mm": (16.5, 5.8),
        "vertices_px": (
            (1050, 1908),
            (1383, 1908),
            (1465, 1978),
            (1465, 2095),
            (953, 2095),
            (953, 1978),
        ),
    },
    {
        "name": "headphone",
        "bbox_px": (1132, 1625, 1301, 1797),
        "shape": "circle",
        "photo_derived_size_mm": (5.4, 5.4),
        "scale_source": "neighboring HDMI 1 image scale; physical check pending",
    },
    {
        "name": "rj45",
        "bbox_px": (1586, 1785, 2047, 2093),
        "shape": "rj45_main_plus_relief",
        "confirmed_size_mm": (15.0, 10.0),
        "relief_size_mm": (4.5, 1.0),
    },
    {
        "name": "stack_dual_usb",
        "bbox_px": (2179, 1698, 2614, 2150),
        "shape": "roundrect",
        "confirmed_size_mm": (14.0, 14.5),
        "corner_radius_mm": 0.7,
    },
    {
        "name": "hdmi_3",
        "bbox_px": (2778, 1925, 3308, 2113),
        "shape": "photo_polygon",
        "confirmed_size_mm": (16.5, 5.8),
        "vertices_px": (
            (2867, 1925),
            (3211, 1925),
            (3308, 1990),
            (3308, 2113),
            (2778, 2113),
            (2778, 1990),
        ),
    },
)


CASE_06_SOURCE = "pics/机箱盒子06.jpg"
CASE_06_CROP_PX = (1050, 1500, 3300, 2050)

# Exterior-photo traces at the full 4096 x 3072 source resolution.  The two
# USB openings retain their raw pixel positions and perspective skew only as
# photographic evidence.  The mechanical reference normalizes the identical,
# same-datum connectors to one shared Z center.  ``vertices_px`` are the
# intersections of the four straight edge runs before applying the
# photographed rounded corners.
CASE_06_PHOTO_TRACES = (
    {
        "name": "usb_left",
        "bbox_px": (1235, 1674, 1650, 1865),
        "shape": "photo_roundrect",
        "confirmed_size_mm": (12.8, 5.5),
        "vertices_px": (
            (1235, 1674),
            (1650, 1680),
            (1649, 1865),
            (1235, 1860),
        ),
        "corner_radius_px": 24.0,
    },
    {
        "name": "usb_right",
        "bbox_px": (1851, 1689, 2262, 1876),
        "shape": "photo_roundrect",
        "confirmed_size_mm": (12.8, 5.5),
        "vertices_px": (
            (1851, 1689),
            (2262, 1698),
            (2262, 1876),
            (1851, 1868),
        ),
        "corner_radius_px": 24.0,
    },
    {
        "name": "power_switch",
        "bbox_px": (2722, 1657, 3032, 1962),
        "shape": "circle",
        "confirmed_size_mm": (9.4, 9.4),
    },
)
