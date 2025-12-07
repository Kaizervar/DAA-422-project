# src/dataset_builder.py
"""
Construct the 'repair' dataset used for RL stage.
Two modes:
- LM generation mode: sample N solutions using a provided LM and keep failing ones (paper approach).
- Synthetic fallback: produce corruptions by random edits from ground-truth (faster).
Output: newline JSON with fields:
- prompt
- init_code (list of lines)
- tests
- ground_truth_code (string)
"""
import json, os, argparse, random, time
from src.corruptor import delete_line, add_line, replace_line, typo_word

def sample_with_model(model_name, examples, out_path, per_task=100, keep_max=20, temp=0.8, seed=42):
    from transformers import AutoTokenizer, AutoModelForCausalLM
    random.seed(seed)
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name).cuda()
    model.eval()

    total = 0
    with open(out_path, "w") as out:
        for ex in examples:
            desc = ex.get("text", "")
            gt = ex.get("code", "")
            tests = ex.get("test_list", ex.get("tests", []))
            prompt = f"# {desc}\n# Provide a python solution\n"
            candidates = set()
            tries = 0
            while len(candidates) < per_task and tries < per_task * 2:
                tries += 1
                input_ids = tok(prompt, return_tensors="pt").input_ids.cuda()
                outputs = model.generate(input_ids, do_sample=True, temperature=temp, max_new_tokens=256)
                out_code = tok.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)
                out_code = out_code.strip()
                if out_code and out_code not in candidates:
                    candidates.add(out_code)
            # now filter those that fail tests (we'll run tests by naive exec)
            failed = []
            for cand in candidates:
                # run tests simply: exec candidate then tests
                g = {}
                try:
                    exec(cand, g, g)
                    ok = True
                    for t in tests:
                        try:
                            exec(t, g, g)
                        except:
                            ok = False
                            break
                    if not ok:
                        failed.append(cand)
                except:
                    failed.append(cand)
            # keep at most keep_max failing unique solutions
            kept = failed[:keep_max]
            for k in kept:
                rec = {"prompt": desc, "init_code": k.splitlines(), "tests": tests, "ground_truth": gt}
                out.write(json.dumps(rec) + "\n")
                total += 1
    print(f"Wrote {total} repair tasks to {out_path}")

def synthetic_repair_dataset(examples, out_path, per_task=5, seed=42):
    random.seed(seed)
    total = 0
    with open(out_path, "w") as out:
        for ex in examples:
            desc = ex.get("text", "")
            gt = ex.get("code", "")
            clean_lines = [ln for ln in gt.splitlines()]
            tests = ex.get("test_list", ex.get("tests", []))
            # generate per_task corrupt initial solutions by applying more corruptions than CoE demos
            for _ in range(per_task):
                code = clean_lines[:]
                c = random.randint(5, 20)  # more corrupted
                for _ in range(c):
                    op = random.choice(["delete", "add", "replace", "typo"])
                    if op == "delete":
                        code = delete_line(code)
                    elif op == "add":
                        code = add_line(code, clean_lines)
                    elif op == "replace":
                        code = replace_line(code, clean_lines)
                    elif op == "typo":
                        code = typo_word(code)
                rec = {"prompt": desc, "init_code": code, "tests": tests, "ground_truth": gt}
                out.write(json.dumps(rec) + "\n")
                total += 1
    print(f"Wrote {total} synthetic repair tasks to {out_path}")

def main(args):
    # load MBPP
    with open(args.mbpp_path) as f:
        examples = [json.loads(l) for l in f]
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, args.output_name)

    if args.mode == "lm":
        print("Sampling candidate solutions using LM. Requires GPU and model availability.")
        sample_with_model(args.model_name, examples, out_path, per_task=args.per_task,
                          keep_max=args.keep_max, temp=args.temperature)
    else:
        synthetic_repair_dataset(examples, out_path, per_task=args.per_task)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mbpp-path", required=True, help="mbpp jsonl path")
    p.add_argument("--output-dir", default="data/repair_tasks", help="output dir")
    p.add_argument("--output-name", default="repair_train.jsonl", help="output file")
    p.add_argument("--mode", choices=["lm", "synthetic"], default="synthetic")
    p.add_argument("--model-name", default="text-davinci-003", help="model name for LM sampling (HF)")
    p.add_argument("--per-task", type=int, default=100, help="candidates per task (lm) or per-task outputs (synthetic)")
    p.add_argument("--keep-max", type=int, default=20, help="keep at most this many failing candidates per task (lm mode)")
    p.add_argument("--temperature", type=float, default=0.8)
    args = p.parse_args()
    main(args)