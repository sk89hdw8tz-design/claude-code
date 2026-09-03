# Proposal: pair_17_18_y — settled value (8th St SOUTH block face), apply via --units 17 18 --similarity

Opus evidence agent; dry-run only, nothing applied (real pair_17_18_y.json still REJECTED).

Settled control: axis street, corridor "8th St — SOUTH block face", a_native (17) = 2685.4, b_native (18) = 2685.6,
read at the extent x-centres localsolve.point uses (17: x=1660.0, 100-block, printed 70'; 18: x=1653.5,
400-block, printed 80'). Fit rms 0.14–0.36 px.

Why the face, not the centre: at their evaluation points the plates draw different roadway widths (17: 70';
18: 80'); plate 17's own 70'/80' half-width difference = 17.05 px = 5.6 ft, exactly the two Gate-A
reviewers' disagreement (2581.1 vs 2564.0). The south face is continuous on both plates (17: 2685.36 →
2679.87 with no break at Strand; the widening is taken off the north side; 18: 2685.60 → 2688.00).
Identity: both print 8TH ST.; 17 carries 101–123/110–124 then 201–223/202–224; 18 carries 301–323 east of
Mechanic; 200|300 break on Ave C as the accepted x-tie argues. One street off would move ~1,200 px.

Independent tie: seawall double line (16.0/16.1 px separation, slopes 0.4° apart). Plate-internal
distance 8th St S face → seawall centreline along the Ave C meridian: 576.8 ft (17) vs 575.4 ft (18),
0.24% apart. Step is placement plus sheet scale, not a drawing difference.

Current steps at Ave C meridian (17 − 18): 8th S face +10.07 ft; 7th St frontage +14.75; seawall +14.49;
Ave C x +0.21.

Dry runs: translation --units 18 is NOT the fix (closes a third, breaks Ave C x to 3.0 ft).
--units 17 18 --similarity: 18 samples, residual median 1.5 / max 3.4 ft; 17 scale +0.22%, rot 0.425→0.329°;
18 scale −0.04%, rot 0.507→0.332°. bandresid 333 controls median 1.60→1.62 ft, >6 ft 12→11 (none new);
pair_17_18_y 13.1→3.4. Predicted steps after: 8th S 0.34 ft, 8th N −0.13, 7th St 3.98, seawall 3.18
(residual = drafting-scale difference; cannot be absorbed further without breaking 17|21, 17|22, 18|19, 18|22).

Note: bandresid reports 13.1 ft for this pair vs measured 10.07 ft (horizontal-line model vs 0.15–0.2°
tilted street). Alternative meridian pair a=2679.1/b=2688.3 matches the band exactly but under-drives the
solve (leaves 8th 2.35, 7th 6.32, seawall 5.70). Recommend the extent-centre pair.

Change:
- controls/pair_17_18_y.json: status ACCEPTED, corridor "8th St — SOUTH block face", a_native 2685.4,
  b_native 2685.6, record previous rejected values and this reason.
- python3 tools/localsolve.py --year 1912 --units 17 18 --similarity --apply
Related seams to re-check: 17|18 (edge_00/01), 17|21, 17|22, 18|19, 18|22, 18|23.
