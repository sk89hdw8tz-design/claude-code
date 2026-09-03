# Interior close-review brief (1912 Galveston Sanborn mosaic)

`win_NN.jpg` are 1:1 windows of the finished mosaic — 1 px = 0.1725 ft, the
plates' own resolution, exactly what the print carries. They are sampled on
a grid across the mapped city, so most fall inside a plate rather than on a
seam.

Look for anything that would be wrong in a printed historical map:

- **seam defect**: a street, block face, alley, rail line or pipe run that
  steps, doubles or breaks; a street name or width numeral printed twice; a
  building split with mismatched halves.
- **furniture**: a plate number, plate title, north arrow, scale bar or
  border rule printed over drawn map content.
- **gap**: unpainted white canvas inside the mapped city.
- **wrong owner**: a strip where one plate's blank or coarse drawing covers
  ground the neighbour draws in detail.
- **artefact**: anything that is not on an original plate — a blur, a
  smeared edge, a repeated patch of texture, a resampling stair-step on a
  straight rule, a colour that no Sanborn plate uses.

NOT defects, and not to be reported: paper tone differences between plates,
foxing, stains, edge darkening, the plates' own hand lettering, an
adjoining-sheet numeral or a compass rose sitting in a roadway or on water
(the accepted master keeps those), and the two plates drawing the same
street at different widths (a source disagreement in the 1912 record).

Return the structured schema you were given. Name streets, blocks and
buildings concretely; give positions as fractions of the window (x, y from
the top-left, 0-1). If a window shows only clean map, say so.
