# SVG to PowerPoint Shape Converter

A Python library that converts SVG (Scalable Vector Graphics) files into native, editable PowerPoint shapes. Unlike simple image embedding, this tool parses SVG elements and recreates them as true PowerPoint objects—rectangles become rectangles, lines become lines, and text becomes editable text boxes.

## Installation

```bash
pip install svg2pptx
```

Or install from source:

```bash
git clone https://github.com/svg2pptx/svg2pptx.git
cd svg2pptx
pip install -e ".[dev]"
```

## Quick Start

```python
from svg2pptx import svg_to_pptx

# Convert SVG file to PowerPoint
svg_to_pptx("icon.svg", "output.pptx")
```

## Features

- **Editable shapes** — Resize, recolor, and modify individual elements directly in PowerPoint
- **Native formatting** — Apply PowerPoint styles, themes, and animations to converted shapes
- **Smaller file sizes** — Vector shapes are lighter than embedded raster images
- **Preservation of structure** — Maintain layers, groups, and object hierarchy from your original design

## Supported SVG Elements

| Element | Support |
|---------|---------|
| `<rect>` | ✅ Full |
| `<circle>` | ✅ Full |
| `<ellipse>` | ✅ Full |
| `<line>` | ✅ Full |
| `<polygon>` | ✅ Full |
| `<polyline>` | ✅ Full |
| `<path>` | ✅ Approximated curves |
| `<g>` (groups) | ✅ Full |
| `<text>` | ✅ Basic |

## Configuration

```python
from svg2pptx import svg_to_pptx, Config

config = Config(
    scale=2.0,                  # Scale factor for SVG content
    curve_tolerance=0.5,        # Curve approximation quality (lower = more accurate)
    preserve_groups=True,       # Maintain SVG group structure
)

svg_to_pptx("diagram.svg", "output.pptx", config=config)
```

## Advanced Usage

```python
from svg2pptx import SVGConverter
from pptx import Presentation

# Add SVG shapes to an existing presentation
prs = Presentation()
slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

converter = SVGConverter()
converter.add_to_slide("icon.svg", slide)

prs.save("combined.pptx")
```

## Limitations

- **Bezier curves** are approximated with line segments (configurable tolerance)
- **Gradients** are not supported (will use first color)
- **Filters and effects** (blur, drop shadow) are not supported
- **CSS external stylesheets** are not supported

## License

MIT License