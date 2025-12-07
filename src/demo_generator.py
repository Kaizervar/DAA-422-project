"""
Generate Chain-of-Edits (CoE) synthetic demonstrations.
Outputs newline-delimited JSON with fields:
- prompt: task description + DSL instructions + tests
- trace: list of alternating states and actions (strings); final element "EXIT"
- init_code_lines: list of initial (corrupted) lines
- tests: list of test strings
"""
import json, random, argparse, os
from src.corruptor import delete_line, add_line, replace_line, typo_word
from src.env import CoEEnv

CORRUPTION_TYPES = ["delete", "add", "replace", "typo"]

def invert_action_for_op(op_type, clean_lines, current_lines):
    """
    Return a DSL action (string) that attempts to revert a corruption op.
    We approximate the inverse using the original clean_lines when available.
    """
    # We'll try to restore by matching a line from clean_lines not present in current_lines.
    # If not possible, fallback to simple heuristics.
    if op_type == "delete":
        # find first line in clean_lines not in current_lines -> insert at its index
        for i, ln in enumerate(clean_lines):
            if i >= len(current_lines) or current_lines[i] != ln:
                # ADDL <line_index+1> >>><line>
                return f"ADDL {i+1} >>>{ln}"
        # fallback: add at end
        return f"ADDL {len(current_lines)+1} >>>{clean_lines[-1]}"
    if op_type == "add":
        # remove a line that is not in clean_lines (find index)
        for i, ln in enumerate(current_lines):
            if i >= len(clean_lines) or ln != clean_lines[i]:
                return f"DELL {i+1}"
        # fallback: delete last
        return f"DELL {len(current_lines)}"
    if op_type == "replace" or op_type == "typo":
        # replace the first differing line with the clean one
        for i, ln in enumerate(clean_lines):
            if i >= len(current_lines) or current_lines[i] != ln:
                return f"REPL {i+1} >>>{ln}"
        # fallback: replace line 1
        return f"REPL 1 >>>{clean_lines[0]}"
    return "EXIT"

def make_prefix_prompt(task_description, tests):
    header = (
        "You are an expert Python programmer whose goal is to fix all mistakes in a code snippet.\n"
        "You may interact with the code snippet only by applying the provided DSL commands. Valid DSL\n"
        "command templates are:\n"
        "`### DELL <line_number>` to delete the line at the specified line number.\n"
        "`### ADDL <line_number> >>><line_content>` to add a line at the specified line number.\n"
        "`### REPL <line_number> >>><line_content>` to replace the line at the specified line number.\n"
        "`### REPW <line_number> >>><string_to_replace> >>><string_to_insert>` to replace string occurrences.\n"
    )
    tests_text = "\n".join(tests)
    prompt = f"{header}\nHere is your task: {task_description}\nYour code should pass these tests:\n{tests_text}\nBelow is an initial malfunctioning code snippet to fix:\n"
    return prompt

def generate_demo_for_example(clean_code_lines, tests, donor_pool, num_corruptions):
    # 1) produce corrupted code and list of applied corruptions
    code = clean_code_lines[:]
    ops = []
    for _ in range(num_corruptions):
        c = random.choice(CORRUPTION_TYPES)
        if c == "delete":
            code = delete_line(code); ops.append("delete")
        elif c == "add":
            code = add_line(code, donor_pool); ops.append("add")
        elif c == "replace":
            code = replace_line(code, donor_pool); ops.append("replace")
        elif c == "typo":
            code = typo_word(code); ops.append("typo")
    # instantiate environment at corrupted state
    env = CoEEnv(code, tests)
    trace = []
    # initial state as string
    trace.append(env.state.render())
    # reverse operations in reverse order by producing actions derived from clean_lines
    current_lines = env.state.code_lines[:]
    for op in reversed(ops):
        action = invert_action_for_op(op, clean_code_lines, current_lines)
        trace.append(action)
        state = env.apply(action)
        trace.append(state.render())
        current_lines = state.code_lines[:]
    trace.append("EXIT")
    return trace, code

def main(args):
    # load MBPP JSONL
    with open(args.mbpp_path, "r") as f:
        examples = [json.loads(l) for l in f]
    # donor pool: lines drawn from all ground-truth solutions to increase realism
    donor_pool = []
    for ex in examples:
        src = ex.get("code", "")
        lines = [ln for ln in src.splitlines() if ln.strip() != ""]
        donor_pool.extend(lines)
    random.shuffle(donor_pool)

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, args.output_name)
    total = 0
    with open(out_path, "w") as out:
        for ex in examples:
            # MBPP items: 'text' (description), 'code' (ground truth), 'test_list' or 'tests'
            task_desc = ex.get("text", "Implement the function.")
            clean_code = ex.get("code", "")
            if isinstance(clean_code, list):  # some variants
                clean_lines = clean_code
            else:
                clean_lines = [ln for ln in clean_code.splitlines()]
            tests = ex.get("test_list", ex.get("tests", []))
            # produce N demos per MBPP task
            n = args.per_task if args.per_task else 100
            for _ in range(n):
                c = random.randint(1, args.max_corruptions)
                trace, corrupted = generate_demo_for_example(clean_lines, tests, donor_pool, c)
                prefix = make_prefix_prompt(task_desc, tests)
                record = {
                    "prompt": prefix,
                    "trace": trace,
                    "init_code_lines": corrupted,
                    "tests": tests
                }
                out.write(json.dumps(record) + "\n")
                total += 1
                if args.limit and total >= args.limit:
                    break
            if args.limit and total >= args.limit:
                break
    print(f"Wrote {total} demonstrations to {out_path}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mbpp-path", required=True, help="MBPP jsonl path")
    p.add_argument("--output-dir", default="data/coe_demos", help="output dir")
    p.add_argument("--output-name", default="coe_train.jsonl", help="output filename")
    p.add_argument("--per-task", type=int, default=100, help="demos per MBPP task (paper used 100 for train)")
    p.add_argument("--max-corruptions", type=int, default=5, help="max corruptions per demo")
    p.add_argument("--limit", type=int, default=0, help="global demo limit (0 = no limit)")
    args = p.parse_args()
    main(args)