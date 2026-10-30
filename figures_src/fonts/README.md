# Bundled fonts

The four faces of **TeX Gyre Heros** (regular, bold, italic, bold italic;
version 2.004, Bogusław Jackowski and Janusz M. Nowacki, GUST e-foundry)
are redistributed here unmodified under the GUST Font License
(`GUST-FONT-LICENSE.txt`, an instance of the LaTeX Project Public License;
see `MANIFEST-TeX-Gyre-Heros.txt`).

`hybridsim.plotstyle.apply_style()` registers them with Matplotlib so that
the figures are rendered -- and the layout lint in `hybridsim/figcheck.py`
measures text -- with the same font metrics in every environment, whether
or not a TeX distribution is installed.
