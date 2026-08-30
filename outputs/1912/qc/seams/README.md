# Why there is no photometric seam score for the city mosaic

`tools/seamqc.py` measures seam agreement by warping both sheets into the same
mosaic window and phase-correlating them. It was run against the 1912 city
seams and **its output is not used as a gate**, for a reason worth recording.

Adjacent Sanborn sheets barely share mapped ground. They abut: each sheet's
edge carries border furniture — the neatline, the title block, and the
"SEE SHEET n" continuation notes that neighbours print *differently by
design*. `seam_10-43_100.png` is the evidence: sheets 10 and 43 are frozen
core sheets that passed the prior accepted QA and printed correctly in the
27×40 master, yet the seam window shows one panel reading "43 OR F…" and the
other "10 OR F…". Those are each sheet's pointer to the other. Correlating
them measures the difference between two different pieces of text, and duly
reported a ~100 px "offset" that does not exist on the ground.

Trimming the margin band fixes the honesty problem but removes almost all the
data: on a 12-pair sample, requiring the whole window inside both sheets'
printed extents left 1 of 12 seams measurable. Sweeping the trim and window
size moved the reported median across seams from 36 px to 99 px — a number
that swings 3× on a tuning knob is not a measurement, and shipping it as a
seam grade would be worse than having no number.

**What settled it.** A full sweep was run anyway (132 adjacent pairs, 87
measurable) and checked against seams inspected by eye in the rendered
mosaic. It fails in both directions:

- *False positives.* It reported ~96 px on 9|11 and ~103 px on 10|43, both
  frozen core seams. `../human/HQ9_09-10_core_control_clean.jpg` shows the
  core rendering cleanly — one street label, lot numbers continuous, nothing
  doubled.
- *False negative, the decisive one.* Seam 75|76 came back **"no-signal"**.
  That is the single worst defect found in the whole 1912 mosaic: the Avenue F
  / Church label is drawn twice, ~86 ft apart, with the cut between the two
  copies (`../human/HQ9_75-76_duplicated_street_label.jpg`).

A metric that misses the worst defect in the mosaic while flagging good seams
is not a screening tool either, so its output is not kept. The seams were
graded by eye off the rendered mosaic instead — see HQ-9.

What *is* well posed for this mosaic, and is used instead:

- **`../tiling_audit.json`** (`tools/tiling.py`) — exact polygon geometry, not
  sampled pixels: is the city one connected piece, does any ground go
  unclaimed (gap), does any pixel have two owners (overlap). This is the
  brief's Stage 4 gate and it found a real defect — see HQ-8, the missing
  sheet 72.
- **`../../recipe/qc/solve_residuals.json`** and the held-out landmark gate —
  registration accuracy measured against identified ground control, which is
  what "do the sheets agree" actually means.
- The rendered mosaic itself, read at 100%.

`seam_15-16_100.png` is kept as the counter-example: two tie-placed outer
sheets whose shared lettering ("MECHANIC") really is displaced between them.
Where genuine shared content exists, the tool does see it — there is just not
enough of it, often enough, to grade every seam this way.
