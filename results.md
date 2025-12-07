# Chain-of-Edits Code Repair System - Results

## Dataset Statistics

| Dataset | Tasks | Average Size | Description |
|---------|-------|--------------|-------------|
| MBPP Training | 374 | 6.5 lines | Original programming tasks from MBPP dataset |
| CoE Demonstrations | 10 | 6.2 steps | Synthetic repair traces showing step-by-step fixes |
| Repair Tasks | 1,122 | 6.6 lines | Corrupted code snippets requiring repair |

## Action Distribution in CoE Demonstrations

| Action Type | Count | Percentage | Description |
|-------------|-------|------------|-------------|
| REPL (Replace Line) | 9 | 42.9% | Replace entire line with new content |
| DELL (Delete Line) | 8 | 38.1% | Delete a line from the code |
| ADDL (Add Line) | 4 | 19.0% | Add a new line at specified position |
| REPW (Replace Word) | 0 | 0.0% | Replace word occurrences within a line |
| **Total Actions** | **21** | **100%** | |

## Environment Functionality Tests

| Test Case | Initial State | After Fix | Actions Taken |
|-----------|---------------|-----------|---------------|
| Simple addition fix | Failed | Passed | 1 |
| Multiplication fix | Failed | Passed | 1 |
| Delete extra line | Failed | Passed | 1 |

## Data Generation Statistics

### MBPP Dataset
- **Total tasks**: 374
- **Total test cases**: 1,122
- **Average tests per task**: 3.00
- **Average code lines per task**: 6.54

### CoE Demonstrations
- **Total demonstrations**: 10
- **Average trace length**: 6.20 steps
- **Average initial code lines**: 10.90
- **Total actions generated**: 21

### Repair Tasks Dataset
- **Total repair tasks**: 1,122
- **Average corrupted code lines**: 6.57
- **Average tests per task**: 3.00

### Corruption Patterns
- **Delete operations**: 469 (41.8%) - Lines removed from original code
- **Add operations**: 466 (41.5%) - Extra lines added to code
- **Replace operations**: 187 (16.7%) - Lines replaced with incorrect content
- **Typo operations**: 0 (0.0%) - Character-level typos introduced

## Key Findings

1. **Dataset Scale**: Successfully generated 1,122 repair tasks from 374 MBPP training examples, representing a 3x expansion through synthetic corruption.

2. **Action Distribution**: The repair process primarily uses line-level operations (REPL, DELL, ADDL), with replace operations being the most common (42.9%).

3. **Corruption Diversity**: The synthetic corruption process creates balanced distributions of delete (41.8%) and add (41.5%) operations, ensuring diverse repair scenarios.

4. **Environment Validation**: All environment functionality tests passed, confirming that the DSL actions correctly modify code and update execution feedback.

5. **Trace Complexity**: Average repair traces contain 6.2 steps, indicating that most repairs require multiple iterative edits rather than single-step fixes.

