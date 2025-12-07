"""
Generate LaTeX/PGFPlots code for publication-quality graphs.
This doesn't require matplotlib installation.
"""
import json
import os
from collections import Counter

def load_data():
    """Load all datasets."""
    data = {}
    
    # Load CoE demonstrations
    if os.path.exists('data/coe_demos/coe_train.jsonl'):
        with open('data/coe_demos/coe_train.jsonl', 'r') as f:
            coe_data = [json.loads(l) for l in f]
        
        action_types = []
        trace_lengths = []
        for d in coe_data:
            trace_lengths.append(len(d['trace']))
            for item in d['trace']:
                if item.startswith('DELL'):
                    action_types.append('DELL')
                elif item.startswith('ADDL'):
                    action_types.append('ADDL')
                elif item.startswith('REPL'):
                    action_types.append('REPL')
                elif item.startswith('REPW'):
                    action_types.append('REPW')
        
        data['coe'] = {
            'action_types': action_types,
            'trace_lengths': trace_lengths,
            'total': len(coe_data)
        }
    
    # Load repair tasks
    if os.path.exists('data/repair_tasks/repair_train.jsonl'):
        with open('data/repair_tasks/repair_train.jsonl', 'r') as f:
            repair_data = [json.loads(l) for l in f]
        
        corruption_types = []
        code_lengths = []
        for d in repair_data:
            code_lengths.append(len(d['init_code']))
            gt_lines = len(d.get('ground_truth', '').splitlines())
            init_lines = len(d['init_code'])
            if init_lines < gt_lines:
                corruption_types.append('Delete')
            elif init_lines > gt_lines:
                corruption_types.append('Add')
            else:
                corruption_types.append('Replace')
        
        data['repair'] = {
            'corruption_types': corruption_types,
            'code_lengths': code_lengths,
            'total': len(repair_data)
        }
    
    # Load MBPP
    if os.path.exists('data/mbpp_raw/train.jsonl'):
        with open('data/mbpp_raw/train.jsonl', 'r') as f:
            mbpp_data = [json.loads(l) for l in f]
        
        code_lengths = [len(d.get('code', '').splitlines()) for d in mbpp_data]
        test_counts = [len(d.get('test_list', d.get('tests', []))) for d in mbpp_data]
        
        data['mbpp'] = {
            'code_lengths': code_lengths,
            'test_counts': test_counts,
            'total': len(mbpp_data)
        }
    
    return data

def generate_latex_graphs(data, output_file='graphs.tex'):
    """Generate LaTeX/PGFPlots code for all graphs."""
    
    latex_code = """% Publication-Quality Graphs for Chain-of-Edits Code Repair
% Generated automatically - ready to include in LaTeX document
% Requires: \\usepackage{pgfplots} in preamble

"""
    
    # 1. Action Distribution Bar Chart
    if 'coe' in data:
        action_counts = Counter(data['coe']['action_types'])
        actions = sorted(action_counts.keys())
        counts = [action_counts[a] for a in actions]
        
        latex_code += """
% Figure 1: DSL Action Distribution
\\begin{figure}[h]
\\centering
\\begin{tikzpicture}
\\begin{axis}[
    ybar,
    bar width=0.6cm,
    width=10cm,
    height=6cm,
    ylabel={Count},
    xlabel={DSL Action Type},
    title={Distribution of DSL Actions in CoE Demonstrations},
    symbolic x coords={""" + ','.join(actions) + """},
    xtick=data,
    nodes near coords,
    nodes near coords align={vertical},
    ymin=0,
    grid=major,
    grid style={dashed, gray!30},
]
"""
        for action, count in zip(actions, counts):
            latex_code += f"\\addplot coordinates {{({action},{count})}};\n"
        
        latex_code += """\\end{axis}
\\end{tikzpicture}
\\caption{Distribution of DSL Actions in CoE Demonstrations}
\\label{fig:action_distribution}
\\end{figure}

"""
    
    # 2. Corruption Distribution
    if 'repair' in data:
        corruption_counts = Counter(data['repair']['corruption_types'])
        corruptions = sorted(corruption_counts.keys())
        counts = [corruption_counts[c] for c in corruptions]
        percentages = [c/sum(counts)*100 for c in counts]
        
        latex_code += """
% Figure 2: Corruption Type Distribution
\\begin{figure}[h]
\\centering
\\begin{tikzpicture}
\\begin{axis}[
    ybar,
    bar width=0.8cm,
    width=10cm,
    height=6cm,
    ylabel={Count},
    xlabel={Corruption Type},
    title={Distribution of Corruption Types in Repair Tasks},
    symbolic x coords={""" + ','.join(corruptions) + """},
    xtick=data,
    nodes near coords={\\pgfmathprintnumber{\\pgfplotspointmeta} (\\pgfmathprintnumber[fixed,precision=1]{\\pgfplotspointmeta*100/sum}%)},
    nodes near coords align={vertical},
    ymin=0,
    grid=major,
    grid style={dashed, gray!30},
]
"""
        for corruption, count in zip(corruptions, counts):
            latex_code += f"\\addplot coordinates {{({corruption},{count})}};\n"
        
        latex_code += """\\end{axis}
\\end{tikzpicture}
\\caption{Distribution of Corruption Types in Repair Tasks}
\\label{fig:corruption_distribution}
\\end{figure}

"""
    
    # 3. Dataset Comparison
    datasets = []
    counts = []
    if 'mbpp' in data:
        datasets.append('MBPP')
        counts.append(data['mbpp']['total'])
    if 'coe' in data:
        datasets.append('CoE')
        counts.append(data['coe']['total'])
    if 'repair' in data:
        datasets.append('Repair')
        counts.append(data['repair']['total'])
    
    if datasets:
        latex_code += """
% Figure 3: Dataset Size Comparison
\\begin{figure}[h]
\\centering
\\begin{tikzpicture}
\\begin{axis}[
    ybar,
    bar width=1cm,
    width=10cm,
    height=6cm,
    ylabel={Number of Examples},
    xlabel={Dataset},
    title={Dataset Size Comparison},
    symbolic x coords={""" + ','.join(datasets) + """},
    xtick=data,
    nodes near coords,
    nodes near coords align={vertical},
    ymin=0,
    grid=major,
    grid style={dashed, gray!30},
]
"""
        for dataset, count in zip(datasets, counts):
            latex_code += f"\\addplot coordinates {{({dataset},{count})}};\n"
        
        latex_code += """\\end{axis}
\\end{tikzpicture}
\\caption{Dataset Size Comparison}
\\label{fig:dataset_comparison}
\\end{figure}

"""
    
    # 4. Trace Length Distribution (histogram)
    if 'coe' in data:
        trace_lengths = data['coe']['trace_lengths']
        length_counts = Counter(trace_lengths)
        lengths = sorted(length_counts.keys())
        freqs = [length_counts[l] for l in lengths]
        
        latex_code += """
% Figure 4: Trace Length Distribution
\\begin{figure}[h]
\\centering
\\begin{tikzpicture}
\\begin{axis}[
    ybar,
    bar width=0.5cm,
    width=10cm,
    height=6cm,
    ylabel={Frequency},
    xlabel={Trace Length (steps)},
    title={Distribution of Trace Lengths in CoE Demonstrations},
    xtick={""" + ','.join(map(str, lengths)) + """},
    ymin=0,
    grid=major,
    grid style={dashed, gray!30},
]
"""
        for length, freq in zip(lengths, freqs):
            latex_code += f"\\addplot coordinates {{({length},{freq})}};\n"
        
        latex_code += """\\end{axis}
\\end{tikzpicture}
\\caption{Distribution of Trace Lengths in CoE Demonstrations}
\\label{fig:trace_length}
\\end{figure}

"""
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(latex_code)
    
    print(f"LaTeX graph code saved to: {output_file}")
    return latex_code

def generate_html_visualizations(data, output_file='graphs.html'):
    """Generate HTML/SVG visualizations using basic JavaScript."""
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Chain-of-Edits Code Repair - Results Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        h2 { color: #555; margin-top: 30px; border-bottom: 2px solid #2E86AB; padding-bottom: 10px; }
        .chart-container { margin: 30px 0; position: relative; height: 400px; }
        canvas { max-width: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Chain-of-Edits Code Repair System - Results Visualization</h1>
"""
    
    # Action Distribution
    if 'coe' in data:
        action_counts = Counter(data['coe']['action_types'])
        actions = list(action_counts.keys())
        counts = [action_counts[a] for a in actions]
        
        html += """
        <h2>DSL Action Distribution</h2>
        <div class="chart-container">
            <canvas id="actionChart"></canvas>
        </div>
        <script>
            const actionCtx = document.getElementById('actionChart').getContext('2d');
            new Chart(actionCtx, {
                type: 'bar',
                data: {
                    labels: """ + json.dumps(actions) + """,
                    datasets: [{
                        label: 'Action Count',
                        data: """ + json.dumps(counts) + """,
                        backgroundColor: ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'],
                        borderColor: ['#1a5a7a', '#7a2d55', '#c16a01', '#9a2f16'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: { display: true, text: 'Distribution of DSL Actions in CoE Demonstrations', font: { size: 16 } },
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'Count' } },
                        x: { title: { display: true, text: 'DSL Action Type' } }
                    }
                }
            });
        </script>
"""
    
    # Corruption Distribution
    if 'repair' in data:
        corruption_counts = Counter(data['repair']['corruption_types'])
        corruptions = list(corruption_counts.keys())
        counts = [corruption_counts[c] for c in corruptions]
        
        html += """
        <h2>Corruption Type Distribution</h2>
        <div class="chart-container">
            <canvas id="corruptionChart"></canvas>
        </div>
        <script>
            const corruptionCtx = document.getElementById('corruptionChart').getContext('2d');
            new Chart(corruptionCtx, {
                type: 'bar',
                data: {
                    labels: """ + json.dumps(corruptions) + """,
                    datasets: [{
                        label: 'Corruption Count',
                        data: """ + json.dumps(counts) + """,
                        backgroundColor: ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'],
                        borderColor: ['#1a5a7a', '#7a2d55', '#c16a01', '#9a2f16'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: { display: true, text: 'Distribution of Corruption Types in Repair Tasks', font: { size: 16 } },
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'Count' } },
                        x: { title: { display: true, text: 'Corruption Type' } }
                    }
                }
            });
        </script>
"""
    
    # Dataset Comparison
    datasets = []
    counts = []
    if 'mbpp' in data:
        datasets.append('MBPP Training')
        counts.append(data['mbpp']['total'])
    if 'coe' in data:
        datasets.append('CoE Demos')
        counts.append(data['coe']['total'])
    if 'repair' in data:
        datasets.append('Repair Tasks')
        counts.append(data['repair']['total'])
    
    if datasets:
        html += """
        <h2>Dataset Size Comparison</h2>
        <div class="chart-container">
            <canvas id="datasetChart"></canvas>
        </div>
        <script>
            const datasetCtx = document.getElementById('datasetChart').getContext('2d');
            new Chart(datasetCtx, {
                type: 'bar',
                data: {
                    labels: """ + json.dumps(datasets) + """,
                    datasets: [{
                        label: 'Number of Examples',
                        data: """ + json.dumps(counts) + """,
                        backgroundColor: ['#2E86AB', '#A23B72', '#F18F01'],
                        borderColor: ['#1a5a7a', '#7a2d55', '#c16a01'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: { display: true, text: 'Dataset Size Comparison', font: { size: 16 } },
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'Number of Examples' } },
                        x: { title: { display: true, text: 'Dataset' } }
                    }
                }
            });
        </script>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"HTML visualization saved to: {output_file}")
    return html

def main():
    print("=" * 80)
    print("GENERATING GRAPH CODE (No matplotlib required)")
    print("=" * 80)
    print()
    
    # Load data
    print("Loading data...")
    data = load_data()
    
    # Generate LaTeX code
    print("\nGenerating LaTeX/PGFPlots code...")
    generate_latex_graphs(data, 'reports/graphs.tex')
    
    # Generate HTML visualization
    print("Generating HTML visualization...")
    os.makedirs('reports', exist_ok=True)
    generate_html_visualizations(data, 'reports/graphs.html')
    
    print("\n" + "=" * 80)
    print("Graph code generation complete!")
    print("=" * 80)
    print("\nFiles generated:")
    print("  1. reports/graphs.tex - LaTeX/PGFPlots code (copy into your paper)")
    print("  2. reports/graphs.html - Interactive HTML visualization (open in browser)")
    print("\nTo use LaTeX graphs:")
    print("  - Add \\usepackage{pgfplots} to your LaTeX preamble")
    print("  - Copy the figure environments from graphs.tex into your document")
    print("\nTo view HTML graphs:")
    print("  - Open reports/graphs.html in any web browser")

if __name__ == "__main__":
    main()

