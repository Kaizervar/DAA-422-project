# src/eval.py
"""
Evaluation script computing pass@1 (greedy) and pass@k (we implement pass@4 sampling).
Input: repair test jsonl with fields: prompt, init_code (list), tests.
For models trained on CoE traces, we attach the text editor env and perform up to max_turns turns,
appending state to context and decoding predicted action each turn. For pass@1 we use greedy
decoding (deterministic). For pass@4 we sample 4 trajectories using temp=0.2 and consider success
if any trajectory finishes with all tests passing.
"""
import json, argparse, os, math
from transformers import AutoTokenizer, AutoModelForCausalLM
from src.env import CoEEnv
import torch

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def run_one_episode_greedy(model, tokenizer, init_code_lines, tests, max_turns=10):
    env = CoEEnv(init_code_lines, tests)
    for t in range(max_turns):
        prompt = env.state.render() + "\n### "
        enc = tokenizer(prompt, return_tensors="pt").to(DEVICE)
        gen = model.generate(**enc, max_new_tokens=32, do_sample=False)  # greedy
        action = tokenizer.decode(gen[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        action = action.splitlines()[0] if action else "EXIT"
        env.apply(action)
        if env.state.feedback == "":
            # solved
            return True
        if action.startswith("EXIT"):
            break
    return env.state.feedback == ""

def run_one_episode_sample(model, tokenizer, init_code_lines, tests, max_turns=10, temp=0.2):
    env = CoEEnv(init_code_lines, tests)
    for t in range(max_turns):
        prompt = env.state.render() + "\n### "
        enc = tokenizer(prompt, return_tensors="pt").to(DEVICE)
        gen = model.generate(**enc, max_new_tokens=32, do_sample=True, temperature=temp)
        action = tokenizer.decode(gen[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        action = action.splitlines()[0] if action else "EXIT"
        env.apply(action)
        if env.state.feedback == "":
            return True
        if action.startswith("EXIT"):
            break
    return env.state.feedback == ""

def evaluate(model_name, data_path, max_turns=10, k=4, device=DEVICE):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
    # if adapter exists under model_name (peft), it's fine to pass in that path
    # load data
    with open(data_path) as f:
        tasks = [json.loads(l) for l in f]
    pass1 = 0
    passk = 0
    for t in tasks:
        init_code = t.get("init_code", t.get("init_code_lines", []))
        tests = t.get("tests", t.get("test_list", []))
        try:
            ok1 = run_one_episode_greedy(model, tokenizer, init_code, tests, max_turns=max_turns)
            pass1 += 1 if ok1 else 0
            # pass@k: sample k times
            ok_any = False
            for _ in range(k):
                ok = run_one_episode_sample(model, tokenizer, init_code, tests, max_turns=max_turns, temp=0.2)
                if ok:
                    ok_any = True
                    break
            passk += 1 if ok_any else 0
        except Exception as e:
            # in case of runtime error treat as fail
            pass
    n = len(tasks)
    print(f"Evaluated {n} tasks. pass@1 = {pass1}/{n} = {pass1/n*100:.2f}% , pass@{k} = {passk}/{n} = {passk/n*100:.2f}%")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model-name", required=True)
    p.add_argument("--data", required=True, help="repair test jsonl")
    p.add_argument("--max-turns", type=int, default=10)
    p.add_argument("--k", type=int, default=4)
    args = p.parse_args()
    evaluate(args.model_name, args.data, max_turns=args.max_turns, k=args.k)
