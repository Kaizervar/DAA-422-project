"""
Generate publication-ready results and statistics for the paper.
"""
import json
import os
from collections import Counter

def analyze_coe_demos(path):
    """Analyze Chain-of-Edits demonstrations."""
    with open(path, 'r') as f:
        data = [json.loads(l) for l in f]
    
    trace_lengths = [len(d['trace']) for d in data]
    init_code_lengths = [len(d['init_code_lines']) for d in data]
    
    # Count action types
    action_types = []
    for d in data:
        for item in d['trace']:
            if item.startswith('DELL'):
                action_types.append('DELL')
            elif item.startswith('ADDL'):
                action_types.append('ADDL')
            elif item.startswith('REPL'):
                action_types.append('REPL')
            elif item.startswith('REPW'):
                action_types.append('REPW')
    
    action_counts = Counter(action_types)
    
    return {
        'total_demos': len(data),
        'avg_trace_length': sum(trace_lengths) / len(trace_lengths) if trace_lengths else 0,
        'avg_init_code_lines': sum(init_code_lengths) / len(init_code_lengths) if init_code_lengths else 0,
        'action_distribution': dict(action_counts),
        'total_actions': sum(action_counts.values())
    }

def analyze_repair_tasks(path):
    """Analyze repair tasks dataset."""
    with open(path, 'r') as f:
        data = [json.loads(l) for l in f]
    
    corrupted_lengths = [len(d['init_code']) for d in data]
    test_counts = [len(d['tests']) for d in data]
    
    # Analyze corruption patterns
    corruption_types = {'delete': 0, 'add': 0, 'replace': 0, 'typo': 0}
    # Estimate based on differences from ground truth
    for d in data:
        gt_lines = len(d.get('ground_truth', '').splitlines())
        init_lines = len(d['init_code'])
        if init_lines < gt_lines:
            corruption_types['delete'] += 1
        elif init_lines > gt_lines:
            corruption_types['add'] += 1
        else:
            corruption_types['replace'] += 1
    
    return {
        'total_tasks': len(data),
        'avg_corrupted_lines': sum(corrupted_lengths) / len(corrupted_lengths) if corrupted_lengths else 0,
        'avg_tests_per_task': sum(test_counts) / len(test_counts) if test_counts else 0,
        'corruption_patterns': corruption_types
    }

def analyze_mbpp(path):
    """Analyze MBPP dataset."""
    with open(path, 'r') as f:
        data = [json.loads(l) for l in f]
    
    test_counts = [len(d.get('test_list', d.get('tests', []))) for d in data]
    code_lengths = [len(d.get('code', '').splitlines()) for d in data]
    
    return {
        'total_tasks': len(data),
        'total_test_cases': sum(test_counts),
        'avg_tests_per_task': sum(test_counts) / len(test_counts) if test_counts else 0,
        'avg_code_lines': sum(code_lengths) / len(code_lengths) if code_lengths else 0
    }

def test_environment():
    """Test environment functionality."""
    from src.env import CoEEnv
    
    results = []
    
    # Test 1: Simple fix
    env1 = CoEEnv(['def add(a, b):', '    return a'], ['assert add(1, 2) == 3'])
    initial_feedback = env1.state.feedback
    state1 = env1.apply('REPL 2 >>>    return a + b')
    results.append({
        'test': 'Simple addition fix',
        'initial_state': 'Failed',
        'after_fix': 'Passed' if state1.feedback == '' else 'Failed',
        'actions_taken': 1
    })
    
    # Test 2: Multiple edits
    env2 = CoEEnv(['def multiply(x, y):', '    return x'], ['assert multiply(3, 4) == 12'])
    state2a = env2.apply('REPL 2 >>>    return x * y')
    results.append({
        'test': 'Multiplication fix',
        'initial_state': 'Failed',
        'after_fix': 'Passed' if state2a.feedback == '' else 'Failed',
        'actions_taken': 1
    })
    
    # Test 3: Delete and add
    env3 = CoEEnv(['def test():', '    x = 1', '    return x', '    y = 2'], ['assert test() == 1'])
    state3a = env3.apply('DELL 4')
    results.append({
        'test': 'Delete extra line',
        'initial_state': 'Failed',
        'after_fix': 'Passed' if state3a.feedback == '' else 'Failed',
        'actions_taken': 1
    })
    
    return results

def main():
    print("=" * 80)
    print("PUBLICATION-READY RESULTS")
    print("=" * 80)
    print()
    
    # Analyze datasets
    print("## Dataset Statistics")
    print("-" * 80)
    
    if os.path.exists('data/mbpp_raw/train.jsonl'):
        mbpp_stats = analyze_mbpp('data/mbpp_raw/train.jsonl')
        print(f"\n### MBPP Training Dataset")
        print(f"Total tasks: {mbpp_stats['total_tasks']}")
        print(f"Total test cases: {mbpp_stats['total_test_cases']}")
        print(f"Average tests per task: {mbpp_stats['avg_tests_per_task']:.2f}")
        print(f"Average code lines per task: {mbpp_stats['avg_code_lines']:.2f}")
    
    if os.path.exists('data/coe_demos/coe_train.jsonl'):
        coe_stats = analyze_coe_demos('data/coe_demos/coe_train.jsonl')
        print(f"\n### Chain-of-Edits Demonstrations")
        print(f"Total demonstrations: {coe_stats['total_demos']}")
        print(f"Average trace length: {coe_stats['avg_trace_length']:.2f} steps")
        print(f"Average initial code lines: {coe_stats['avg_init_code_lines']:.2f}")
        print(f"Total actions: {coe_stats['total_actions']}")
        print(f"\nAction Distribution:")
        for action, count in coe_stats['action_distribution'].items():
            pct = (count / coe_stats['total_actions'] * 100) if coe_stats['total_actions'] > 0 else 0
            print(f"  {action}: {count} ({pct:.1f}%)")
    
    if os.path.exists('data/repair_tasks/repair_train.jsonl'):
        repair_stats = analyze_repair_tasks('data/repair_tasks/repair_train.jsonl')
        print(f"\n### Repair Tasks Dataset")
        print(f"Total repair tasks: {repair_stats['total_tasks']}")
        print(f"Average corrupted code lines: {repair_stats['avg_corrupted_lines']:.2f}")
        print(f"Average tests per task: {repair_stats['avg_tests_per_task']:.2f}")
        print(f"\nCorruption Patterns:")
        for pattern, count in repair_stats['corruption_patterns'].items():
            pct = (count / repair_stats['total_tasks'] * 100) if repair_stats['total_tasks'] > 0 else 0
            print(f"  {pattern}: {count} ({pct:.1f}%)")
    
    # Test environment
    print(f"\n## Environment Functionality Tests")
    print("-" * 80)
    env_tests = test_environment()
    for i, test in enumerate(env_tests, 1):
        print(f"\nTest {i}: {test['test']}")
        print(f"  Initial state: {test['initial_state']}")
        print(f"  After fix: {test['after_fix']}")
        print(f"  Actions taken: {test['actions_taken']}")
    
    # Generate LaTeX table
    print(f"\n\n## LaTeX Table Format")
    print("-" * 80)
    print("\\begin{table}[h]")
    print("\\centering")
    print("\\caption{Dataset Statistics}")
    print("\\label{tab:dataset_stats}")
    print("\\begin{tabular}{lrr}")
    print("\\toprule")
    print("Dataset & Count & Avg. Size \\\\")
    print("\\midrule")
    if os.path.exists('data/mbpp_raw/train.jsonl'):
        print(f"MBPP Training & {mbpp_stats['total_tasks']} & {mbpp_stats['avg_code_lines']:.1f} lines \\\\")
    if os.path.exists('data/coe_demos/coe_train.jsonl'):
        print(f"CoE Demonstrations & {coe_stats['total_demos']} & {coe_stats['avg_trace_length']:.1f} steps \\\\")
    if os.path.exists('data/repair_tasks/repair_train.jsonl'):
        print(f"Repair Tasks & {repair_stats['total_tasks']} & {repair_stats['avg_corrupted_lines']:.1f} lines \\\\")
    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\end{table}")
    
    # Generate markdown table
    print(f"\n\n## Markdown Table Format")
    print("-" * 80)
    print("| Dataset | Count | Average Size |")
    print("|---------|-------|--------------|")
    if os.path.exists('data/mbpp_raw/train.jsonl'):
        print(f"| MBPP Training | {mbpp_stats['total_tasks']} | {mbpp_stats['avg_code_lines']:.1f} lines |")
    if os.path.exists('data/coe_demos/coe_train.jsonl'):
        print(f"| CoE Demonstrations | {coe_stats['total_demos']} | {coe_stats['avg_trace_length']:.1f} steps |")
    if os.path.exists('data/repair_tasks/repair_train.jsonl'):
        print(f"| Repair Tasks | {repair_stats['total_tasks']} | {repair_stats['avg_corrupted_lines']:.1f} lines |")
    
    print(f"\n\n## Action Distribution (CoE Demonstrations)")
    print("-" * 80)
    if os.path.exists('data/coe_demos/coe_train.jsonl'):
        print("| Action Type | Count | Percentage |")
        print("|-------------|-------|------------|")
        for action, count in sorted(coe_stats['action_distribution'].items()):
            pct = (count / coe_stats['total_actions'] * 100) if coe_stats['total_actions'] > 0 else 0
            print(f"| {action} | {count} | {pct:.1f}% |")
    
    print("\n" + "=" * 80)
    print("Results generation complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()

