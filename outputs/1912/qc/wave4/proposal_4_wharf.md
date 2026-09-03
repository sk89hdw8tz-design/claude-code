# Proposal: wharf sheet 4 (and dependent sheet 3) — placement wrong by ≈348 ft

Source: periphery re-check edge_15 (plate 4 elevator vs plate 13 Elevator "B"); Opus evidence agent, nothing applied.

Verdict: SAME BUILDING. Plate 4's "ELEVATOR (IRON CLAD) (For Report See Sheet 13)" is plate 13's
Elevator "B" (the sheet-13 report block is headed "Galveston Wharf Co's Elevator B"). Both copies sit
between 28th and 29th, hard against 29th, body centre 225.8 ft (plate 4) / 225.6 ft (plate 13) west of
the Ave A centreline; same annexes (Br. Ck. square, engine house with two boilers, red annex, conveyer
raised 40' to the slip). Block 748, addresses 2802–2828 / 2801–2827.

Cause: tools/wharfplace.py WHARF["4"]["ave_a_chain"] pins plate 4's Ave A to plate 15 x-chain 0
([29,235]) which is the scan/neatline border (plate 15 extent x0=79), not a corridor. Plate 15's Ave A
is x-chain 1 ([1044,1254], 210 px = 72 ft, "AVE. A OR WATER" + G.C.&S.F.R.R. printed, 3100-block
addresses 3102–3126 / 3101–3127). Chain0→chain1 separation = 349.5 ft; measured misplacement of plate
4's Ave A at 29th St = 2016.9 px = 347.9 ft west (351.8 at 30th; y agrees to 0.5 px).

Why not one block off: inland of chain 1 is "AVE. B OR STRAND" (printed on 13 and 15); bayward there is
no avenue, only the Wharf Co terminal tracks and slips. Plate 13 stays None: its three x-chains are all
paired one face too far west (lattice.json defect on plate 13, note only).

Change:
- tools/wharfplace.py: WHARF["4"]["ave_a_chain"] = {"13": None, "15": 1} with the comment above.
- python3 tools/wharfplace.py --year 1912 --sheet 4 --apply, then --sheet 3 --apply (3 reads 4's transform).
Dry-run: sheet 4 t (−21273.5,12286.0) → (−19260.5,12285.0), scale 3.9724→3.9766, residual median 1.1→1.0,
max 3.2→3.3 ft; sheet 3 t → (−19577.8,23328.0) = +350.4 ft, residual median 1.6→1.5, max 7.8→6.4 ft.
Rewritten frontage controls: pair_4_13.a_native 3147.4→2637.8, pair_4_15.a_native 3137.2→2627.6 (b 200
unchanged), both just west of the elevator body (2727–2821) so plates 13/15 own the elevator and yard.
After the move the elevator copies coincide (Ave A 1.6 ft; corners 4–12 ft = drawn-size difference).

Related: 4|13, 4|15, 3|4, 3|67, 3|75 (the 660-ft wharf source gap must be re-measured after the move),
5a/5b|4 frontage pairs, periphery edge_15/edge_08.
