"""Build single-page PDF deliverables from a composite TIFF.

Two outputs:
  - archival one-page PDF: full-resolution JPEG (quality 92, 4:4:4) on a
    300 ppi page, with the traced navigation grid as an optional content
    group (OCG layer, default OFF) — vector lines and labels drawn in PDF
    operators, never touching the raster.
  - chat one-page PDF: same page layout, JPEG quality tuned to fit a byte
    budget (30 MiB chat delivery limit), no overlay.

Usage: python3 onepage.py <composite.tif> <outdir> [pad]
"""
import json
import os
import sys

import numpy as np

import config
import coverage_prior as cov

os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(2 ** 40))
import cv2  # noqa: E402
import pikepdf  # noqa: E402

DPI = 300


def jpeg_bytes(img, quality, subsample_444=True):
    flags = [cv2.IMWRITE_JPEG_QUALITY, quality]
    if subsample_444:
        flags += [cv2.IMWRITE_JPEG_SAMPLING_FACTOR,
                  cv2.IMWRITE_JPEG_SAMPLING_FACTOR_444]
    ok, buf = cv2.imencode(".jpg", img, flags)
    assert ok
    return patch_density(buf.tobytes())


def patch_density(jpg):
    """Stamp 300x300 dpi into the JFIF APP0 header."""
    if jpg[2:4] == b"\xff\xe0" and jpg[6:11] == b"JFIF\x00":
        b = bytearray(jpg)
        b[13] = 1
        b[14:16] = DPI.to_bytes(2, "big")
        b[16:18] = DPI.to_bytes(2, "big")
        return bytes(b)
    return jpg


def grid_layer_stream(w_px, h_px, pad, year="1885"):
    """PDF content stream drawing the consensus street grid in page units
    (1 pt = 300/72 px). Returns (stream, fonts_needed)."""
    reg = json.load(open(os.path.join(config.BUILD_DIR, year,
                                      "registration.json")))
    X = {int(k): v for k, v in reg["consensus_av"].items()}
    Y = {int(k): v for k, v in reg["consensus_st"].items()}
    ed = config.EDITIONS[year]
    k = 72.0 / DPI  # px -> pt

    def px(x):  # canvas x -> pt
        return (x + pad) * k

    def py(y):  # canvas y -> pt (PDF origin bottom-left)
        return (h_px - (y + pad)) * k

    av_names = {0: "A (Water)", 1: "B (Strand)", 2: "C (Mechanic)",
                3: "D (Market)", 4: "E (Postoffice)", 5: "F (Church)",
                6: "G (Winnie)", 7: "H (Ball)", 8: "I (Sealy)",
                9: "J (Broadway)"}
    s = []
    s.append("q 1 0 0 RG 2.2 w [9 6] d")           # red, dashed
    y_lo, y_hi = min(Y.values()), max(Y.values())
    x_lo, x_hi = min(X.values()), max(X.values())
    for a, x in sorted(X.items()):
        s.append(f"{px(x):.1f} {py(y_lo - 120):.1f} m "
                 f"{px(x):.1f} {py(y_hi + 120):.1f} l S")
    for st, y in sorted(Y.items()):
        s.append(f"{px(x_lo - 120):.1f} {py(y):.1f} m "
                 f"{px(x_hi + 120):.1f} {py(y):.1f} l S")
    s.append("[] 0 d")
    # labels
    s.append("BT /F1 26 Tf 1 0 0 rg")
    for a, x in sorted(X.items()):
        name = f"Av. {av_names.get(a, chr(65 + a))}"
        s.append(f"1 0 0 1 {px(x) + 6:.1f} {py(y_lo - 160):.1f} Tm ({name}) Tj")
    for st, y in sorted(Y.items()):
        nm = {1: "st", 2: "nd", 3: "rd"}.get(st % 10 if st % 100 not in
                                             (11, 12, 13) else 0, "th")
        s.append(f"1 0 0 1 {px(x_lo - 340):.1f} {py(y) + 6:.1f} Tm "
                 f"({st}{nm} St.) Tj")
    s.append("ET")
    # target marker: 22nd & Postoffice
    tx, ty = px(X[4]), py(Y[22])
    s.append(f"0 0.55 0 RG 3 w "
             f"{tx - 30:.1f} {ty - 30:.1f} 60 60 re S")
    s.append(f"BT /F1 30 Tf 0 0.55 0 rg 1 0 0 1 {tx + 38:.1f} {ty + 10:.1f} "
             "Tm (22nd & Postoffice) Tj ET")
    s.append("BT /F1 22 Tf 1 0 0 rg 1 0 0 1 20 20 Tm "
             "(NAVIGATION LAYER \\(derived, traced grid\\) - toggle off for "
             "the untouched archival raster) Tj ET Q")
    return "\n".join(s)


def build_pdf(img, out_path, quality, overlay_pad=None, subsample_444=True):
    h_px, w_px = img.shape[:2]
    jpg = jpeg_bytes(img, quality, subsample_444)
    w_pt, h_pt = w_px * 72.0 / DPI, h_px * 72.0 / DPI

    pdf = pikepdf.new()
    stream = pikepdf.Stream(pdf, jpg)
    stream.stream_dict = pikepdf.Dictionary(
        Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image,
        Width=w_px, Height=h_px, ColorSpace=pikepdf.Name.DeviceRGB,
        BitsPerComponent=8, Filter=pikepdf.Name.DCTDecode)
    content = f"q {w_pt:.2f} 0 0 {h_pt:.2f} 0 0 cm /Im0 Do Q\n"
    resources = {"/XObject": {"/Im0": stream}}

    if overlay_pad is not None:
        ocg = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.OCG, Name=pikepdf.String("Navigation grid")))
        pdf.Root.OCProperties = pikepdf.Dictionary(
            OCGs=pikepdf.Array([ocg]),
            D=pikepdf.Dictionary(OFF=pikepdf.Array([ocg]),
                                 Order=pikepdf.Array([ocg])))
        layer = grid_layer_stream(w_px, h_px, overlay_pad)
        content += f"/OC /NavOC BDC\n{layer}\nEMC\n"
        resources["/Properties"] = {"/NavOC": ocg}
        resources["/Font"] = {"/F1": pikepdf.Dictionary(
            Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name("/Helvetica-Bold"))}

    res = pikepdf.Dictionary()
    for k, d in resources.items():
        sub = pikepdf.Dictionary()
        for n, v in d.items():
            sub[n] = v
        res[k] = sub
    page = pikepdf.Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=[0, 0, w_pt, h_pt],
        Resources=res,
        Contents=pikepdf.Stream(pdf, content.encode()))
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(page)))
    pdf.save(out_path)
    return os.path.getsize(out_path), len(jpg)


def main():
    tif, outdir = sys.argv[1], sys.argv[2]
    pad = int(sys.argv[3]) if len(sys.argv) > 3 else None
    os.makedirs(outdir, exist_ok=True)
    img = cv2.imread(tif)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    p = os.path.join(outdir, "galveston_1885_onepage.pdf")
    n, j = build_pdf(img_rgb, p, 92, overlay_pad=pad)
    print(f"archival onepage: {n/1e6:.1f} MB (jpeg {j/1e6:.1f} MB)")

    # chat copy: binary-search quality to fit under 28 MB (30 MiB cap
    # minus headroom), 4:2:0 like any web JPEG at this size
    budget = 28_000_000
    lo, hi, best = 30, 80, None
    while lo <= hi:
        q = (lo + hi) // 2
        jpg = jpeg_bytes(img_rgb, q, subsample_444=False)
        if len(jpg) <= budget:
            best = q
            lo = q + 1
        else:
            hi = q - 1
    p2 = os.path.join(outdir, "galveston_1885_onepage_compressed.pdf")
    n2, j2 = build_pdf(img_rgb, p2, best, overlay_pad=pad,
                       subsample_444=False)
    print(f"chat onepage: q{best}, {n2/1e6:.1f} MB")


if __name__ == "__main__":
    main()
