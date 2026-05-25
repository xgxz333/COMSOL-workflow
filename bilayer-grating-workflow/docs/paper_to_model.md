# Paper-to-Model Mapping

## Information extracted from the article

The reference is Zhang et al., *Laser & Photonics Reviews* 18, 2301233
(2024), "Large-Range Beam Steering through Dynamic Manipulation of
Topological Charges."

The main article describes a one-dimensional silicon grating covered by GST
and SiO2 on both sides. Its mechanism is:

1. An up-down and left-right symmetric grating with vertical sidewalls
   supports an accidental off-Gamma BIC on a TE-like band.
2. Tilting a sidewall from 90 degrees to 78 degrees breaks up-down symmetry
   and splits an integer topological charge into two half-integer charges.
3. Changing the GST refractive index moves and merges these charges
   differently in upward and downward radiation channels, yielding a
   unidirectional guided resonance (UGR).

Quantitative anchors given in the main article are:

| Item | Value |
| --- | --- |
| Silicon refractive index | 3.48 |
| Symmetric BIC location | `kx*a/(2*pi) = 0.1422` |
| Final sidewall angle | 78 degrees |
| a-GST real refractive index | 4.724 |
| c-GST real refractive index | 5.96 |
| a-GST UGR | upward, `kx*a/(2*pi) = 0.1342`, 186 THz |
| c-GST UGR | downward, `kx*a/(2*pi) = 0.0954`, 179 THz |
| Same-frequency demonstration | 183.5 THz |
| GST extinction coefficients used with loss | 0.05 and 0.30 |

The detailed original dimensions are delegated to the Supporting
Information, which is not contained in the supplied PDF. Dimensions in the
default configuration of this project are therefore search seeds, not a
claim of exact paper reproduction.

## Proposed device translated to 2D

This project represents the user's new hypothesis rather than the paper's
single-grating geometry:

- Two vertically separated silicon gratings share exactly the same period,
  duty cycle, lateral center, and silicon thickness.
- A PCM cap is placed only above the upper silicon ridge.
- An upper SiO2 encapsulation/cap is included around the PCM. The initial
  inter-grating gap uses background material because no spacer was specified
  in the proposed modification.
- The unequal upper material environment is the only intended vertical
  symmetry-breaking mechanism.

The unit cell is modeled in an `x-z` cross-section with Floquet periodic
boundaries along `x` and PML/open radiation boundaries along `z`.

## Validation target

For each candidate geometry, the same eigenmode calculation is performed for
amorphous and crystalline PCM. A useful switching design must provide:

- strong upward radiation in the amorphous state;
- strong downward radiation in the crystalline state;
- adequate `Q` in both states;
- resonance frequencies sufficiently close for a practical single-frequency
  operating point.

The objective is consequently more selective than maximizing `Q` alone. A
high-Q mode that is dark in both directions or radiates in the same direction
for both PCM states is not considered a successful switch.
