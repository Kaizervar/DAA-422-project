# Chain-of-Edits Code Repair System

A research implementation of a code repair system using Chain-of-Edits (CoE) methodology. This system trains models to fix code by applying a sequence of Domain-Specific Language (DSL) commands iteratively.

## 📋 Overview

This project implements a complete pipeline for:
- Generating synthetic code repair demonstrations
- Creating corrupted code datasets for training
- Training models using supervised fine-tuning (SFT) and reinforcement learning (RL)
- Evaluating models on code repair tasks

## 🏗️ Project Structure

```
.
├── src/                    # Source code
│   ├── corruptor.py       # Code corruption utilities
│   ├── dataset_builder.py # Dataset generation
│   ├── demo_generator.py  # CoE demonstration generation
│   ├── env.py            # CoE environment implementation
│   ├── eval.py           # Evaluation scripts
│   ├── rl_train.py       # Reinforcement learning training
│   └── sft_train.py      # Supervised fine-tuning
├── data/                  # Datasets
│   ├── mbpp_raw/         # MBPP source dataset
│   ├── coe_demos/        # Generated CoE demonstrations
│   └── repair_tasks/     # Generated repair tasks
├── experiments/           # Training outputs and checkpoints
└── reports/              # Results and visualizations
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- CUDA-capable GPU (recommended for training)
- Required packages: `transformers`, `torch`, `peft`, `datasets`

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd chain-of-edits-code-repair

# Install dependencies
pip install transformers torch peft datasets
```

### Basic Usage

1. **Generate CoE Demonstrations**
```bash
python src/demo_generator.py \
    --mbpp-path data/mbpp_raw/train.jsonl \
    --output-dir data/coe_demos \
    --per-task 100 \
    --max-corruptions 5
```

2. **Generate Repair Tasks**
```bash
python src/dataset_builder.py \
    --mbpp-path data/mbpp_raw/train.jsonl \
    --mode synthetic \
    --per-task 5 \
    --output-dir data/repair_tasks
```

3. **Train Model (SFT)**
```bash
python src/sft_train.py \
    --demos data/coe_demos/coe_train.jsonl \
    --model-name meta-llama/Llama-3.2-1B \
    --out-dir experiments/sft_llama \
    --epochs 1
```

4. **Evaluate Model**
```bash
python src/eval.py \
    --model-name experiments/sft_llama/lora \
    --data data/repair_tasks/repair_train.jsonl \
    --max-turns 10 \
    --k 4
```

## 📊 Results

### Dataset Statistics

| Dataset | Count | Average Size |
|---------|-------|--------------|
| MBPP Training | 374 | 6.5 lines |
| CoE Demonstrations | 10 | 6.2 steps |
| Repair Tasks | 1,122 | 6.6 lines |

### Action Distribution

- **REPL** (Replace Line): 42.9%
- **DELL** (Delete Line): 38.1%
- **ADDL** (Add Line): 19.0%

### Corruption Patterns

- **Delete**: 41.8%
- **Add**: 41.5%
- **Replace**: 16.7%

See `PAPER_RESULTS_SUMMARY.md` for detailed results and `reports/` for visualizations.

## 🔧 Components

### Code Corruption (`corruptor.py`)
Utilities for corrupting code:
- `delete_line()` - Remove random lines
- `add_line()` - Insert random lines
- `replace_line()` - Replace lines
- `typo_word()` - Introduce typos

### Environment (`env.py`)
Implements the CoE environment:
- `ScratchpadState` - Holds code and feedback
- `DSLExecutor` - Executes code and tests
- `CoEEnv` - Applies DSL actions and updates state

### DSL Actions
- `DELL <line>` - Delete line
- `ADDL <line> >>><content>` - Add line
- `REPL <line> >>><content>` - Replace line
- `REPW <line> >>>old>>>new` - Replace word
- `EXIT` - Terminate

## 📈 Generating Results

### Statistics
```bash
python generate_results.py
```

### Graphs
```bash
python generate_graphs_latex.py
```

Outputs:
- `results.tex` - LaTeX tables
- `results.md` - Markdown tables
- `reports/graphs.tex` - LaTeX graphs
- `reports/graphs.html` - Interactive HTML

## 📝 Citation

If you use this code in your research, please cite:

```bibtex
@software{chain_of_edits_code_repair,
  title = {Chain-of-Edits Code Repair System},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/yourusername/chain-of-edits-code-repair}
}
```

## 📄 License

[Specify your license here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

[Your contact information]

## 🙏 Acknowledgments

- MBPP dataset for providing programming tasks
- Hugging Face for transformers library
- PEFT for efficient fine-tuning

---

*For detailed results and paper-ready materials, see `COMPLETE_RESULTS_PACKAGE.md`*

