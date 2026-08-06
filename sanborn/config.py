"""Constants for the Galveston Sanborn composite build.

All values verified in the prior manual run (see CLAUDE_CODE_BUILD_SPEC.md).
Pitches are constants of each edition; fix them and solve only for phase.
"""

import os

WORK_ROOT = os.environ.get(
    "SANBORN_WORK",
    "/tmp/claude-0/-home-user-claude-code/2bd63ebc-a879-5d86-b98a-dc1ab929f20f/scratchpad/sanborn",
)
SOURCES_DIR = os.path.join(WORK_ROOT, "sources")
BUILD_DIR = os.path.join(WORK_ROOT, "build")
DELIVER_DIR = os.path.join(WORK_ROOT, "deliver")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# Detection runs at this width regardless of source scale; coordinates are
# scaled back up afterwards. Same relative precision, much faster.
DETECT_WIDTH = 3400

# Global grid model: X = avenue_index * P_AV, Y = (street_number - 16) * P_ST
STREET_ORIGIN = 16

EDITIONS = {
    "1885": {
        "source": "loc",
        "loc_item": "sanborn08539_001",
        "loc_master_base": (
            "https://tile.loc.gov/storage-services/master/gmd/gmd403m/g4034m/"
            "g4034gm/g4034gm_g085391885/08539_1885-{num:04d}.tif"
        ),
        "native_size": (6450, 7650),          # (w, h) of every LoC master
        "working_set": [2, 3, 4, 5, 6, 7, 9, 10, 11, 14],
        "index_sheet": 1,                      # reference only, never in art
        "pitch_av": 1856.0,                    # at 6450 px master scale
        "pitch_st": 2170.0,
        "paper_bgr": (176, 202, 216),
        # Panels verified off-grid or off-scale — excluded, disclosed:
        # sheet 3 upper panel (street pitch ~606, different scale)
        # sheet 11 everything except upper-left panel
        # sheet 4 right panel (east of Broadway, outside crop)
    },
    "1877": {
        "source": "ut",
        "ut_url": (
            "https://maps.lib.utexas.edu/maps/sanborn/g-i/"
            "txu-sanborn-galveston-1877-{num:02d}.jpg"
        ),
        "ut_referer": "https://maps.lib.utexas.edu/maps/sanborn/g.html",
        "native_size": (3400, 4124),           # approx; verify per sheet
        "working_set": [3, 4, 9, 10],
        "all_sheets": [2, 3, 4, 5, 6, 7, 8, 9, 10],  # A2 reads every sheet
        "index_sheet": None,                   # 1877 has no index sheet
        "pitch_av": 972.0,                     # at 3400 px native scale
        "pitch_st": 1135.0,
        "paper_bgr": (153, 179, 194),
        # sheet 8: nine disconnected panels — excluded, disclosed.
        # sheet 10: physical tear through blocks 441-442 — retained, authentic.
    },
}

# Pitch at the 3400 px detection scale is the same for both editions
# (both editions print at the same physical scale; UT scans are 3400 wide,
# LoC masters downsample to 3400 for detection).
PITCH_AV_DETECT = 972.0
PITCH_ST_DETECT = 1135.0

# Off-scale panel rejection: measured pitch deviating more than this fraction
# from the edition pitch means the panel is off-scale — exclude and disclose.
PANEL_PITCH_TOLERANCE = 0.05

# Affine validation gate (per-axis scale vs 1.000)
SCALE_WARN = 0.01    # flag
SCALE_FAIL = 0.02    # stop: a misidentified grid line

# Compositing (values at 3400 detection scale; scale up for LoC masters)
CLIP_SHIFT_3400 = 90     # push clip past boundary street so labels are unique
FEATHER_3400 = 24        # narrow feather only
COM_REFINE_WINDOW = 80   # center-of-mass refinement half-window, px

GAIN_CLAMP = (0.93, 1.08)  # per-channel paper-tone gain limits

# Known genuine gap (1885): Ave G-H x 18th-20th is unmapped by the edition.
# Fill with flat paper tone and disclose. Never generate content.

TARGET = {"avenue": "E", "street": 22}  # 22nd & Postoffice (Avenue E)
