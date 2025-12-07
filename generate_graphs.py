"""
Generate publication-quality graphs for the paper.
"""
import json
import os
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from collections import Counter

# Set publication-quality style
try:
    plt.style.use('seaborn-v0_8-paper')
except:
    try:
        plt.style.use('seaborn-paper')
    except:
        plt.style.use('default')
matplotlib.rcParams.update({
    'font.size': 11,
    'font.family': 'serif',
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 16,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1
})

def load_data():
    """Load all datasets."""
    data = {}
    
    # Load CoE demonstrations
    if os.path.exists('data/coe_demos/coe_train.jsonl'):
        with open('data/coe_demos/coe_train.jsonl', 'r') as f:
            coe_data = [json.loads(l) for l in f]
        
        # Extract action types
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
        
        # Analyze corruption patterns
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

def plot_action_distribution(data, output_dir='reports'):
    """Plot distribution of DSL actions."""
    if 'coe' not in data:
        return
    
    action_counts = Counter(data['coe']['action_types'])
    actions = list(action_counts.keys())
    counts = list(action_counts.values())
    
    # Sort by count
    sorted_pairs = sorted(zip(actions, counts), key=lambda x: x[1], reverse=True)
    actions, counts = zip(*sorted_pairs) if sorted_pairs else ([], [])
    
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(actions, counts, color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'][:len(actions)])
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontweight='bold')
    
    ax.set_xlabel('DSL Action Type', fontweight='bold')
    ax.set_ylabel('Count', fontweight='bold')
    ax.set_title('Distribution of DSL Actions in CoE Demonstrations', fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/action_distribution.png', format='png', dpi=300)
    plt.savefig(f'{output_dir}/action_distribution.pdf', format='pdf')
    print(f"Saved: {output_dir}/action_distribution.png and .pdf")
    plt.close()

def plot_action_pie_chart(data, output_dir='reports'):
    """Plot pie chart of action distribution."""
    if 'coe' not in data:
        return
    
    action_counts = Counter(data['coe']['action_types'])
    actions = list(action_counts.keys())
    counts = list(action_counts.values())
    
    # Sort by count
    sorted_pairs = sorted(zip(actions, counts), key=lambda x: x[1], reverse=True)
    actions, counts = zip(*sorted_pairs) if sorted_pairs else ([], [])
    
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'][:len(actions)]
    
    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(counts, labels=actions, autopct='%1.1f%%',
                                       colors=colors, startangle=90,
                                       textprops={'fontsize': 12, 'fontweight': 'bold'})
    
    # Make percentage text white and bold
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    ax.set_title('DSL Action Distribution\n(CoE Demonstrations)', 
                 fontweight='bold', fontsize=14, pad=20)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/action_pie_chart.png', format='png', dpi=300)
    plt.savefig(f'{output_dir}/action_pie_chart.pdf', format='pdf')
    print(f"Saved: {output_dir}/action_pie_chart.png and .pdf")
    plt.close()

def plot_corruption_distribution(data, output_dir='reports'):
    """Plot distribution of corruption types."""
    if 'repair' not in data:
        return
    
    corruption_counts = Counter(data['repair']['corruption_types'])
    corruptions = list(corruption_counts.keys())
    counts = list(corruption_counts.values())
    
    # Sort by count
    sorted_pairs = sorted(zip(corruptions, counts), key=lambda x: x[1], reverse=True)
    corruptions, counts = zip(*sorted_pairs) if sorted_pairs else ([], [])
    
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(corruptions, counts, color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'][:len(corruptions)])
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}\n({height/sum(counts)*100:.1f}%)',
                ha='center', va='bottom', fontweight='bold')
    
    ax.set_xlabel('Corruption Type', fontweight='bold')
    ax.set_ylabel('Count', fontweight='bold')
    ax.set_title('Distribution of Corruption Types in Repair Tasks', fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/corruption_distribution.png', format='png', dpi=300)
    plt.savefig(f'{output_dir}/corruption_distribution.pdf', format='pdf')
    print(f"Saved: {output_dir}/corruption_distribution.png and .pdf")
    plt.close()

def plot_code_length_distribution(data, output_dir='reports'):
    """Plot distribution of code lengths across datasets."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    datasets = []
    if 'mbpp' in data:
        datasets.append(('MBPP Training', data['mbpp']['code_lengths'], axes[0]))
    if 'repair' in data:
        datasets.append(('Repair Tasks', data['repair']['code_lengths'], axes[1]))
    if 'coe' in data:
        # Get initial code lengths from CoE
        with open('data/coe_demos/coe_train.jsonl', 'r') as f:
            coe_data = [json.loads(l) for l in f]
        init_lengths = [len(d['init_code_lines']) for d in coe_data]
        datasets.append(('CoE Initial Code', init_lengths, axes[2]))
    
    for title, lengths, ax in datasets:
        ax.hist(lengths, bins=15, color='#2E86AB', edgecolor='black', alpha=0.7)
        ax.set_xlabel('Code Lines', fontweight='bold')
        ax.set_ylabel('Frequency', fontweight='bold')
        ax.set_title(title, fontweight='bold', pad=10)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        # Add statistics
        mean_val = np.mean(lengths)
        median_val = np.median(lengths)
        ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.1f}')
        ax.axvline(median_val, color='green', linestyle='--', linewidth=2, label=f'Median: {median_val:.1f}')
        ax.legend(fontsize=9)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/code_length_distribution.png', format='png', dpi=300)
    plt.savefig(f'{output_dir}/code_length_distribution.pdf', format='pdf')
    print(f"Saved: {output_dir}/code_length_distribution.png and .pdf")
    plt.close()

def plot_trace_length_distribution(data, output_dir='reports'):
    """Plot distribution of trace lengths in CoE demonstrations."""
    if 'coe' not in data:
        return
    
    trace_lengths = data['coe']['trace_lengths']
    
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(trace_lengths, bins=range(min(trace_lengths), max(trace_lengths)+2), 
            color='#A23B72', edgecolor='black', alpha=0.7)
    
    mean_val = np.mean(trace_lengths)
    median_val = np.median(trace_lengths)
    ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f}')
    ax.axvline(median_val, color='green', linestyle='--', linewidth=2, label=f'Median: {median_val:.1f}')
    
    ax.set_xlabel('Trace Length (steps)', fontweight='bold')
    ax.set_ylabel('Frequency', fontweight='bold')
    ax.set_title('Distribution of Trace Lengths in CoE Demonstrations', fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.legend()
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/trace_length_distribution.png', format='png', dpi=300)
    plt.savefig(f'{output_dir}/trace_length_distribution.pdf', format='pdf')
    print(f"Saved: {output_dir}/trace_length_distribution.png and .pdf")
    plt.close()

def plot_dataset_comparison(data, output_dir='reports'):
    """Plot comparison of dataset sizes."""
    datasets = []
    counts = []
    
    if 'mbpp' in data:
        datasets.append('MBPP\nTraining')
        counts.append(data['mbpp']['total'])
    if 'coe' in data:
        datasets.append('CoE\nDemos')
        counts.append(data['coe']['total'])
    if 'repair' in data:
        datasets.append('Repair\nTasks')
        counts.append(data['repair']['total'])
    
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(datasets, counts, color=['#2E86AB', '#A23B72', '#F18F01'][:len(datasets)])
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height):,}',
                ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    ax.set_ylabel('Number of Examples', fontweight='bold')
    ax.set_title('Dataset Size Comparison', fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Use log scale if there's large variation
    if max(counts) / min(counts) > 10:
        ax.set_yscale('log')
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/dataset_comparison.png', format='png', dpi=300)
    plt.savefig(f'{output_dir}/dataset_comparison.pdf', format='pdf')
    print(f"Saved: {output_dir}/dataset_comparison.png and .pdf")
    plt.close()

def plot_test_coverage(data, output_dir='reports'):
    """Plot test coverage statistics."""
    if 'mbpp' not in data:
        return
    
    test_counts = data['mbpp']['test_counts']
    
    fig, ax = plt.subplots(figsize=(8, 5))
    unique, counts = np.unique(test_counts, return_counts=True)
    bars = ax.bar(unique.astype(str), counts, color='#2E86AB', edgecolor='black', alpha=0.7)
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontweight='bold')
    
    ax.set_xlabel('Number of Tests per Task', fontweight='bold')
    ax.set_ylabel('Number of Tasks', fontweight='bold')
    ax.set_title('Test Coverage Distribution (MBPP Dataset)', fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/test_coverage.png', format='png', dpi=300)
    plt.savefig(f'{output_dir}/test_coverage.pdf', format='pdf')
    print(f"Saved: {output_dir}/test_coverage.png and .pdf")
    plt.close()

def main():
    print("=" * 80)
    print("GENERATING PUBLICATION-QUALITY GRAPHS")
    print("=" * 80)
    print()
    
    # Load data
    print("Loading data...")
    data = load_data()
    
    # Generate all graphs
    print("\nGenerating graphs...")
    plot_action_distribution(data)
    plot_action_pie_chart(data)
    plot_corruption_distribution(data)
    plot_code_length_distribution(data)
    plot_trace_length_distribution(data)
    plot_dataset_comparison(data)
    plot_test_coverage(data)
    
    print("\n" + "=" * 80)
    print("All graphs generated successfully!")
    print("=" * 80)
    print("\nGraphs saved in 'reports/' directory:")
    print("  - action_distribution.png/pdf")
    print("  - action_pie_chart.png/pdf")
    print("  - corruption_distribution.png/pdf")
    print("  - code_length_distribution.png/pdf")
    print("  - trace_length_distribution.png/pdf")
    print("  - dataset_comparison.png/pdf")
    print("  - test_coverage.png/pdf")
    print("\nAll graphs are 300 DPI and ready for publication!")

if __name__ == "__main__":
    main()

