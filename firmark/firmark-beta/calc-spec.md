# Calculation Specification — ASD Bending Member Check, NDS 2024

**Subject:** Simply-supported, single-span, prismatic sawn-lumber or glulam bending member under
uniformly distributed gravity load. Allowable Stress Design (ASD).

**Governing documents**

| Ref | Document |
|---|---|
| NDS | AWC *National Design Specification (NDS) for Wood Construction*, 2024 edition |
| NDS-S | AWC *NDS Supplement: Design Values for Wood Construction*, 2024 edition (+ Feb-2024 and Mar-2025 addenda) |
| ASCE 7 | ASCE/SEI 7-22, *Minimum Design Loads and Associated Criteria*, §2.4 (ASD combinations) |
| IBC | 2021/2024 *International Building Code*, Table 1604.3 (deflection limits) |

**Material data source (this repo):** `/workspace/firmark/material-databases/data/…`
Every reference design value and every section property used below is cited to a specific
file + record `id`. Values **not** present in that repo are flagged inline with
`[REPO GAP]` and consolidated in §9.

**Clause-number confidence convention:** clause numbers given bare are ones I am confident of.
Anything I am not certain of for the 2024 edition specifically is marked
**(clause number to verify)**. Do not let an implementer silently "clean up" those markers.

---

## 0. Notation, units, and the section-property source

### 0.1 Symbols

| Symbol | Meaning | Unit |
|---|---|---|
| `q_D, q_L, q_Lr, q_S` | Area loads: dead, floor live, roof live, snow | psf |
| `t_w` | Tributary width | ft |
| `s` | Framing spacing, on center | in |
| `L` | Clear span, simple span, center-to-center of bearings | ft |
| `L_in` | Span in inches = `12·L` | in |
| `w` | Uniform line load on the member | plf (lb/ft) |
| `w_in` | Uniform line load = `w/12` | lb/in |
| `b` | Member breadth (thickness), **dressed** | in |
| `d` | Member depth, **dressed** | in |
| `A` | Gross cross-section area `= b·d` | in² |
| `S` | Section modulus about bending axis `= b·d²/6` | in³ |
| `I` | Moment of inertia about bending axis `= b·d³/12` | in⁴ |
| `M` | Maximum moment | in-lb (internally) |
| `V` | Design shear | lb |
| `R` | Support reaction | lb |
| `f_b, f_v, f_c⊥` | Induced (actual) stresses | psi |
| `F_b, F_v, F_c⊥, F_t, F_c, E, E_min` | **Reference** design values (unadjusted) | psi |
| `F_b', F_v', …` | **Adjusted** (allowable) design values | psi |
| `F_b*` | `F_b ×` all applicable factors **except** `C_fu`, `C_V`, `C_L` | psi |
| `F_c*` | `F_c ×` all applicable factors **except** `C_P` | psi |
| `Δ` | Deflection | in |
| `DCR` | Demand-capacity ratio (unitless; ≤ 1.00 = passes) | — |

### 0.2 Internal unit discipline (non-negotiable for the implementation)

The app converts **once**, at the boundary between §1 and §3, and then works in
**pounds and inches** for every stress calculation. Reference design values in
NDS-S are psi; section properties are in inches. Mixing ft and in is the single
most common source of wrong wood calcs.

- Loads are entered in psf and ft/in and reduced to `w` in **plf** in §1.
- Moment is computed in **in-lb**: `M = 1.5·w·L²` where `w` is plf and `L` is **ft**
  (derivation: `M[ft-lb] = w·L²/8`; `M[in-lb] = 12·M[ft-lb] = 12·w·L²/8 = 1.5·w·L²`).
- Deflection is computed in **in**: `Δ = 22.5·w·L⁴ / (E'·I)` where `w` is plf,
  `L` is **ft**, `E'` is psi, `I` is in⁴
  (derivation: `Δ = 5·w_in·L_in⁴/(384·E'·I)`; substituting `w_in = w/12` and
  `L_in⁴ = 20736·L⁴` gives `5·20736/(12·384) = 22.5`).

Both closed forms are exact, not approximations. Implement them as written and unit-test the
two derivations against the long form.

### 0.3 Section properties

**Sawn lumber:** read dressed `b`, `d`, `A`, `S_x`, `I_x` directly from
`wood_sawn_section_properties_nds2024_table_1b.json` (NDS-S Table 1B, S4S dry dressed sizes,
Table 1A / PS 20 basis). Do **not** compute from nominal sizes. Record ids are
`sawn_secprop:s4s:<nominal>` (e.g. `sawn_secprop:s4s:2x10`). The seed's own
`derivation.formulas` field confirms `A=b·d; Sx=b·d²/6; Ix=b·d³/12`.

**Glulam:** the repo has **no NDS-S Table 1C standard glulam size table** `[REPO GAP #10]`.
It has manufacturer `record_type: "member_size_properties"` rows only (Boise Glulam, 67 rows;
Rosboro X-Beam 2.0E, 48 rows) in
`wood_glulam_current_official_public_2026_03_28.json`. For any glulam section not present
there, compute `A`, `S`, `I` from the net dressed `b × d` using the same rectangular formulas,
and surface a UI note that the section geometry was computed rather than read from a
tabulated source.

---

## 1. Load path — psf to plf

### 1.1 Tributary width

Two cases, and the app must know which one it is in because self-weight is handled differently:

**(a) Repetitive framing member** (rafter, floor joist, stud-framed member — the member is one
of a field of identical members):

```
t_w = s / 12                                  [ft], s in inches o.c.
```

**(b) Beam / header / girder** (the member collects load from framing on one or both sides):

```
t_w = (L_left / 2) + (L_right / 2)            [ft]
```

where `L_left`, `L_right` are the **horizontal** spans of the framing bearing on each side.
For a single-sided condition set the absent term to 0. For a ridge beam with equal rafter runs
each side, `t_w = L_rafter_run_left/2 + L_rafter_run_right/2`.

### 1.2 Line loads per load case

```
w_D  = q_D  · t_w        [plf]
w_L  = q_L  · t_w        [plf]
w_Lr = q_Lr · t_w        [plf]
w_S  = q_S  · t_w        [plf]
```

### 1.3 Self-weight rule

- **Case (a), repetitive framing:** self-weight is assumed to be inside `q_D`. The app must
  display: *"q_D is taken to include the framing member's own weight."* Do not add it twice.
- **Case (b), beam/header:** self-weight is **not** inside `q_D` (the psf allowance describes
  the framing above, not the beam). Add:

  ```
  w_sw = γ · A / 144        [plf],  γ = density in pcf, A in in²
  w_D  ← w_D + w_sw
  ```

  Densities: for sawn lumber the repo publishes
  `approximate_weight_lbft_by_density_pcf` at 25/30/35/40/45/50 pcf in the Table 1B seed but
  **no species-specific density** `[REPO GAP #14]`. For glulam, 35 pcf is recoverable from
  `wood_glulam_current_official_public_2026_03_28.json`, record
  `glulam_rosboro_x_beam_2_0e_3p5x11p875`: `weight_plf = 10.1` at `b·d = 3.5 × 11.875`
  → `10.1 × 144 / 41.5625 = 34.99 pcf`. **Default γ = 35 pcf for softwood glulam and 35 pcf
  for DF-L / SP sawn lumber; expose it as an editable input and label it an assumption.**

### 1.4 Slope

All spans are **horizontal projections** and all psf values are **on the horizontal
projection**. Sloped-roof conversion (`q_along_slope × √(1+(rise/run)²)`), and the fact that
snow is defined on the horizontal while roofing dead load is defined on the slope, are the
user's responsibility. The app must print this. Sloped-member axial thrust is out of scope (§8).

---

## 2. Load combinations and the load-duration factor

### 2.1 The combinations (ASCE 7-22 §2.4.1, basic ASD combinations)

Only the gravity-relevant combinations are implemented. `H`, `F`, `T`, `W`, `E`, and `R` (rain)
terms are dropped — see §8.

| # | Combination | ASCE 7-22 §2.4.1 basic comb. |
|---|---|---|
| 1 | `D` | 1 |
| 2 | `D + L` | 2 |
| 3a | `D + Lr` | 3 |
| 3b | `D + S` | 3 |
| 4a | `D + 0.75L + 0.75Lr` | 4 |
| 4b | `D + 0.75L + 0.75S` | 4 |

Enumerate **all six**. Combinations that reduce to a duplicate (e.g. `D + L` when `q_L = 0`)
are still evaluated; §2.3 handles their `C_D` correctly and the enveloping in §6 discards the
non-governing one on its merits, not by a special case.

### 2.2 `C_D`, load duration factor — NDS Table 2.3.2

| Load duration | `C_D` | Typical design load |
|---|---|---|
| Permanent | **0.9** | Dead load `D` |
| Ten years | **1.0** | Occupancy live load `L` |
| Two months | **1.15** | Snow load `S` |
| Seven days | **1.25** | Construction / roof live load `Lr` |
| Ten minutes | **1.6** | Wind `W` or seismic `E` |
| Impact | **2.0** | Impact |

`[REPO GAP #3]` — Table 2.3.2 is not in the material repo. Hard-code it as a constant table
in the app with the citation.

**Applicability limits on `C_D` (NDS 2.3.2):**
- `C_D` **does not apply** to `E`, `E_min`, or `F_c⊥`. It applies to `F_b`, `F_t`, `F_v`, `F_c`.
- `C_D = 1.6` is the cap for the members in this spec; the 2.0 impact value shall not be applied
  to structural composite lumber or to connections.
- `C_D` is **not** applied in the deflection check (§5.5) — deflection uses `E'`, and `C_D`
  never touches `E`.

### 2.3 The shortest-duration rule (this is the rule implementers get wrong)

> **`C_D` for a load combination is the factor corresponding to the SHORTEST-duration load
> present in that combination**, and it is applied to the **entire** combination — not
> load-by-load. (NDS 2.3.2 and NDS Appendix B.)

Operationally:

```
duration_rank = { D: 0.9, L: 1.0, S: 1.15, Lr: 1.25, W: 1.6, E: 1.6 }

C_D(combination) = max( duration_rank[t] for t in terms(combination) if magnitude(t) != 0 )
```

Two consequences the implementation must honor:

1. **Zero-magnitude terms do not set `C_D`.** If `q_L = 0`, combination `D + L` is numerically
   `D` alone and its `C_D` is **0.9**, not 1.0. Testing `if term in combination` instead of
   `if magnitude(term) > 0` produces an unconservative 11% capacity error on the dead-only case.
2. `max()` is correct because the tabulated `C_D` increases monotonically as duration shortens.

Resulting factors for the six combinations (assuming all listed loads nonzero):

| # | Combination | `C_D` | Set by |
|---|---|---|---|
| 1 | `D` | 0.90 | `D`, permanent |
| 2 | `D + L` | 1.00 | `L`, ten years |
| 3a | `D + Lr` | 1.25 | `Lr`, seven days |
| 3b | `D + S` | 1.15 | `S`, two months |
| 4a | `D + 0.75L + 0.75Lr` | 1.25 | `Lr`, seven days |
| 4b | `D + 0.75L + 0.75S` | 1.15 | `S`, two months |

### 2.4 Enveloping requirement

> The check **must** be run for every enumerated combination, and the app **must** report which
> combination governs, per limit state and overall.

**Do not shortcut this by ranking `w / C_D`.** That heuristic is only valid when the capacity
is strictly linear in `C_D`. It is **not** valid whenever `C_L` (§4.4) or `C_P` (§4.10) is
active, because `C_L` is a nonlinear function of `F_b*`, which itself contains `C_D`. Compute
each combination's DCR explicitly. This is cheap (six evaluations) and correct.

The `[REPO GAP #13]` note: ASCE 7 load combinations are not in the material repo (it is a
material catalog, not a loads library). Hard-code with citation.

---

## 3. Demands

For each combination, form the total uniform load `w_comb` (plf) by summing the factored
line loads from §1.2 with the ASCE coefficients from §2.1 (`1.0` or `0.75`).

### 3.1 Maximum moment

Simple span, uniform load, maximum at midspan:

```
M_ftlb = w_comb · L² / 8                       [ft-lb],  w in plf, L in ft
M      = 12 · M_ftlb = 1.5 · w_comb · L²       [in-lb]
f_b    = M / S                                 [psi]
```

### 3.2 Shear

Maximum shear at the face of support:

```
R = V_support = w_comb · L / 2                 [lb]
```

**NDS §3.4.3.1 — reduction to shear at distance `d` from the support.**

NDS 3.4.3.1(a): *for beams supported by full bearing on one surface and with loads applied to
the opposite surface, uniformly distributed loads within a distance `d` from the face of
supports shall be permitted to be ignored.* NDS 3.4.3.1(b) gives the companion `x/d` reduction
for concentrated loads within `d` (not used here — uniform load only).

Design shear when the reduction is permitted:

```
V_design = w_comb · ( L/2 − d/12 )             [lb],  d in inches
```

**Permitted only when ALL of the following hold. The app exposes this as an explicit checkbox,
defaulted OFF, and prints the conditions:**

1. The member is supported by **full bearing on one surface** (bottom bearing on a plate, sill,
   beam, or wall), and
2. The loads are applied to the **opposite surface** (top-loaded), and
3. The load in question is **uniformly distributed**, and
4. The member is **not notched** at the support (NDS §3.4.3.2 governs notched members and is
   out of scope, §8).

**Not permitted** when the member is hung from a face-mount hanger, top-mount hanger, or
saddle; when it is supported at its top; or when load is applied to the bottom face (e.g., a
suspended load). In those cases use `V_design = V_support`.

If `L/2 − d/12 ≤ 0` (absurdly short span), fall back to `V_design = V_support`.

### 3.3 Shear stress, rectangular section

```
f_v = 1.5 · V_design / A                       [psi]
```

(the `3V/2A` maximum of the parabolic shear distribution in a solid rectangle).

### 3.4 Bearing

```
f_c⊥ = R / (b · l_b)                           [psi]
```

where `l_b` is the bearing length **parallel to the grain of the supported member**, in inches,
and `R` is the **unreduced** support reaction `w_comb·L/2`. The §3.4.3.1 `d`-reduction applies to
shear only and must **never** be applied to the bearing reaction.

### 3.5 Deflection

```
Δ = 5 · w_in · L_in⁴ / (384 · E' · I)          [in]
  = 22.5 · w_defl · L⁴ / (E' · I)              [in],  w in plf, L in ft
```

`E'` per §5.6. Shear deformation is neglected in this formula; for sawn lumber the tabulated
`E` is an apparent modulus that already embeds it, and for glulam the app **must** use
`Ex_app` (not `Ex_true`) for the same reason — see §5.5.

The load set `w_defl` for the deflection check is **not** a strength combination; see §5.5.

---

## 4. Adjustment factors

### 4.1 `C_D` — load duration factor (NDS Table 2.3.2)

See §2.2 / §2.3. `[REPO GAP #3]`

### 4.2 `C_M` — wet service factor

**Trigger (sawn lumber, NDS-S Table 4A footnote / NDS 4.1.4):** apply `C_M` when the
in-service **moisture content exceeds 19%** for an extended period of time. Reference values in
Tables 4A–4F are tabulated for dry service (MC ≤ 19%). Below the trigger, all `C_M = 1.0`.

**Sawn dimension lumber multipliers (NDS-S Table 4A, "Adjustment Factors" block):**

| Design value | `C_M` | Exception |
|---|---|---|
| `F_b` | **0.85** | `C_M = 1.0` when `F_b · C_F ≤ 1150 psi` |
| `F_t` | **1.0** | — |
| `F_v` | **0.97** | — |
| `F_c⊥` | **0.67** | — |
| `F_c` | **0.80** | `C_M = 1.0` when `F_c · C_F ≤ 750 psi` |
| `E` | **0.90** | — |
| `E_min` | **0.90** | — |

*Grounding:* these seven multipliers, and both threshold exceptions, are recoverable from the
repo at `wood_sawn_member_database_phase1_nds2024_v1_2_wet_pressure_treated.json`,
`derivation.wet_service_factors_used` and `derivation.cm_threshold_basis` — e.g. record
`wood_sawn_2x10_douglas_fir_larch_1_wet_pt` carries
`{Fb:1, Ft:1, Fv:0.97, Fc_perp:0.67, Fc:0.8, E:0.9, Emin:0.9}` with
`fb_times_cf_for_cm_check: 1100`, `cm_fb_exception_applied: true`. They are **not** published
in the repo as a standalone `C_M` table `[REPO GAP #5]`.

**Note the ordering trap:** the `F_b` and `F_c` exceptions are evaluated on `F_b·C_F`
(reference value × size factor), *before* any other factor. Compute `C_F` first, then test the
threshold, then select `C_M`.

**Glulam multipliers (NDS-S Table 5A "Adjustment Factors" / NDS 5.1.4). Trigger: MC ≥ 16%:**

| Design value | `C_M` |
|---|---|
| `F_b` (`F_bx`, `F_by`) | **0.80** |
| `F_t` | **0.80** |
| `F_v` (`F_vx`, `F_vy`) | **0.875** |
| `F_c⊥` | **0.53** |
| `F_c` | **0.73** |
| `E`, `E_min` | **0.833** |

*Grounding:* identical values appear in the repo as manufacturer wet-use factors in
`wood_glulam_current_official_public_2026_03_28.json` → `shared_design_adjustments`
(Boise PR-L313, Rosboro PR-L251, SmartLam PR-L326, WFP PR-L269 all publish
`{Fbx:0.8, Fc_perpendicular_x:0.53, Fvx:0.875, Ex:0.833, Ft:0.8, Fc_parallel:0.73}`). There is
no NDS-keyed `C_M` record for glulam `[REPO GAP #11]`.

### 4.3 `C_t` — temperature factor (NDS Table 2.3.3)

Applies when the member will experience **sustained** exposure to elevated temperature.
`T` is the sustained in-service temperature.

| Design values | In-service moisture | `T ≤ 100°F` | `100°F < T ≤ 125°F` | `125°F < T ≤ 150°F` |
|---|---|---|---|---|
| `F_t`, `E`, `E_min` | Wet or dry | 1.0 | **0.9** | **0.9** |
| `F_b`, `F_v`, `F_c`, `F_c⊥` | Dry | 1.0 | **0.8** | **0.7** |
| `F_b`, `F_v`, `F_c`, `F_c⊥` | Wet | 1.0 | **0.7** | **0.5** |

Default for all normal building interiors and roofs: `C_t = 1.0`. `[REPO GAP #4]`

### 4.4 `C_L` — beam stability factor (NDS §3.3.3) — full derivation

**Step 0 — the `C_L = 1.0` conditions.** `C_L = 1.0` if **any** of:

- `d ≤ b` (depth does not exceed breadth) — NDS 3.3.3.1; or
- The **compression edge** of the member is **supported throughout its length** to prevent
  lateral displacement, **and** the ends at points of bearing have lateral support to prevent
  rotation — NDS 3.3.3.1. For a gravity-loaded simple span this is the top edge; continuous
  structural sheathing nailed to the top edge plus blocking/rim at the bearings satisfies it.
- (The alternative NDS 4.4.1 depth-to-breadth bracing rules for sawn lumber may also be
  invoked; the app implements only the two conditions above and offers `C_L = 1.0` as an
  explicit user assertion with the text of NDS 3.3.3.1 shown.)

**Step 1 — unbraced length `l_u`.** `l_u` is the distance between points of lateral support of
the **compression edge**, in inches. If the compression edge is unbraced between bearings,
`l_u = L_in`.

**Step 2 — effective length `l_e` (NDS Table 3.3.3).** The rows below are the ones reachable
from this spec's scope (single span, uniformly distributed load) plus the neighboring cases the
UI may offer. `l_u/d` selects the band.

| Loading / support condition | `l_u/d < 7` | `7 ≤ l_u/d ≤ 14.3` | `l_u/d > 14.3` |
|---|---|---|---|
| Single span, uniformly distributed load | `2.06·l_u` | `1.63·l_u + 3d` | `1.84·l_u` |
| Single span, concentrated load at center, no intermediate lateral support | `1.80·l_u` | `1.37·l_u + 3d` | `1.84·l_u` |
| Single span, concentrated load at center, lateral support at center | `1.11·l_u` | `1.11·l_u` | `1.11·l_u` |
| Single span, two equal concentrated loads at 1/3 points, lateral support at 1/3 points | `1.68·l_u` | `1.68·l_u` | `1.68·l_u` |
| Single span, three equal concentrated loads at 1/4 points, lateral support at 1/4 points | `1.54·l_u` | `1.54·l_u` | `1.54·l_u` |
| Any other single-span or cantilever condition | `2.06·l_u` | `1.63·l_u + 3d` | `1.84·l_u` |

Cantilever rows exist in Table 3.3.3 (`1.33·l_u` / `0.90·l_u + 3d` / `1.06·l_u` for uniform
load; `1.87·l_u` / `1.44·l_u + 3d` / `1.61·l_u` for a concentrated end load) but cantilevers
are **out of scope** (§8) and must not be selectable.

**Step 3 — slenderness ratio (NDS 3.3.3.6):**

```
R_B = sqrt( l_e · d / b² )
```

`R_B` **shall not exceed 50** (NDS 3.3.3.7). If `R_B > 50`, the app must **hard-fail** the
member with the message *"R_B = <value> exceeds the NDS 3.3.3.7 limit of 50; the member is not
permitted at this unbraced length. Add lateral bracing or increase b."* Do not compute a `C_L`
from an out-of-range `R_B`.

**Step 4 — critical buckling design value (NDS 3.3.3.8):**

```
F_bE = 1.20 · E_min' / R_B²
```

`E_min'` per §5.6. **For glulam bending about the x-x axis, `E_min'` in this equation is built
from `E_y min`** (the weak-axis value that governs lateral-torsional buckling), not `E_x min`.
NDS-S Table 5A publishes both (`ex_min` and `ey_min`). *(Clause number to verify — the rule is
stated in NDS §3.3.3 for glued laminated timber; I am confident of the rule, not of the
sub-clause number in the 2024 edition.)* For sawn lumber there is a single `E_min`.

**Step 5 — `F_b*`.** `F_b*` = the reference bending design value multiplied by **all**
applicable adjustment factors **except** `C_fu`, `C_V`, and `C_L`:

```
sawn:   F_b* = F_b · C_D · C_M · C_t · C_F · C_i · C_r
glulam: F_b* = F_b · C_D · C_M · C_t · C_c · C_I
```

Note `C_r` **is** inside `F_b*` for sawn lumber.

**Step 6 — the three-term Ylinen-form equation (NDS Eq. 3.3-6):**

Let `α = F_bE / F_b*`. Then

```
        1 + α        ┌  ( 1 + α )²      α   ┐^(1/2)
C_L =  -------  −    │  ( ----- )   −  ---- │
         1.9         └  (  1.9  )      0.95 ┘
```

i.e. `C_L = (1+α)/1.9 − sqrt( ((1+α)/1.9)² − α/0.95 )`.

The radicand is non-negative for all `α ≥ 0`; if floating-point noise makes it slightly
negative, clamp to 0. `C_L → 1.0` as `α → ∞` and `C_L → α` as `α → 0`. Assert `0 < C_L ≤ 1.0`.

**Glulam only — `C_L` and `C_V` are alternatives, not cumulative.** NDS §5.3.6: for glulam
bending members, the **lesser** of `C_L` and `C_V` shall apply — never their product.

### 4.5 `C_F` — size factor (NDS-S Table 4A, "Size Factor" block)

**Applies to `F_b`, `F_t`, and `F_c`** of **visually graded dimension lumber** (2"–4" nominal
thickness) in Tables 4A and 4F. It does **not** apply to `F_v`, `F_c⊥`, `E`, or `E_min`.

`C_F` varies with **nominal width (depth in bending)**, **nominal thickness**, and **grade**.

**Grades Select Structural, No. 1 & Btr, No. 1, No. 2, No. 3:**

| Nominal width | `C_F` for `F_b`, 2"&3" thick | `C_F` for `F_b`, 4" thick | `C_F` for `F_t` | `C_F` for `F_c` |
|---|---|---|---|---|
| 2", 3" | 1.5 | 1.5 | 1.5 | 1.15 |
| 4" | 1.5 | 1.5 | 1.5 | 1.15 |
| 5" | 1.4 | 1.4 | 1.4 | 1.1 |
| 6" | 1.3 | 1.3 | 1.3 | 1.1 |
| 8" | 1.2 | 1.3 | 1.2 | 1.05 |
| 10" | 1.1 | 1.2 | 1.1 | 1.0 |
| 12" | 1.0 | 1.1 | 1.0 | 1.0 |
| 14" and wider | 0.9 | 1.0 | 0.9 | 0.9 |

**Stud grade:** 2", 3", 4" wide → `F_b` 1.1, `F_t` 1.1, `F_c` 1.05. 5", 6" wide → 1.0 / 1.0 / 1.0.
Over 6" wide, Stud grade must use **No. 3** tabulated values and No. 3 size factors.

**Construction, Standard grades** (2"–4" wide only): `C_F = 1.0` for all of `F_b`, `F_t`, `F_c`.
**Utility grade:** 4" wide → 1.0 / 1.0 / 1.0; 2" and 3" wide → `F_b` 0.4, `F_t` 0.4, `F_c` 0.6.

*Grounding:* the 2"-thick column of the SS/#1/#2/#3/Stud rows for 2x4 through 2x12 is
independently confirmed in the repo at
`wood_sawn_member_database_phase1_nds2024_v1_2_wet_pressure_treated.json`,
`derivation.cm_threshold_basis.size_factor_for_cm_threshold` —
2x4 `{1.5,1.5,1.15}`, 2x6 `{1.3,1.3,1.1}`, 2x8 `{1.2,1.2,1.05}`, 2x10 `{1.1,1.1,1.0}`,
2x12 `{1.0,1.0,1.0}`, and Stud 2x4 `{1.1,1.1,1.05}`, Stud 2x6 `{1.0,1.0,1.0}`.
The **4"-thick column, the 14"-and-wider row, and the Construction/Standard/Utility rows are
NOT in the repo** and must be transcribed from NDS-S Table 4A `[REPO GAP #1]`.

**Exclusions — three of them, and all three matter:**

1. **Southern Pine and Mixed Southern Pine (NDS-S Table 4B): `C_F = 1.0`, always.** Table 4B
   values are tabulated **per nominal width**, so the size effect is already inside the
   published value. The repo makes this machine-checkable: Table 4B records carry
   `"size_factor_applied": true` while Table 4A records carry
   `"size_factor_applied": false`. **The app must key off that flag, not off a species-name
   string match.** Applying `C_F` on top of a Table 4B value overstates capacity by up to 50%.
2. **Timbers, 5"×5" and larger (NDS-S Table 4D).** Do not use the Table 4A `C_F`. For
   **Beams and Stringers** and **Posts and Timbers** with depth `d > 12 in`, NDS §4.3.6 gives

   ```
   C_F = (12/d)^(1/9)   ≤ 1.0
   ```

   For `d ≤ 12 in`, `C_F = 1.0`. Table 4D data is in the repo
   (`wood_sawn_timbers_nds2024_table_4d.json`, 239 records, `size_factor_applied: false`); the
   formula is not `[REPO GAP #16]`.
3. **Glulam:** `C_F` does not exist. Glulam uses the volume factor `C_V` (§4.9).

### 4.6 `C_fu` — flat use factor (NDS-S Table 4A, "Flat Use Factor" block)

**Applies to `F_b` only, and only when the member is loaded on its WIDE face** (bending about
the y-y / weak axis of the tabulated orientation). Dimension lumber 2"–4" thick.

For every member in this spec's primary scope — a joist, rafter, header, or beam loaded on its
narrow edge — **`C_fu = 1.0`**. The app should set `C_fu = 1.0` and gray it out unless the user
selects a flatwise orientation (e.g., plank decking, a flat 2x laid on its face).

Tabulated values (NDS-S Table 4A):

| Nominal width | 2" & 3" thick | 4" thick |
|---|---|---|
| 2", 3" | 1.0 | — |
| 4" | 1.1 | 1.0 |
| 5" | 1.1 | 1.05 |
| 6" | 1.15 | 1.05 |
| 8" | 1.15 | 1.05 |
| 10" and wider | 1.2 | 1.1 |

`[REPO GAP #2]` — not in the repo; transcribe from Table 4A and **verify against the printed
table before release** (this is the one factor table above that I could not cross-check against
any repo record).

Glulam has its own flat-use provision: for bending about y-y with `d < 12 in`,
`C_fu = (12/d)^(1/9)` with `d = 3 in` used when `d < 3 in`. The repo confirms this wording in
`wood_glulam_current_official_public_2026_03_28.json` → `shared_design_adjustments` →
`Fby_depth_factor` (Rosboro, WFP, SmartLam entries).

### 4.7 `C_r` — repetitive member factor (NDS §4.3.9)

```
C_r = 1.15
```

**Applies to `F_b` only.** Applies to **no other design value** — not `F_v`, not `E`, not
`F_c⊥`.

**ALL FOUR qualifying conditions must be satisfied (NDS 4.3.9):**

1. The members are **dimension lumber, 2" to 4" nominal thickness**; and
2. There are **three or more** such members acting together; and
3. They are **spaced not more than 24 inches on center**; and
4. They are **joined by floor, roof, or other load-distributing elements** adequate to support
   the design load (sheathing, decking, subfloor, or bridging/blocking that distributes load
   between members).

If any one fails, `C_r = 1.0`. Notably: a single header, a doubled/tripled beam acting as one
built-up member at a discrete location, a glulam, an LVL, and any timber ≥ 5" thick all get
`C_r = 1.0`. Two joists side by side do not qualify (needs three).

The app must present these as four checkboxes, all of which must be checked, and must default
`C_r = 1.0` for any member typed as "beam", "header", "girder", or "ridge beam".

`[REPO GAP #7]` — not in the repo.

### 4.8 `C_i` — incising factor (NDS Table 4.3.8)

Applies to **dimension lumber that has been incised parallel to grain** to increase
preservative penetration. Table 4.3.8 values are valid for incisions to a maximum depth of
0.4 in, a maximum length of 3/8 in, and a density of up to approximately 1100 incisions per ft².

| Design value | `C_i` |
|---|---|
| `E`, `E_min` | **0.95** |
| `F_b`, `F_t`, `F_v`, `F_c` | **0.80** |
| `F_c⊥` | **1.00** |

*Grounding:* exactly these values are in the repo at
`wood_sawn_member_database_phase1_nds2024_v1_2_wet_pressure_treated.json`,
`derivation.incising_factors_used` (e.g. `wood_sawn_2x10_douglas_fir_larch_1_wet_pt`:
`{Fb:0.8, Ft:0.8, Fv:0.8, Fc_perp:1, Fc:0.8, E:0.95, Emin:0.95}`). Not published as a
standalone table `[REPO GAP #6]`.

Default `C_i = 1.0`. Pressure treatment alone does **not** trigger `C_i` — only physical
incising does. The repo's seed notes are explicit and worth reproducing in the UI:
*"Reference design values for untreated lumber also apply to lumber pressure treated by an
approved process and preservative"*; DF-L, Hem-Fir and SPF are commonly incised, Southern Pine
generally is not. Glulam is never incised in this sense; `C_i` does not exist for glulam.

### 4.9 `C_V` — volume factor, glulam only (NDS §5.3.6)

```
C_V = (21/L_ft)^(1/x) · (12/d)^(1/x) · (5.125/b)^(1/x)   ≤ 1.0
```

- `L_ft` = length of the beam **between points of zero moment**, in feet (for a simple span
  under uniform load this is the full span `L`).
- `d` = depth in inches; `b` = width in inches. **If `b > 10.75 in`, use `b = 10.75 in`.**
- `x = 20` for **Southern Pine**; `x = 10` for **all other species**.
- Cap at 1.0.

`C_V` applies to `F_b` only, and per §5.3.6 the **lesser of `C_L` and `C_V`** is applied — never
both.

*Grounding:* the exponent split is in the repo as
`volume_factor_exponents: {"Douglas fir-Larch": 0.1, "Southern Pine": 0.05}` (note: published
as `1/x`) in `wood_glulam_current_official_public_2026_03_28.json` → `shared_design_adjustments`
(SmartLam PR-L326), and as `volume_factor_exponent: 0.1` for Rosboro/WFP, `0.05` for Anthony SP.

`[REPO GAP #9]` — **NDS-S Table 5A stress classes do not carry a species tag.** The repo record
`glulam_5a:24f_1_8e` has no species field, and the 24F-1.8E stress class is manufactured in both
DF/DF and SP layups. The app therefore **cannot infer `x` from the stress class**; it must
require the user to declare the species (or select a combination symbol from
`wood_glulam_bending_combination_reference_design_values_nds2024_table_5a_expanded.json`, whose
56 records **are** keyed `(combination_symbol, species)` — e.g. `glulam_5aexp:16f_v3:df_df`).
Getting `x` wrong swings `C_V` in the wrong direction and is silently unconservative for SP.

### 4.10 `C_P` — column stability factor (NDS §3.7.1)

Included for the combined-bending-and-axial and pure-compression cases. Not exercised by the
pure-bending member in §7, but specified here because the applicability matrix requires it.

```
F_cE = 0.822 · E_min' / (l_e/d)²

F_c* = F_c · (all applicable factors except C_P)
     = F_c · C_D · C_M · C_t · C_F · C_i          (sawn)
     = F_c · C_D · C_M · C_t                      (glulam)

β = F_cE / F_c*

           1 + β        ┌  ( 1 + β )²      β  ┐^(1/2)
C_P  =    -------   −   │  ( ----- )   −  --- │
            2c          └  (  2c   )       c  ┘
```

`c` values (NDS 3.7.1):

| Member type | `c` |
|---|---|
| Sawn lumber | **0.8** |
| Round timber poles and piles | **0.85** |
| Structural glued laminated timber, structural composite lumber, cross-laminated timber | **0.9** |

`l_e/d` is evaluated about **both** principal axes and the **larger** ratio governs.
`l_e/d ≤ 50` (NDS 3.7.1.4), except `l_e/d ≤ 75` is permitted during construction.
`l_e = K_e · l` with `K_e` from NDS Appendix G.

### 4.11 `C_b` — bearing area factor (NDS §3.10.4)

See §5.4.

### 4.12 `C_T` — buckling stiffness factor (NDS §4.4.2)

Applies to `E_min` **only**, and only for **2×4 or smaller** sawn-lumber **truss compression
chords** sheathed on the narrow face with 3/8" or thicker wood structural panels, dry service.
For every member in this spec, **`C_T = 1.0`**. It is carried in the `E_min'` definition (§5.6)
for completeness.

### 4.13 Glulam-only factors carried but defaulted

| Factor | NDS clause | Meaning | Default here |
|---|---|---|---|
| `C_c` | §5.3.8 | Curvature factor, curved glulam | 1.0 (prismatic straight member) |
| `C_I` | §5.3.9 *(clause number to verify)* | Stress interaction factor, tapered glulam | 1.0 (prismatic) |
| `C_vr` | §5.3.10 *(clause number to verify)* | Shear reduction factor = **0.72** for non-prismatic members, members with connections that induce tension perpendicular to grain, and members subject to impact or cyclic loading | 1.0 (none of these apply) |

*Grounding for `C_vr = 0.72`:* the repo carries
`non_prismatic_or_connection_shear_factor: 0.72` in
`wood_glulam_current_official_public_2026_03_28.json` → `shared_design_adjustments` (Rosboro,
WFP, SmartLam).

---

### 4.14 Applicability matrix — NDS Table 4.3.1 (sawn lumber, ASD)

Rows = design value. Columns = factor. **Y** = the factor multiplies that design value.
**—** = it does not.

| | `C_D` | `C_M` | `C_t` | `C_L` | `C_F` | `C_fu` | `C_i` | `C_r` | `C_P` | `C_T` | `C_b` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **`F_b`** | Y | Y | Y | Y | Y | Y | Y | Y | — | — | — |
| **`F_t`** | Y | Y | Y | — | Y | — | Y | — | — | — | — |
| **`F_v`** | Y | Y | Y | — | — | — | Y | — | — | — | — |
| **`F_c⊥`** | — | Y | Y | — | — | — | Y | — | — | — | Y |
| **`F_c`** | Y | Y | Y | — | Y | — | Y | — | Y | — | — |
| **`E`** | — | Y | Y | — | — | — | Y | — | — | — | — |
| **`E_min`** | — | Y | Y | — | — | — | Y | — | — | Y | — |

Written out:

```
F_b'    = F_b    · C_D · C_M · C_t · C_L · C_F · C_fu · C_i · C_r
F_t'    = F_t    · C_D · C_M · C_t · C_F · C_i
F_v'    = F_v    · C_D · C_M · C_t · C_i
F_c⊥'   = F_c⊥   ·       C_M · C_t · C_i · C_b
F_c'    = F_c    · C_D · C_M · C_t · C_F · C_i · C_P
E'      = E      ·       C_M · C_t · C_i
E_min'  = E_min  ·       C_M · C_t · C_i · C_T
```

Three things to notice, because they are the usual bugs:
- **`C_D` never touches `F_c⊥`, `E`, or `E_min`.**
- **`C_F` never touches `F_v`, `F_c⊥`, `E`, or `E_min`.**
- **`C_r` touches `F_b` and nothing else.**

### 4.15 Applicability matrix — NDS Table 5.3.1 (structural glued laminated timber, ASD)

| | `C_D` | `C_M` | `C_t` | `C_L` | `C_V` | `C_fu` | `C_c` | `C_I` | `C_vr` | `C_P` | `C_b` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **`F_b`** | Y | Y | Y | Y¹ | Y¹ | Y | Y | Y | — | — | — |
| **`F_t`** | Y | Y | Y | — | — | — | — | — | — | — | — |
| **`F_v`** | Y | Y | Y | — | — | — | — | — | Y | — | — |
| **`F_c⊥`** | — | Y | Y | — | — | — | — | — | — | — | Y |
| **`F_c`** | Y | Y | Y | — | — | — | — | — | — | Y | — |
| **`E`** | — | Y | Y | — | — | — | — | — | — | — | — |
| **`E_min`** | — | Y | Y | — | — | — | — | — | — | — | — |

¹ **The lesser of `C_L` and `C_V` applies — not both** (NDS §5.3.6).

Note the differences from sawn lumber: no `C_F`, no `C_r`, no `C_i`, no `C_T`; new `C_V`,
`C_c`, `C_I`, `C_vr`.

---

## 5. Capacities and demand-capacity ratios

### 5.1 Bending

```
F_b' = F_b · C_D · C_M · C_t · C_L · C_F · C_fu · C_i · C_r        (sawn)
F_b' = F_b · C_D · C_M · C_t · min(C_L, C_V) · C_fu · C_c · C_I    (glulam)

DCR_b = f_b / F_b'
```

For glulam, use `F_bx+` when the tension side is the tension-lamination face (the normal
orientation for a simple-span beam with the stamped "TOP" up) and `F_bx−` when the beam is
inverted or when negative moment puts the compression lamination in tension. This spec's scope
is positive moment only → **`F_bx+`**, and the app must print the "TOP" orientation requirement.

### 5.2 Shear

```
F_v' = F_v · C_D · C_M · C_t · C_i          (sawn)
F_v' = F_v · C_D · C_M · C_t · C_vr         (glulam)

f_v   = 1.5 · V_design / A
DCR_v = f_v / F_v'
```

### 5.3 Bearing (compression perpendicular to grain)

```
F_c⊥' = F_c⊥ · C_M · C_t · C_i · C_b        (sawn; drop C_i for glulam)

f_c⊥   = R / (b · l_b)
DCR_c⊥ = f_c⊥ / F_c⊥'
```

No `C_D` — bearing capacity is not duration-sensitive.

### 5.4 `C_b`, bearing area factor (NDS §3.10.4)

> `F_c⊥` applies to bearings of **any length at the ends of a member**, and to **all bearings
> 6 in or more in length** at any other location. For bearings **less than 6 in in length and
> not nearer than 3 in to the end of a member**, `F_c⊥` may be multiplied by `C_b`.

```
C_b = (l_b + 0.375) / l_b        [l_b in inches]
```

| `l_b` (in) | 0.5 | 1.0 | 1.5 | 2.0 | 3.0 | 4.0 | 6.0 or more |
|---|---|---|---|---|---|---|---|
| `C_b` | 1.75 | 1.38 | 1.25 | 1.19 | 1.13 | 1.10 | 1.00 |

**Decision rule the app implements:**

```
if bearing_is_at_member_end            -> C_b = 1.0
else if l_b >= 6.0                     -> C_b = 1.0
else if distance_to_nearest_end < 3.0  -> C_b = 1.0
else                                   -> C_b = (l_b + 0.375)/l_b
```

For a **simply-supported single-span member, both bearings are end bearings**, so
**`C_b = 1.0` for every case in this spec's primary scope.** `C_b > 1.0` is reachable only for
an interior bearing (e.g., a beam continuous over the support — out of scope, §8) or a plate
bearing on a member's mid-length. `[REPO GAP #8]`

### 5.5 Deflection — a serviceability ratio, not a stress ratio

> **`DCR_defl = Δ_actual / Δ_allow`.** This is a **serviceability** ratio. It is not a stress
> ratio, it carries no load-duration factor, and it does not participate in the strength
> envelope described in §2.4. Report it in its own row and label it *serviceability*.

**Allowable deflections — IBC Table 1604.3.** The table has **three** load columns:
**`L`** (live load alone), **`S or W`** (snow or wind alone), and **`D + L`** (the total).
`ℓ` is the span. The first two columns are numerically identical on every row this app uses,
which is exactly why they are so often collapsed into one — but the third column is **not**
equal to them on any row, and collapsing the first two and then reprinting them under the
`D + L` heading drops the real total-load column entirely.

| Construction (IBC Table 1604.3 row) | `L` | `S or W` | `D + L` |
|---|---|---|---|
| Roof members supporting **plaster or stucco** ceiling | `ℓ/360` | `ℓ/360` | `ℓ/240` |
| Roof members supporting **nonplaster** ceiling | `ℓ/240` | `ℓ/240` | `ℓ/180` |
| Roof members **not supporting** a ceiling | `ℓ/180` | `ℓ/180` | `ℓ/120` |
| **Floor members** | `ℓ/360` | — | `ℓ/240` |

The floor row has no `S or W` entry: snow and wind do not act on a floor.

**The exact rows this app relies on:**
- **Floor joist / floor beam / floor header:** *"Floor members"* — **`ℓ/360` for `L` alone,
  `ℓ/240` for `D + L`.**
- **Rafter / roof beam / ridge beam with a gypsum (nonplaster) ceiling attached:**
  *"Roof members supporting nonplaster ceiling"* — **`ℓ/240` for `S` or `Lr` alone, `ℓ/180` for
  `D + S`.**
- **Rafter with no ceiling (e.g., open porch, exposed rafters):**
  *"Roof members not supporting ceiling"* — **`ℓ/180` for `S` or `Lr` alone; IBC allows
  `ℓ/120` for `D + S`, but this app uses `ℓ/180` — see the firm overlay below.**

> **Correction to a commonly repeated shorthand.** The shorthand is *"IBC Table 1604.3 has two
> columns, variable and total."* It does not. It has three — `L`, `S or W`, and `D + L` — and
> the error this shorthand produces is always the same one: the two identical variable columns
> get merged, and the merged pair is then reprinted under the `D + L` heading, so the real
> total-load column silently disappears and every total-load limit comes out one step **too
> tight**. On the nonplaster-ceiling row that turns `ℓ/180` into `ℓ/240`; on the
> not-supporting-ceiling row it turns `ℓ/120` into `ℓ/180`.
>
> Tightening a limit is not a safe error. It is still a wrong answer, it fails members that the
> code passes, and — because it looks conservative — nobody checks it. The app must implement
> the table as printed, and state separately and by name any place the firm chooses to be
> tighter. That separation is the point of the product: a number that is conservative by
> **policy** is defensible, and the same number arriving by **transcription error** is not.

> **Firm overlay — `roof_no_ceiling` total load.** The app checks the not-supporting-ceiling
> row at **`ℓ/180`** for `D + S`, where IBC Table 1604.3 permits `ℓ/120`. This is a deliberate
> firm standard, tighter than code, applied because an open-porch or exposed-rafter roof at
> `ℓ/120` is visibly sagging and generates callbacks. It is **not** a transcription of the
> table and must not be "corrected" to `ℓ/120` without a decision from the firm. Every other
> cell in `engine.js`'s `DEFL` map is the table as printed.
>
> **IRC scope note.** The IRC — not the IBC — governs one- and two-family dwellings, and every
> region pack in `weights.js` declares the IRC. **IRC Table R301.7 has no `D + L` column at
> all**: it publishes only the live/snow-alone limits (`ℓ/360` floors, `ℓ/240` and `ℓ/180`
> rafters). So for IRC work the app's entire total-load check — not just the
> `roof_no_ceiling` value — is a firm overlay, not a code requirement. It should be labelled
> that way on the sheet rather than cited to a code section that does not contain it.

**Load sets for the deflection check** (`w_defl` in the §3.5 formula):

```
Δ_variable  from  w_defl = w_L         (floor)
                  w_defl = max(w_Lr, w_S)   (roof)      -> compare to the L / S-or-W limit
Δ_total     from  w_defl = w_D + w_L                    (floor)
                  w_defl = w_D + max(w_Lr, w_S)         (roof)  -> compare to the D + L limit
```

The roof slot is `max(w_Lr, w_S)`, **never the sum**: snow and roof live are alternative
occupancies of the same roof, and adding them designs for a load that cannot occur.

**Members that carry a roof AND a floor** (`weights.js` `carries: "roof+floor"` — a header under
an upper storey, for example) are not named by the floor/roof branch above. Floor live is a
different tributary and *does* coexist with a roof load, so it adds:

```
w_variable = w_L + max(w_Lr, w_S)          general form; reduces to the two branches above
w_total    = w_D + w_L + max(w_Lr, w_S)    when q_L = 0 (roof) or q_Lr = q_S = 0 (floor)
```

This general form is what the engine implements. Taking a blanket `max(w_L, w_Lr, w_S)` instead
would cut the deflection demand on a mixed roof+floor header by about a third — unconservative,
and silently so.

Both are checked; the larger `DCR_defl` is reported.

**Optional IBC creep allowance (default OFF).** IBC Table 1604.3 footnote *(clause/footnote
letter to verify — footnote (d) in the 2018 IBC)* permits, for wood structural members with a
moisture content of less than 16% at time of installation and used under dry conditions, the
`D + L` deflection to be taken as `D/2 + L`. If the user enables it:
`Δ_total = 0.5·Δ_D + Δ_variable`. Print the footnote text when enabled.

**`E'` in the deflection formula:**
- Sawn lumber: `E' = E · C_M · C_t · C_i`, from the NDS-S Table 4A `E` column
  (an **apparent** modulus that already includes shear deformation).
- Glulam: `E' = E_x,app · C_M · C_t`. **Use `ex_app`, not `ex_true`.** The `5wL⁴/384EI` formula
  omits shear deformation; `E_app` restores it. Using `ex_true` understates deflection by
  roughly 5%.

`[REPO GAP #12]` — IBC Table 1604.3 is not in the material repo (it is a building-code table,
not a material catalog). Hard-code with citation.

### 5.6 `E_min'` — where it comes from and where it is used

```
E_min' = E_min · C_M · C_t · C_i · C_T        (sawn)
E_min' = E_min · C_M · C_t                    (glulam)
```

`E_min` is the **reference modulus of elasticity for beam and column stability** — a 5th-
percentile value with a safety-adjustment already applied, published as its own column in
NDS-S Tables 4A–4F and 5A. It is **not** `E`, it is **not** derived from `E` by the app, and
it is **never** used to compute deflection.

`E_min'` is used in exactly two places:

1. `F_bE = 1.20 · E_min' / R_B²` — beam stability, §4.4 Step 4.
2. `F_cE = 0.822 · E_min' / (l_e/d)²` — column stability, §4.10.

Read `E_min` from the repo: `reference_values_psi.Emin` (sawn, Tables 4A/4B/4D) or
`reference_values_psi.ex_min` / `ey_min` (glulam, Table 5A). Never back-compute it.

---

## 6. Governing case selection and display

### 6.1 Algorithm

```
combos = enumerate_gravity_combinations()          # §2.1, six of them
results = []

for cmb in combos:
    w   = total_line_load(cmb)                     # §3
    C_D = shortest_duration_factor(cmb)            # §2.3 — nonzero terms only

    # strength limit states — recompute the FULL factor stack per combination,
    # because C_L and C_P depend nonlinearly on C_D through F_b* / F_c*
    factors = build_factor_stack(member, service, C_D)
    results.append(("bending", cmb, f_b(w)  / Fb_prime(factors)))
    results.append(("shear",   cmb, f_v(w)  / Fv_prime(factors)))
    results.append(("bearing", cmb, f_cperp(w) / Fcperp_prime(factors)))

# serviceability — separate track, no C_D, no strength combinations
results.append(("deflection_variable", "S (or Lr, or L) alone", d_var  / d_allow_col1))
results.append(("deflection_total",    "D + variable",          d_tot  / d_allow_col2))

governing = max(results, key=DCR)
```

### 6.2 Tie-breaking and rounding

- Compare DCRs at **full floating-point precision**. Round only for display (3 decimal places).
- On an exact tie, prefer, in order: bending → shear → bearing → deflection. Deterministic
  output matters more than which one wins.
- Pass/fail threshold: `DCR ≤ 1.000` passes. Do **not** apply a tolerance band; a member at
  1.004 fails and the engineer decides what to do about it.

### 6.3 What the app displays

**Headline block**
- `PASS` / `FAIL`
- Governing **limit state** (bending / shear / bearing / deflection)
- Governing **load combination**, written out with its numbers (e.g. `D + S = 60.0 plf`)
- Governing `C_D` and the load that set it (e.g. `C_D = 1.15 (snow, two-month duration)`)
- Governing `DCR` to three decimals

**Per-limit-state table** — one row per limit state, each showing its **own** governing
combination (they can differ; bearing is often governed by a different combination than bending
because `C_D` does not apply to `F_c⊥`):

| Limit state | Governing combo | `C_D` | Demand | Capacity | DCR | Status |
|---|---|---|---|---|---|---|

**Factor-stack panel** — every factor, its value, the clause it comes from, and *why* it took
that value ("`C_r = 1.15` — dimension lumber, 3+ members, 16 in o.c. ≤ 24 in, sheathed";
"`C_L = 1.00` — compression edge continuously supported per NDS 3.3.3.1"). A factor shown
without a reason is a black box, which is the thing this product exists not to be.

**Full combination envelope** — all six combinations with their DCRs, so the engineer can see
the margin between the governing case and the runners-up.

**Provenance panel** — for every reference design value and section property: the repo file,
the record `id`, the NDS table, and the printed page. E.g.
`F_b = 900 psi — wood_sawn_reference_design_values_nds2024_table_4a.json,
id sawn_4a:douglas_fir_larch:no_2:2in_and_wider, NDS-S Table 4A, p.34`.

**Limitations panel** — §8, verbatim.

---

## 7. Worked examples (regression tests)

All intermediate values below are stated to at least 3 significant figures and are the
**expected outputs** of the implementation. Tolerance for regression: **±0.1%** on every
derived quantity, **±0.001** absolute on every DCR.

---

### 7.1 Example 1 — 2×10 DF-L No. 2 rafter @ 16" o.c.

#### 7.1.1 Inputs

| Input | Value |
|---|---|
| Member | 2×10 sawn dimension lumber, S4S |
| Species / grade | Douglas Fir-Larch, No. 2, visually graded |
| Application | Roof rafter, simple span, horizontal projection |
| Spacing `s` | 16 in o.c. |
| Span `L` | 13.0 ft (horizontal, center of bearing to center of bearing) |
| `q_D` | 15 psf (inclusive of rafter self-weight — repetitive framing rule, §1.3) |
| `q_L` | 0 psf (no floor live load on a rafter) |
| `q_Lr` | 20 psf |
| `q_S` | 30 psf |
| Service condition | Dry, MC ≤ 19% → `C_M = 1.0` |
| Temperature | Normal, `T ≤ 100°F` → `C_t = 1.0` |
| Incising | None → `C_i = 1.0` |
| Lateral support | Structural sheathing nailed continuously to the top (compression) edge; blocking at both bearings → NDS 3.3.3.1 satisfied → `C_L = 1.0` |
| Ceiling | Gypsum board applied to underside → IBC "roof members supporting nonplaster ceiling" |
| Bearing length `l_b` | 3.5 in (bearing on a nominal 2×4 top plate), **end bearing** |
| §3.4.3.1 `d`-reduction | Enabled (bottom-bearing on plate, top-loaded, uniform load, unnotched) |

#### 7.1.2 Section properties

Source: `/workspace/firmark/material-databases/data/wood_sawn_section_properties_nds2024_table_1b.json`,
record `id = "sawn_secprop:s4s:2x10"` (NDS-S Table 1B, printed p.14; dressed sizes Table 1A / PS 20).

| Property | Value |
|---|---|
| `b` | 1.5 in |
| `d` | 9.25 in |
| `A` | 13.875 in² |
| `S_x` | 21.390625 in³ |
| `I_x` | 98.931641 in⁴ |

#### 7.1.3 Reference design values

Source: `/workspace/firmark/material-databases/data/wood_sawn_reference_design_values_nds2024_table_4a.json`,
record `id = "sawn_4a:douglas_fir_larch:no_2:2in_and_wider"`
(NDS-S Table 4A, printed p.34; size classification `2" & wider`; `size_factor_applied: false`;
grading agencies WCLIB/WWPA; `specific_gravity: 0.50`).

| Value | psi |
|---|---|
| `F_b` | 900 |
| `F_t` | 575 |
| `F_v` | 180 |
| `F_c⊥` | 625 |
| `F_c` | 1350 |
| `E` | 1,600,000 |
| `E_min` | 580,000 |

#### 7.1.4 Load path (§1)

```
t_w   = 16 / 12                       = 1.333333 ft
w_D   = 15 psf × 1.333333 ft          = 20.0000 plf
w_L   = 0                             = 0.0000 plf
w_Lr  = 20 psf × 1.333333 ft          = 26.6667 plf
w_S   = 30 psf × 1.333333 ft          = 40.0000 plf
```

#### 7.1.5 Load combinations (§2)

| # | Combination | Arithmetic | `w_comb` (plf) | `C_D` | Set by |
|---|---|---|---|---|---|
| 1 | `D` | 20.0 | **20.0000** | **0.90** | `D` (permanent) |
| 2 | `D + L` | 20.0 + 0 | **20.0000** | **0.90** | `L = 0`, so `D` sets it — §2.3 rule 1 |
| 3a | `D + Lr` | 20.0 + 26.6667 | **46.6667** | **1.25** | `Lr` (seven-day) |
| 3b | `D + S` | 20.0 + 40.0 | **60.0000** | **1.15** | `S` (two-month) |
| 4a | `D + 0.75L + 0.75Lr` | 20.0 + 0 + 20.0 | **40.0000** | **1.25** | `Lr` |
| 4b | `D + 0.75L + 0.75S` | 20.0 + 0 + 30.0 | **50.0000** | **1.15** | `S` |

Combination 2 is numerically identical to combination 1 and takes `C_D = 0.90`, not 1.00.

#### 7.1.6 Factor stack for `F_b`

| Factor | Value | Clause | Reason |
|---|---|---|---|
| `C_D` | per combo | Table 2.3.2 | shortest-duration load present |
| `C_M` | 1.00 | Table 4A adj. | dry service, MC ≤ 19% |
| `C_t` | 1.00 | Table 2.3.3 | `T ≤ 100°F` |
| `C_L` | 1.00 | §3.3.3.1 | compression edge continuously supported, ends restrained |
| `C_F` | **1.10** | Table 4A | 2" thick, 10" nominal width, grade No. 2 — repo-confirmed (`size_factor_for_cm_threshold` = 1.1 for 2x10 #2) |
| `C_fu` | 1.00 | Table 4A | loaded on the narrow edge |
| `C_i` | 1.00 | Table 4.3.8 | not incised |
| `C_r` | **1.15** | §4.3.9 | 2" nominal thick ✓, ≥3 members ✓, 16 ≤ 24 in o.c. ✓, sheathing distributes ✓ |

```
F_b' = 900 × C_D × 1.00 × 1.00 × 1.00 × 1.10 × 1.00 × 1.00 × 1.15
     = 1138.50 × C_D          [psi]
```

| Combination | `C_D` | `F_b'` (psi) |
|---|---|---|
| 1, 2 | 0.90 | **1024.65** |
| 3a, 4a | 1.25 | **1423.125** |
| 3b, 4b | 1.15 | **1309.275** |

#### 7.1.7 Bending envelope

`M = 1.5·w·L² = 1.5·w·169` in-lb; `f_b = M / 21.390625`.

| # | Combination | `w` (plf) | `M` (in-lb) | `f_b` (psi) | `C_D` | `F_b'` (psi) | `DCR_b` |
|---|---|---|---|---|---|---|---|
| 1 | `D` | 20.0000 | 5,070.0 | 237.02 | 0.90 | 1024.65 | 0.231 |
| 2 | `D + L` | 20.0000 | 5,070.0 | 237.02 | 0.90 | 1024.65 | 0.231 |
| 3a | `D + Lr` | 46.6667 | 11,830.0 | 553.05 | 1.25 | 1423.125 | 0.389 |
| **3b** | **`D + S`** | **60.0000** | **15,210.0** | **711.06** | **1.15** | **1309.275** | **0.543** |
| 4a | `D + 0.75Lr` | 40.0000 | 10,140.0 | 474.04 | 1.25 | 1423.125 | 0.333 |
| 4b | `D + 0.75S` | 50.0000 | 12,675.0 | 592.55 | 1.15 | 1309.275 | 0.453 |

**Governing bending: `D + S`, `DCR_b = 0.543`** (full precision 0.543094).

Longhand for the governing case:
```
M     = 1.5 × 60.0000 × 13.0²  = 1.5 × 60 × 169     = 15,210.0 in-lb
      ( = 60 × 169 / 8 = 1267.5 ft-lb )
f_b   = 15,210.0 / 21.390625                        = 711.056 psi
F_b'  = 900 × 1.15 × 1.10 × 1.15                    = 1309.275 psi
DCR_b = 711.056 / 1309.275                          = 0.543094  ->  0.543
```

#### 7.1.8 Shear envelope

`F_v' = 180 · C_D` (all other applicable factors = 1.00).
`V_design = w·(L/2 − d/12) = w·(6.5 − 9.25/12) = w × 5.729167` lb.
`f_v = 1.5·V_design / 13.875 = 0.6193694 · w` psi.

| # | Combination | `w` (plf) | `V_design` (lb) | `f_v` (psi) | `F_v'` (psi) | `DCR_v` |
|---|---|---|---|---|---|---|
| 1, 2 | `D` | 20.0000 | 114.583 | 12.387 | 162.00 | 0.076 |
| 3a | `D + Lr` | 46.6667 | 267.361 | 28.904 | 225.00 | 0.128 |
| **3b** | **`D + S`** | **60.0000** | **343.750** | **37.162** | **207.00** | **0.180** |
| 4a | `D + 0.75Lr` | 40.0000 | 229.167 | 24.775 | 225.00 | 0.110 |
| 4b | `D + 0.75S` | 50.0000 | 286.458 | 30.968 | 207.00 | 0.150 |

**Governing shear: `D + S`, `DCR_v = 0.180`** (full precision 0.179527).

*Regression variant — §3.4.3.1 reduction DISABLED:* `V = 60 × 6.5 = 390.0 lb`;
`f_v = 1.5 × 390.0 / 13.875 = 42.162 psi`; `DCR_v = 42.162 / 207.00 = 0.204` (0.203682).

#### 7.1.9 Bearing

`C_D` does not apply, so the governing combination is simply the one with the largest reaction:
`D + S`.

```
R      = w·L/2 = 60.0000 × 13.0 / 2                 = 390.0 lb
A_brg  = b · l_b = 1.5 × 3.5                        = 5.25 in²
f_c⊥   = 390.0 / 5.25                               = 74.286 psi
C_b    = 1.00      (END bearing — §3.10.4, C_b applies only to bearings ≥3 in from a member end)
F_c⊥'  = 625 × 1.00 × 1.00 × 1.00 × 1.00            = 625.00 psi
DCR_c⊥ = 74.286 / 625.00                            = 0.118857  ->  0.119
```

#### 7.1.10 Deflection

```
E'   = 1,600,000 × 1.00 × 1.00 × 1.00               = 1,600,000 psi
I    = 98.931641 in⁴
E'·I = 158,290,625.6  lb-in²
Δ    = 22.5 · w · 13.0⁴ / (E'·I) = 22.5 · w · 28,561 / 158,290,625.6
```

IBC Table 1604.3, row **"Roof members supporting nonplaster ceiling"** → `ℓ/240` in the
`L` and `S or W` columns, **`ℓ/180` in the `D + L` column** (§5.5). `ℓ = 156 in`, so
`Δ_allow = 156/240 = 0.650 in` for the variable-load check and
**`Δ_allow = 156/180 = 0.866667 in`** for the total-load check.

| Check | `w_defl` (plf) | `Δ` (in) | `Δ_allow` (in) | `DCR_defl` |
|---|---|---|---|---|
| Dead alone (reference) | 20.0000 | 0.081195 | — | — |
| `Lr` alone | 26.6667 | 0.108260 | 0.650 | 0.167 |
| **`S` alone (`S or W` col)** | **40.0000** | **0.162391** | **0.650** | **0.250** |
| `D + Lr` | 46.6667 | 0.189456 | 0.866667 | 0.219 |
| **`D + S` (`D + L` col)** | **60.0000** | **0.243586** | **0.866667** | **0.281** |

**Governing deflection: `D + S` total, `DCR_defl = 0.281`** (full precision 0.281061).
The variable-load check at 0.250 is the closer of the two, but the total still governs.

Longhand: `Δ = 22.5 × 60.0000 × 28,561 / 158,290,625.6 = 38,557,350 / 158,290,625.6 = 0.243586 in`.

*Optional IBC creep footnote enabled:* `Δ = 0.5(0.081195) + 0.162391 = 0.202988 in`, against
the `D + L` allowable `0.866667 in` → `DCR = 0.234` (0.234217). Default OFF.

#### 7.1.11 Result

| Limit state | Governing combination | `C_D` | Demand | Capacity | DCR | Status |
|---|---|---|---|---|---|---|
| **Bending** | `D + S` = 60.0 plf | 1.15 | `f_b` = 711.06 psi | `F_b'` = 1309.28 psi | **0.543** | PASS |
| Shear | `D + S` = 60.0 plf | 1.15 | `f_v` = 37.162 psi | `F_v'` = 207.00 psi | 0.180 | PASS |
| Bearing | `D + S` = 60.0 plf | n/a | `f_c⊥` = 74.286 psi | `F_c⊥'` = 625.00 psi | 0.119 | PASS |
| Deflection (`S`) | `S` alone | n/a | Δ = 0.16239 in | 0.650 in (`ℓ/240`) | 0.250 | PASS |
| Deflection (total) | `D + S` | n/a | Δ = 0.24359 in | 0.86667 in (`ℓ/180`) | 0.281 | PASS |

> **GOVERNING: Bending, load combination `D + S` (ASCE 7-22 §2.4.1 comb. 3),
> `C_D = 1.15` (snow, two-month duration). DCR = 0.543. PASS.**

#### 7.1.12 Variant 1b — same rafter with **no** lateral bracing (exercises `C_L`)

Identical inputs except the compression edge is unbraced between bearings (`l_u = L_in = 156 in`).
Governing combination `D + S`.

```
l_u / d   = 156 / 9.25                              = 16.865      -> band l_u/d > 14.3
l_e       = 1.84 · l_u = 1.84 × 156                 = 287.040 in       [Table 3.3.3]
R_B       = sqrt(287.040 × 9.25 / 1.5²)
          = sqrt(2655.12 / 2.25) = sqrt(1180.053)   = 34.3519      (≤ 50 ✓, NDS 3.3.3.7)
E_min'    = 580,000 × 1.00 × 1.00 × 1.00 × 1.00     = 580,000 psi
F_bE      = 1.20 × 580,000 / 1180.053               = 589.804 psi
F_b*      = 900 × 1.15 × 1.00 × 1.00 × 1.10 × 1.00 × 1.15   = 1309.275 psi
α         = 589.804 / 1309.275                      = 0.450481
(1+α)/1.9 = 1.450481 / 1.9                          = 0.763411
          squared                                   = 0.582796
α / 0.95                                            = 0.474191
radicand  = 0.582796 − 0.474191                     = 0.108605
sqrt                                                = 0.329553
C_L       = 0.763411 − 0.329553                     = 0.433857
F_b'      = 1309.275 × 0.433857                     = 568.038 psi
DCR_b     = 711.056 / 568.038                       = 1.251780  ->  1.252
```

> **GOVERNING: Bending, `D + S`, DCR = 1.252. FAIL** — the unbraced rafter is 25% overstressed.
> This variant is the required regression test for the `C_L` path; a bug that leaves `C_L` at
> 1.0 will not be caught by Example 1 alone.

---

### 7.2 Example 2 — 5-1/4 × 11-7/8 24F-1.8E glulam ridge beam

#### 7.2.0 Section-availability flag — read this before using the numbers

> **`[REPO GAP #10 / #17]`** A **5-1/4 in × 11-7/8 in** glulam is **not** a standard NDS-S
> Table 1C section. Western-species glulam is laminated in 1-1/2 in laminations at net widths
> of 3-1/8 / 5-1/8 / 6-3/4 / 8-3/4 in; Southern Pine glulam uses 1-3/8 in laminations at net
> widths of 3 / 5 / 6-3/4 / 8-1/2 in. 11.875 in is not an integer multiple of either lamination
> thickness. 5-1/4 × 11-7/8 is a **proprietary I-joist-depth-compatible** glulam
> (Anthony/Canfor Power Beam and similar), sold to match 11-7/8 in I-joist framing.
>
> The repo confirms the gap directly: searching
> `wood_glulam_current_official_public_2026_03_28.json` for `member_size_properties` records at
> `d = 11.875` returns only **Rosboro X-Beam 2.0E at `b = 3.5` and `b = 5.5`**
> (`glulam_rosboro_x_beam_2_0e_3p5x11p875`, `glulam_rosboro_x_beam_2_0e_5p5x11p875`), both
> published as combination **24F-V4-2.0E TRUE**, not 24F-1.8E. The Anthony Power Beam records
> (`glulam_anthony_pr_l263_power_beam_*`) publish **28F-E1/SP, 28F-E2/SP, 30F-E1/SP** and state
> `"PR-L263 publishes a nominal manufacturing range but no discrete stock-size schedule."`
>
> **Therefore:** this example uses the **generic NDS-S Table 5A 24F-1.8E stress class** applied
> to a user-declared net section of 5.25 × 11.875 in, with geometry computed from first
> principles. That is a legitimate calculation **only if the supplier confirms a 24F-1.8E layup
> at that net section.** The app must print this caveat whenever the selected section is not
> found in a tabulated size source.

#### 7.2.1 Inputs

| Input | Value |
|---|---|
| Member | Structural glued laminated softwood timber, 5.25 in × 11.875 in net |
| Combination | **24F-1.8E** stress class (NDS-S Table 5A) |
| Species declared | **DF/DF** → volume factor exponent `1/x = 0.10` (§4.9) |
| Application | Ridge beam, simple span, supporting rafters both sides |
| Rafter horizontal run each side | 13.0 ft |
| Beam span `L` | 16.0 ft |
| `q_D` | 15 psf (roof framing above; **beam self-weight added separately**, §1.3 case b) |
| `q_L` | 0 psf |
| `q_Lr` | 20 psf |
| `q_S` | 30 psf |
| Service condition | Dry, MC < 16% → `C_M = 1.0` |
| Temperature | Normal → `C_t = 1.0` |
| Lateral support of compression edge | Rafters + ridge blocking at 16 in o.c. → `l_u = 16 in` |
| Orientation | Stamped **TOP** up, positive moment → use `F_bx+` |
| Bearing | End bearing on a post cap, `l_b = 5.25 in`, full 5.25 in width |
| §3.4.3.1 `d`-reduction | Enabled (bottom-bearing on post cap, top-loaded, uniform, unnotched) |
| Ceiling | Gypsum (nonplaster) ceiling attached → IBC `ℓ/240` variable / `ℓ/180` total (§5.5) |

#### 7.2.2 Section properties (computed — see §7.2.0)

```
b = 5.25 in,  d = 11.875 in
d²  = 141.015625 in²,   d³ = 1674.560547 in³
A   = 5.25 × 11.875                                 = 62.343750   in²
S_x = 5.25 × 141.015625 / 6  = 740.332031 / 6       = 123.388672  in³
I_x = 5.25 × 1674.560547 / 12 = 8791.442871 / 12    = 732.620239  in⁴
```

#### 7.2.3 Reference design values

Source: `/workspace/firmark/material-databases/data/wood_glulam_reference_design_values_nds2024_table_5a.json`,
record `id = "glulam_5a:24f_1_8e"` (NDS-S Table 5A, stress-class form, printed p.63;
`combination_kind: "stress_class"`; `source_value_status: "exact_tabulated"`).

| Value | psi |
|---|---|
| `F_bx+` | 2400 |
| `F_bx−` | 1450 |
| `F_c⊥x` | 650 |
| `F_vx` | 265 |
| `E_x,true` | 1,900,000 |
| **`E_x,app`** | **1,800,000** |
| `E_x,min` | 950,000 |
| `F_by` | 1450 |
| `F_c⊥y` | 560 |
| `F_vy` | 230 |
| `E_y,true` | 1,700,000 |
| `E_y,app` | 1,600,000 |
| **`E_y,min`** | **850,000** |
| `F_t` | 1100 |
| `F_c` | 1600 |
| `G` | 0.50 |

Deflection uses `E_x,app = 1,800,000`. Beam stability uses `E_y,min = 850,000` (§4.4 Step 4).

#### 7.2.4 Load path (§1)

```
t_w   = 13.0/2 + 13.0/2                             = 13.0000 ft
w_sw  = 35 pcf × 62.34375 in² / 144 = 2182.03125/144 = 15.1530 plf    (γ = 35 pcf, §1.3)
w_D   = 15 psf × 13.0 ft + 15.1530 = 195.0000 + 15.1530   = 210.1530 plf
w_L   = 0                                           = 0.0000 plf
w_Lr  = 20 psf × 13.0 ft                            = 260.0000 plf
w_S   = 30 psf × 13.0 ft                            = 390.0000 plf
```

The implementation carries `w_D = 210.152995 plf` at full precision; tables below show 3 decimals.

#### 7.2.5 Load combinations

| # | Combination | Arithmetic | `w_comb` (plf) | `C_D` |
|---|---|---|---|---|
| 1 | `D` | 210.153 | **210.153** | 0.90 |
| 2 | `D + L` | 210.153 + 0 | **210.153** | 0.90 |
| 3a | `D + Lr` | 210.153 + 260.000 | **470.153** | 1.25 |
| 3b | `D + S` | 210.153 + 390.000 | **600.153** | 1.15 |
| 4a | `D + 0.75L + 0.75Lr` | 210.153 + 0 + 195.000 | **405.153** | 1.25 |
| 4b | `D + 0.75L + 0.75S` | 210.153 + 0 + 292.500 | **502.653** | 1.15 |

#### 7.2.6 `C_V` and `C_L`

**Volume factor (§4.9), governing combination `L = 16.0 ft`:**
```
C_V = (21/16.0)^0.10 × (12/11.875)^0.10 × (5.125/5.25)^0.10
    = (1.312500)^0.10 × (1.010526)^0.10 × (0.976190)^0.10
    = 1.027566 × 1.001048 × 0.997593
    = 1.026167     ->  exceeds 1.0  ->  C_V = 1.000
```

**Beam stability factor (§4.4), governing combination `C_D = 1.15`:**
```
l_u       = 16.0 in       (rafter/blocking spacing along the compression edge)
l_u / d   = 16.0 / 11.875                           = 1.3474     -> band l_u/d < 7
l_e       = 2.06 · l_u = 2.06 × 16.0                = 32.960 in       [Table 3.3.3]
R_B²      = l_e · d / b² = 32.960 × 11.875 / 27.5625
          = 391.400 / 27.5625                       = 14.200454
R_B       = sqrt(14.200454)                         = 3.768349   (≤ 50 ✓)
E_min'    = E_y,min × C_M × C_t = 850,000 × 1.00 × 1.00 = 850,000 psi
F_bE      = 1.20 × 850,000 / 14.200454              = 71,828.69 psi
F_b*      = 2400 × 1.15 × 1.00 × 1.00               = 2760.00 psi
α         = 71,828.69 / 2760.00                     = 26.024888
(1+α)/1.9 = 27.024888 / 1.9                         = 14.223625
          squared                                   = 202.311521
α / 0.95                                            = 27.394619
radicand  = 202.311521 − 27.394619                  = 174.916902
sqrt                                                = 13.225615
C_L       = 14.223625 − 13.225615                   = 0.998010
```

**§5.3.6 — apply the LESSER of `C_L` and `C_V`:** `min(0.998010, 1.000) = 0.998010`.

#### 7.2.7 Bending envelope

`M = 1.5·w·16.0² = 384·w` in-lb; `f_b = M / 123.388672`.
`F_b' = 2400 · C_D · min(C_L, C_V)`, with `C_L` recomputed for each `C_D` (it is
`C_D`-dependent through `F_b*`).

| # | Combination | `w` (plf) | `M` (in-lb) | `f_b` (psi) | `C_D` | `C_L` | `F_b'` (psi) | `DCR_b` |
|---|---|---|---|---|---|---|---|---|
| 1, 2 | `D` | 210.153 | 80,698.75 | 654.02 | 0.90 | 0.998455 | 2156.66 | 0.303 |
| 3a | `D + Lr` | 470.153 | 180,538.75 | 1463.17 | 1.25 | 0.997830 | 2993.49 | 0.489 |
| **3b** | **`D + S`** | **600.153** | **230,458.75** | **1867.75** | **1.15** | **0.998010** | **2754.51** | **0.678** |
| 4a | `D + 0.75Lr` | 405.153 | 155,578.75 | 1260.88 | 1.25 | 0.997830 | 2993.49 | 0.421 |
| 4b | `D + 0.75S` | 502.653 | 193,018.75 | 1564.31 | 1.15 | 0.998010 | 2754.51 | 0.568 |

**Governing bending: `D + S`, `DCR_b = 0.678`** (full precision 0.678069).

Longhand for the governing case:
```
M     = 1.5 × 600.152995 × 16.0²  = 1.5 × 600.152995 × 256  = 230,458.75 in-lb
      ( = 600.152995 × 256 / 8 = 19,204.90 ft-lb )
f_b   = 230,458.75 / 123.388672                           = 1867.75 psi
F_b'  = 2400 × 1.15 × 1.00 × 1.00 × 0.998010              = 2754.51 psi
DCR_b = 1867.75 / 2754.51                                 = 0.678069  ->  0.678
```

Note the `C_L` column moves with `C_D` — this is exactly the nonlinearity that makes the
`w/C_D` ranking shortcut invalid (§2.4). Here it does not change the winner, but it must not be
assumed to never do so.

#### 7.2.8 Shear envelope

`F_v' = 265 · C_D` (`C_M`, `C_t`, `C_vr` all 1.00).
`V_design = w·(L/2 − d/12) = w·(8.0 − 11.875/12) = w × 7.0104167` lb.
`f_v = 1.5·V_design / 62.34375 = 0.1686714 · w` psi.

| # | Combination | `w` (plf) | `V_design` (lb) | `f_v` (psi) | `F_v'` (psi) | `DCR_v` |
|---|---|---|---|---|---|---|
| 1, 2 | `D` | 210.153 | 1473.26 | 35.447 | 238.50 | 0.149 |
| 3a | `D + Lr` | 470.153 | 3295.97 | 79.301 | 331.25 | 0.239 |
| **3b** | **`D + S`** | **600.153** | **4207.32** | **101.229** | **304.75** | **0.332** |
| 4a | `D + 0.75Lr` | 405.153 | 2840.29 | 68.338 | 331.25 | 0.206 |
| 4b | `D + 0.75S` | 502.653 | 3523.81 | 84.783 | 304.75 | 0.278 |

**Governing shear: `D + S`, `DCR_v = 0.332`** (full precision 0.332170).

Longhand: `V_support = 600.152995 × 16.0/2 = 4801.224 lb`;
`V_design = 600.152995 × 7.0104167 = 4207.323 lb`;
`f_v = 1.5 × 4207.323 / 62.34375 = 101.229 psi`; `F_v' = 265 × 1.15 = 304.75 psi`.

*Regression variant — reduction DISABLED:* `V = 4801.224 lb`,
`f_v = 1.5 × 4801.224 / 62.34375 = 115.518 psi`, `DCR_v = 0.379` (0.379059).

#### 7.2.9 Bearing

Governing combination = largest reaction = `D + S` (no `C_D` on `F_c⊥`).

```
R      = 600.152995 × 16.0 / 2                      = 4801.224 lb
A_brg  = 5.25 × 5.25                                = 27.5625 in²
f_c⊥   = 4801.224 / 27.5625                         = 174.194 psi
C_b    = 1.00      (END bearing, §3.10.4)
F_c⊥'  = 650 × 1.00 × 1.00 × 1.00                   = 650.00 psi
DCR_c⊥ = 174.194 / 650.00                           = 0.267991  ->  0.268
```

Required bearing length check: `l_b,req = R / (b · F_c⊥') = 4801.224 / (5.25 × 650) = 1.407 in`.
Provided 5.25 in ✓.

#### 7.2.10 Deflection

```
E'   = E_x,app × C_M × C_t = 1,800,000 × 1.00 × 1.00 = 1,800,000 psi
I    = 732.620239 in⁴
E'·I = 1,318,716,431   lb-in²
Δ    = 22.5 · w · 16.0⁴ / (E'·I) = 22.5 · w · 65,536 / 1,318,716,431
```

IBC Table 1604.3, row **"Roof members supporting nonplaster ceiling"** → `ℓ/240` in the `L` and
`S or W` columns, **`ℓ/180` in the `D + L` column** (§5.5). `ℓ = 192 in`, so
`Δ_allow = 192/240 = 0.800 in` variable and **`192/180 = 1.066667 in`** total.

| Check | `w_defl` (plf) | `Δ` (in) | `Δ_allow` (in) | `DCR_defl` |
|---|---|---|---|---|
| Dead alone (reference) | 210.153 | 0.234989 | — | — |
| `Lr` alone | 260.000 | 0.290726 | 0.800 | 0.363 |
| **`S` alone (`S or W` col)** | **390.000** | **0.436090** | **0.800** | **0.545** |
| `D + Lr` | 470.153 | 0.525715 | 1.066667 | 0.493 |
| **`D + S` (`D + L` col)** | **600.153** | **0.671078** | **1.066667** | **0.629** |

Longhand: `Δ = 22.5 × 600.152995 × 65,536 / 1,318,716,431 = 884,961,600 / 1,318,716,431 = 0.671078 in`.

*Optional IBC creep footnote enabled:* `Δ = 0.5(0.234989) + 0.436090 = 0.553584 in`, against
the `D + L` allowable `1.066667 in` → `DCR = 0.519` (0.518985). Default OFF.

> **⚠ THIS EXAMPLE NO LONGER DEMONSTRATES WHAT IT WAS WRITTEN TO DEMONSTRATE — DO NOT
> RE-BASELINE IT.**
>
> The old numbers checked the **total-load** deflection against the **variable-load** limit
> (`ℓ/240` in both columns), which is the §5.5 error. At the correct `ℓ/180` the governing
> deflection DCR is **0.629**, not 0.839 — and 0.629 is **below** this example's bending DCR of
> **0.678**. Example 2 is therefore **bending-governed** as written, and its stated purpose
> (§7.2.11) as the deflection-governed regression case is gone.
>
> `ex2_glulam_defl_total` and `ex2_overall` are **open fixtures**, not fixtures with new values.
> Writing 0.629 into them turns the suite green while silently deleting the only coverage of
> "the governing limit state is not always bending". **An engineer must supply a new §7.2 load
> case** — longer span, lighter section, or heavier snow — in which deflection genuinely governs
> at `ℓ/180`. That load case is deliberately not invented here. Gap register #18.
>
> The `ex2` **bending (0.678)**, **shear (0.332)** and **bearing (0.268)** fixtures are
> unaffected by the §5.5 correction and remain valid.

#### 7.2.11 Result

| Limit state | Governing combination | `C_D` | Demand | Capacity | DCR | Status |
|---|---|---|---|---|---|---|
| Bending | `D + S` = 600.15 plf | 1.15 | `f_b` = 1867.75 psi | `F_b'` = 2754.51 psi | 0.678 | PASS |
| Shear | `D + S` = 600.15 plf | 1.15 | `f_v` = 101.229 psi | `F_v'` = 304.75 psi | 0.332 | PASS |
| Bearing | `D + S` = 600.15 plf | n/a | `f_c⊥` = 174.194 psi | `F_c⊥'` = 650.00 psi | 0.268 | PASS |
| Deflection (`S`) | `S` alone | n/a | Δ = 0.43609 in | 0.800 in (`ℓ/240`) | 0.545 | PASS |
| Deflection (total) | `D + S` | n/a | Δ = 0.67108 in | 1.06667 in (`ℓ/180`) | 0.629 | PASS |

> **GOVERNING (as currently written): Bending, load combination `D + S`, `C_D = 1.15`,
> `DCR = 0.678`. PASS.** Governing serviceability case: deflection (total), `D + S`,
> `DCR = 0.629`.

This example **was** deliberately deflection-governed, and that is the only reason it exists:
it is the required regression test for the rule that the governing limit state is **not** always
bending, and that the app must report the governing serviceability case separately from the
governing strength case.

Correcting IBC Table 1604.3's `D + L` column (§5.5) moved its deflection DCR from 0.839 to
0.629, under the 0.678 bending DCR, so **as written it no longer exercises that rule.** The
example needs a new load case in which deflection genuinely governs at `ℓ/180`; see §7.2.10 and
gap register #18. The coverage is open — it has not been re-baselined away.

---

### 7.3 Regression fixture summary

| Fixture | Expected governing | Expected DCR (3 s.f.) | Exercises |
|---|---|---|---|
| `geom_2x10_table1b` | — | `A` = 13.875, `S_x` = 21.390625, `I_x` = 98.931641 | Table 1B lookup, not recomputation |
| `geom_glulam_5p25x11p875` | — | `A` = 62.343750, `S_x` = 123.388672, `I_x` = 732.620239 | computed rectangular geometry (`d²` = 141.015625, `d³` = 1674.560547) |
| `ex1_2x10_dfl_no2_rafter` | Bending, `D + S`, `C_D` = 1.15 | **0.543** | psf→plf, `C_D` envelope, `C_F`, `C_r`, `C_L`=1.0 branch |
| `ex1_bending_D_only` | — | **0.231** | zero-magnitude-term `C_D` rule (must be 0.90, not 1.00) |
| `ex1_shear_with_d_reduction` | Shear, `D + S` | **0.180** | §3.4.3.1 enabled |
| `ex1_shear_no_d_reduction` | Shear, `D + S` | **0.204** | §3.4.3.1 disabled |
| `ex1_bearing` | Bearing, `D + S` | **0.119** | `C_b` = 1.0 end-bearing branch, no `C_D` |
| `ex1_defl_live` | Deflection `S` alone | **0.250** | IBC `S or W` column, `ℓ/240` |
| `ex1_defl_total` | Deflection `D + S` | **0.281** | IBC `D + L` column, `ℓ/180` |
| `ex1b_unbraced` | Bending, `D + S` | **1.252** (FAIL) | full `C_L` derivation, `l_u/d > 14.3` band |
| `ex2_glulam_bending` | Bending, `D + S` | **0.678** | Table 5A lookup, `C_V`, `C_L` via `E_y,min` |
| `ex2_glulam_shear` | Shear, `D + S` | **0.332** | `F_vx`, `d`-reduction on a deep member |
| `ex2_glulam_bearing` | Bearing, `D + S` | **0.268** | `F_c⊥x` |
| `ex2_glulam_defl_total` | **Deflection, `D + S`** | ~~0.839~~ **BROKEN — see note** | `E_x,app` (not `E_x,true`), deflection-governed outcome |
| `ex2_overall` | Deflection (total) | ~~0.839~~ **BROKEN — see note** | limit-state selection across strength + serviceability |

> **Fixture note — `ex1_defl_total` corrected, `ex2_*` total-load fixtures blocked.**
>
> Both were computed against the collapsed two-column table corrected in §5.5, which checked
> the total-load deflection at the *variable-load* limit. Both used a nonplaster-ceiling roof,
> whose real `D + L` limit is `ℓ/180`, not `ℓ/240`.
>
> **`ex1_defl_total`: 0.375 → 0.281.** `Δ = 0.243586 in` is unchanged; only the allowable moves,
> from `ℓ/240 = 156/240 = 0.650 in` to `ℓ/180 = 156/180 = 0.866667 in`. `0.243586 / 0.866667 =
> 0.281061 → 0.281`. Example 1 stays bending-governed at 0.543, so its stated purpose survives
> and the fixture is simply corrected. `engine.js` already implements `ℓ/180` here and returns
> 0.281 today; the spec was the side that was wrong.
>
> **`ex2_glulam_defl_total` / `ex2_overall`: no corrected value is given here on purpose.**
> The same arithmetic gives `Δ = 0.671078 in` against `ℓ/180 = 192/180 = 1.066667 in`, i.e.
> **0.629**, not 0.839. But 0.629 is **below** Example 2's bending DCR of 0.678, so at the
> correct limit Example 2 is **no longer deflection-governed** — and being the deflection-
> governed regression case is the entire reason Example 2 exists (§7.2.11: *"This example is
> deliberately deflection-governed… the required regression test for the rule that the
> governing limit state is not always bending"*). Re-baselining `ex2_overall` to 0.629 would
> quietly delete that coverage while leaving the test green.
>
> **This needs a new load case for Example 2 — a longer span, a lighter section, or a heavier
> snow load chosen so that deflection genuinely governs at `ℓ/180`. That load case is not
> invented here.** Until an engineer sets it, treat `ex2_glulam_defl_total` and `ex2_overall`
> as open: the `ex2` bending / shear / bearing fixtures (0.678 / 0.332 / 0.268) are unaffected
> and still hold. Tracked as gap register #18 (§9).

Additional negative tests the implementation must carry:
- `R_B > 50` → hard error, no `C_L` returned.
- Southern Pine (Table 4B, `size_factor_applied: true`) → assert `C_F == 1.0`.
- A glulam input → assert `C_r == 1.0` and `C_F` is not in the stack.
- `C_L` and `C_V` both < 1.0 on a glulam → assert the product is **not** taken.

---

## 8. Scope boundaries — what this specification does NOT cover

The app must print this list, verbatim and unabridged, on every output. A calculation that does
not state its boundaries is not an engineering deliverable.

**Structural configuration**
1. **Multi-span and continuous members.** Only simply-supported single spans. No two-span,
   three-span, or continuous-over-support conditions; no moment redistribution; no negative
   moment at interior supports.
2. **Cantilevers**, including back-span/overhang combinations. The Table 3.3.3 cantilever `l_e`
   rows are deliberately not selectable.
3. **Non-uniform loading.** No concentrated loads, no partial-span loads, no triangular or
   trapezoidal distributions, no pattern loading. Uniform full-span load only.
4. **Non-prismatic members** — tapered, curved, or pitched-and-tapered glulam. `C_c` and `C_I`
   are held at 1.0 and no tapered-section stress-interaction check is performed.
5. **Sloped-member axial thrust**, rafter-tie/collar-tie action, and horizontal thrust at
   bearings. Spans are horizontal projections; axial force in the rafter is not computed.
6. **Built-up and composite members** — multi-ply nailed or bolted beams, flitch beams,
   ply-to-ply load sharing, and the NDS 15.3 spaced-column / built-up-column provisions.

**Member modifications**
7. **Notches** of any kind (NDS §3.4.3.2, §3.2.3). A notched member's shear capacity is
   governed by a different equation and this app does not implement it.
8. **Holes and penetrations** — round, square, or slotted; web holes; utility penetrations.
   NDS has no general design method for these; the app must refuse rather than approximate.
9. **Camber.** No camber is calculated, specified, or credited against deflection.

**Loads and load effects**
10. **LRFD.** ASD only. The `φ`, `λ`, and `K_F` format-conversion apparatus of NDS Appendix N
    is not implemented.
11. **Lateral loads** — wind and seismic. No `C_D = 1.6` combinations, no `0.6D + 0.6W`, no
    `0.6D + 0.7E`, no uplift, no net-uplift reversal on the member, no combined bending +
    axial from lateral drift.
12. **Rain load `R`** and ponding (NDS §3.3.2 requires a positive-drainage / stiffness check
    against progressive deflection). Neither the `R` combination nor the ponding stability
    check is implemented.
13. **Live load reduction** per IBC 1607.11 / ASCE 7 §4.7 and roof-live reduction per
    ASCE 7 §4.8. Enter unreduced psf values; no reduction is applied.
14. **Drift, sliding, unbalanced, and rain-on-snow snow loads** (ASCE 7 Ch. 7). Enter a single
    uniform `q_S`.
15. **Impact and vibration.** No impact factor is applied, and **no floor-vibration check is
    performed.** A floor joist that passes `ℓ/360` can still be objectionably bouncy; that is a
    separate serviceability criterion (TR-12, or a proprietary manufacturer method) and it is
    not implemented here.
16. **Fire design.** No char-rate calculation, no NDS Chapter 16 reduced-section method, no
    fire-resistance rating.

**Materials and environment**
17. **Connections of every kind** — hangers, straps, bolts, screws, nails, hold-downs, bearing
    plates as designed elements, and the group-action / row-tear-out provisions of NDS Ch. 11–13.
    Bearing is checked as `f_c⊥` on wood only.
18. **Interaction of wet service with pressure-preservative treatment and fire-retardant
    treatment.** The app applies `C_M` and `C_i` as independent multipliers per NDS. It does
    **not** model FRT-specific strength reductions, which are proprietary to the treater's
    evaluation report and are not in the material repo. If FRT is selected, the app must
    refuse and direct the user to the treater's report.
19. **Species and grades outside NDS-S Tables 4A, 4B, and 5A** — MSR/MEL (Table 4C), decking
    (Table 4E), non-North-American species (Table 4F), timbers (Table 4D), SCL, I-joists, CLT,
    and mass plywood. The repo has data for most of these; this spec does not cover their
    design equations.
20. **Bi-axial bending** and combined bending + axial (NDS §3.9). `C_P` is specified in §4.10
    for completeness but no interaction equation is evaluated.
21. **Deformation-limited `F_c⊥`.** NDS permits a reduced `F_c⊥` where a 0.02 in deformation
    limit is required rather than the 0.04 in basis of the tabulated value. Not implemented.
22. **Creep beyond the optional IBC `D/2 + L` footnote** (§5.5). No long-term creep factor
    `K_cr` per NDS §3.5.2 is applied to the total-load deflection.

**Process**
23. This is a **member check**, not a design. It does not select sections, iterate, or optimize.
24. Output is **not sealed engineering**. A licensed engineer must review the inputs,
    assumptions, and results and take professional responsibility for them.

---

## 9. Consolidated material-repo gap register

Everything the implementation needs that the repo at
`/workspace/firmark/material-databases` does **not** contain, and how to source it.

| # | Needed value | Status in repo | Action |
|---|---|---|---|
| 1 | **`C_F` size-factor table** (Table 4A) | **Partial.** 2"-thick column, widths 2x4–2x12, grades SS/#1/#2/#3/Stud, recoverable from `wood_sawn_member_database_phase1_nds2024_v1_2_wet_pressure_treated.json` → `derivation.cm_threshold_basis.size_factor_for_cm_threshold`. **Missing:** 4"-thick `F_b` column, 14"-and-wider row, Construction/Standard/Utility rows. No standalone table. | Transcribe full Table 4A size-factor block; file a repo coverage request |
| 2 | **`C_fu` flat-use table** (Table 4A) | **Absent.** No repo record of any kind. | Transcribe Table 4A; **verify against the printed table before release** — the only factor table in this spec with no repo cross-check |
| 3 | **`C_D` Table 2.3.2** | **Absent** (NDS body, not Supplement) | Hard-code constant |
| 4 | **`C_t` Table 2.3.3** | **Absent** | Hard-code constant |
| 5 | **`C_M` sawn multipliers + 1150/750 psi thresholds** | **Recoverable, not tabulated.** `derivation.wet_service_factors_used` and `derivation.cm_threshold_basis` in the wet/PT seed | Hard-code with the repo record as cross-check |
| 6 | **`C_i` Table 4.3.8** | **Recoverable, not tabulated.** `derivation.incising_factors_used` in the wet/PT seed | Hard-code with the repo record as cross-check |
| 7 | **`C_r` = 1.15** and its four conditions | **Absent** | Hard-code constant |
| 8 | **`C_b` Table 3.10.4** | **Absent** | Hard-code formula + table |
| 9 | **`C_V` exponent keyed to a Table 5A stress class** | **Partial and mis-keyed.** `volume_factor_exponent` 0.10 (DF) / 0.05 (SP) exists per manufacturer in `wood_glulam_current_official_public_2026_03_28.json` → `shared_design_adjustments`, but **NDS-S Table 5A stress classes carry no species tag** (`glulam_5a:24f_1_8e` has no species field) | **Require the user to declare the species**, or route them to `wood_glulam_bending_combination_reference_design_values_nds2024_table_5a_expanded.json`, whose 56 records are keyed `(combination_symbol, species)` |
| 10 | **NDS-S Table 1C glulam standard sizes / section properties** | **Absent as an NDS table.** Only manufacturer `member_size_properties` (Boise 67 rows, Rosboro X-Beam 48 rows) | Compute rectangular geometry from user-entered net `b × d`; flag non-tabulated sections in the UI |
| 11 | **Glulam `C_M` keyed to NDS** | **Recoverable, not NDS-keyed.** Manufacturer `wet_use_factors` (Boise/Rosboro/SmartLam/WFP) carry values identical to NDS-S Table 5A | Hard-code with the repo records as cross-check |
| 12 | **IBC Table 1604.3 deflection limits** | **Absent** (building code, not a material catalog) | Hard-code with citation |
| 13 | **ASCE 7 §2.4 load combinations** | **Absent** (loads standard, not a material catalog) | Hard-code with citation |
| 14 | **Species-specific density for self-weight** | **Partial.** Sawn: `approximate_weight_lbft_by_density_pcf` at 25–50 pcf (Table 1B seed) but no species density. Glulam: 35 pcf derivable from `glulam_rosboro_x_beam_2_0e_3p5x11p875` (`weight_plf` 10.1 ÷ area) | Default 35 pcf, editable, labelled an assumption |
| 15 | **`E_x,min` vs `E_y,min` selection rule for glulam `C_L`** | **Data present** (both published in Table 5A); **rule is NDS narrative text**, not data | Hard-code the rule; clause number to verify |
| 16 | **Timber `C_F = (12/d)^(1/9)` formula** (§4.3.6) | **Data present** (`wood_sawn_timbers_nds2024_table_4d.json`, 239 records, `size_factor_applied: false`); **formula absent** | Hard-code formula |
| 17 | **5-1/4 × 11-7/8 glulam at 24F-1.8E** | **Absent, and probably correctly so.** Repo has 11.875-deep glulam only at `b` = 3.5 and 5.5 (Rosboro X-Beam, 24F-V4-2.0E TRUE); Anthony Power Beam (the 5-1/4 in product line) publishes 28F-E1/SP, 28F-E2/SP, 30F-E1/SP with `"no discrete stock-size schedule"` | Treat §7.2 as a user-declared section; require supplier confirmation of a 24F-1.8E layup at that net size |
| 18 | **A deflection-governed load case for Example 2** | **Not a repo gap — an open engineering decision.** Correcting IBC Table 1604.3's `D + L` column (§5.5) moves Example 2's total-load deflection DCR from 0.839 to 0.629, below its bending DCR of 0.678, so §7.2 no longer demonstrates the deflection-governed outcome it was written to demonstrate | An engineer must set a new §7.2 load case — longer span, lighter section, or heavier snow — in which deflection genuinely governs at `ℓ/180`. **Do not re-baseline `ex2_overall` to 0.629**: that leaves the test green and the coverage gone. See the fixture note in §7.3 |

### 9.1 Clause numbers flagged for verification against the printed NDS 2024

- `E_min'` = `E_y,min` for glulam lateral-torsional buckling — rule confident, sub-clause of
  §3.3.3 to verify.
- `C_I` stress interaction factor — stated here as §5.3.9, **to verify**.
- `C_vr` shear reduction factor — stated here as §5.3.10, **to verify**; the value 0.72 is
  repo-confirmed.
- IBC Table 1604.3 wood-creep footnote letter (`D/2 + L` allowance) — footnote **(d)** in the
  2018 IBC; **letter to verify** in the 2021/2024 editions.

Clause numbers I am confident of and which the implementation may cite without a caveat:
NDS §2.3.2, Table 2.3.2, Table 2.3.3, §3.3.3 (and Table 3.3.3, §3.3.3.1, §3.3.3.6, §3.3.3.7,
§3.3.3.8, Eq. 3.3-6), §3.4.3.1, §3.4.3.2, §3.7.1, §3.10.4, Table 4.3.1, §4.3.6, Table 4.3.8,
§4.3.9, §4.4.2, Table 5.3.1, §5.3.6, §5.3.8; ASCE 7-22 §2.4.1; IBC Table 1604.3.
