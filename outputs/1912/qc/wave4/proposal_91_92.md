# Proposal: pair_91_92.json (Ave G / Winnie) — value-wrong, identity unchanged

Source: interior 1:1 sweep win_58 (rect [4302,50844,5802,52344]); Opus diagnosis, nothing applied.

Defect: the 30" supply main down Ave G and its caption print twice, ~61 mosaic px (10.5 ft) apart at the south end (≈4 ft at the north end), one copy per plate. Plate 91's copy lies ~17 px WEST of the 91|92 overlap band, so no cut inside the band can suppress it. dp_cut is not at fault (chose the west side candidate; blank-band rule correctly did not fire, ink ratio 0.83).

Cause: the observer built each plate's centreline as curb ± half-width using 80' (120.3 px). That "80'" is lettered in the E–W cross street beside the 6" W. PIPE, not in Ave G. Both plates letter "70" inside the Ave G roadway (u91 native ≈3145,3500; u92 native ≈128–150,3500).

Width proof needing no label (native px, y 3230–3430): plate 91 west curb 3053.0, shared pipe 3128.9 (75.9 px); plate 92 east curb 240.0, same pipe 113.5 (126.5 px); sum 202.4 px. A 70' avenue on plate 91 at the same latitude measures 209.5 px (casings 1661.5/1871.0); 80' would need ~240 px.

Independent tie (width-free): the same pair of dashed mains + T.H. hydrant at native y 1150–1500 — plate 91: 3139.5 / 3187.0 (Δ47.5); plate 92: 117.9 / 162.3 (Δ44.4); implied plate-to-plate x offset 3021.6/3024.7. The accepted control asserts 3056.4 (~34 px ≈ 11.6 ft too wide). Corrected construction with half-width 105.2 (70') gives a_native 3162.7, b_native 136.5 → offset 3026.2, within ~1 ft of the pipe tie.

Change:
- outputs/1912/recipe/controls/pair_91_92.json: a_native 3177.8 → 3162.7; b_native 121.4 → 136.5; record previous values and this reason; why_not_one_block_off unchanged (600/700 address break confirmed at 44th St: 618–624 west, 702–710 east; the alternative line pairing would need a line at 92 native ≈210, not drawn; a block is ~1000 px).
- then python3 tools/localsolve.py --year 1912 --units 91 --similarity --apply (91 disagrees with BOTH its x-neighbours: pair_91_92 +6.2 and pair_83_91_x +6.2 equal and opposite; 92 is well tied by pair_84_92_x and pair_92_93). Simulated: 91 moves ≈+4–6 ft east, rotation 0.256°→0.178°, residuals median 0.6 / max 1.3 ft (from 1.6 / 6.2). Fallback: free 91+92 together.

Related seams to re-check after: 63_70 (5.1 ft step + clipped pipe caption), 63_71 (10" main swallowed by a legend patch — check after furniture fixes), 64_71 (33 px ≈ 11.5 ft westward jog on the 6" pipe; "plate 64 misplaced"), 20_20b (6" pipe steps ~3.5 ft).
