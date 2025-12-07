# Publication-Ready Graphs - Usage Guide

## Generated Files

1. **`reports/graphs.tex`** - LaTeX/PGFPlots code for publication-quality graphs
2. **`reports/graphs.html`** - Interactive HTML visualization (view in browser)

---

## Using LaTeX Graphs in Your Paper

### Step 1: Add Required Packages

Add these lines to your LaTeX document preamble (before `\begin{document}`):

```latex
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{tikz}
```

### Step 2: Include Graphs

Copy the figure environments from `reports/graphs.tex` into your LaTeX document where you want the graphs to appear.

### Step 3: Compile

Compile your LaTeX document with PDFLaTeX or XeLaTeX. The graphs will be rendered as vector graphics (perfect quality at any zoom level).

---

## Available Graphs

The following graphs are included in `reports/graphs.tex`:

1. **Figure 1: DSL Action Distribution** (`fig:action_distribution`)
   - Bar chart showing distribution of REPL, DELL, ADDL, REPW actions
   - Shows which actions are most commonly used in repairs

2. **Figure 2: Corruption Type Distribution** (`fig:corruption_distribution`)
   - Bar chart showing distribution of Delete, Add, Replace corruption types
   - Shows the balance of different corruption patterns

3. **Figure 3: Dataset Size Comparison** (`fig:dataset_comparison`)
   - Bar chart comparing sizes of MBPP, CoE, and Repair datasets
   - Visualizes the scale of generated data

4. **Figure 4: Trace Length Distribution** (`fig:trace_length`)
   - Histogram showing distribution of trace lengths (number of steps)
   - Shows complexity of repair sequences

---

## Using HTML Visualization

Simply open `reports/graphs.html` in any web browser to view interactive charts. These are useful for:
- Quick preview of the data
- Presentations
- Sharing with collaborators
- Exporting screenshots

The HTML file uses Chart.js and works offline (after initial load).

---

## Customization

### Changing Colors

In `reports/graphs.tex`, you can modify colors by changing the `fill` parameter in `\addplot` commands:

```latex
\addplot[fill=blue!50] coordinates {...};
```

### Changing Sizes

Modify the `width` and `height` parameters in the `axis` environment:

```latex
width=12cm,  % Change width
height=8cm,  % Change height
```

### Adding More Graphs

You can extend `generate_graphs_latex.py` to create additional visualizations by:
1. Adding new data analysis functions
2. Creating new LaTeX figure environments
3. Following the same pattern as existing graphs

---

## Graph Statistics Summary

- **Action Distribution**: REPL (42.9%), DELL (38.1%), ADDL (19.0%)
- **Corruption Patterns**: Delete (41.8%), Add (41.5%), Replace (16.7%)
- **Dataset Sizes**: MBPP (374), CoE (10), Repair (1,122)
- **Average Trace Length**: 6.2 steps

---

## Troubleshooting

### LaTeX Compilation Errors

If you get errors about missing packages:
```bash
# Install required packages (TeX Live/MiKTeX)
tlmgr install pgfplots tikz
```

### HTML Not Displaying

- Ensure you have internet connection (for Chart.js CDN)
- Check browser console for JavaScript errors
- Try a different browser

### Graphs Look Different

- PGFPlots version differences can cause minor rendering differences
- Ensure `\pgfplotsset{compat=1.18}` is set to match your TeX distribution

---

## Example LaTeX Document

```latex
\documentclass{article}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{tikz}

\begin{document}

\section{Results}

% Copy figure environments from graphs.tex here

\begin{figure}[h]
\centering
% ... (copy from graphs.tex)
\end{figure}

\end{document}
```

---

*Generated automatically by generate_graphs_latex.py*

