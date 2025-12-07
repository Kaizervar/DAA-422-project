# src/rl_train.py
"""
On-policy RL training using a GRPO-like per-turn normalization.
This version is fully corrected to ensure:
- No float leakage
- No loss_total without grad
- No crashes when action is empty
- Stable gradient flow
"""

import json, os, argparse, random, math, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from torch.optim import AdamW
from src.env import CoEEnv

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# =====================================================================
# Compute log probability of ACTION tokens (teacher-forcing)
# =====================================================================
def compute_logprob(model, tokenizer, prompt, action_text):
    model.eval()
    with torch.no_grad():
        enc = tokenizer(prompt, return_tensors="pt").to(DEVICE)
        act_enc = tokenizer(action_text, return_tensors="pt", add_special_tokens=False).to(DEVICE)

        input_ids = torch.cat([enc["input_ids"], act_enc["input_ids"]], dim=1)
        attn = torch.ones_like(input_ids).to(DEVICE)

        outputs = model(input_ids, attention_mask=attn)
        logits = outputs.logits
        logps = torch.nn.functional.log_softmax(logits, dim=-1)

        prefix_len = enc["input_ids"].shape[1]
        act_len = act_enc["input_ids"].shape[1]

        token_logps = []
        for i in range(act_len):
            pos = prefix_len + i
            tid = input_ids[0, pos]
            token_logps.append(logps[0, pos-1, tid].item())

        return sum(token_logps), act_len


# =====================================================================
# Sample an action
# =====================================================================
def sample_action(model, tokenizer, prompt, max_new_tokens=32, temp=0.7):
    model.eval()
    enc = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    gen = model.generate(
        **enc,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=temp
    )
    out = gen[0][enc["input_ids"].shape[1]:]
    return tokenizer.decode(out, skip_special_tokens=True).strip()


# =====================================================================
# Rollout one trajectory
# =====================================================================
def rollout_one(model, tokenizer, init_code_lines, tests, max_turns=10, temp=0.7):
    env = CoEEnv(init_code_lines, tests)
    traj = []

    for t in range(max_turns):
        prompt = env.state.render() + "\n### "
        action = sample_action(model, tokenizer, prompt, max_new_tokens=32, temp=temp)
        action = action.splitlines()[0] if action else "EXIT"

        logp, alen = compute_logprob(model, tokenizer, prompt, action)
        before = env.state.feedback
        new_state = env.apply(action)

        reward = 0.0
        if new_state.feedback == "" and before != "":
            reward = 1.0

        if not action.startswith(("DELL", "ADDL", "REPL", "REPW", "EXIT")):
            reward -= 0.5

        traj.append({
            "prompt": prompt,
            "action": action,
            "logp": logp,
            "reward": reward
        })

        if action.startswith("EXIT"):
            break

    if env.state.feedback == "":
        if len(traj) == 0 or not traj[-1]["action"].startswith("EXIT"):
            traj[-1]["reward"] -= 0.5

    return traj


# =====================================================================
# Return + Advantage computation (per-turn normalization)
# =====================================================================
def compute_returns_and_advantages(group_trajs, gamma=1.0):
    max_T = max(len(t) for t in group_trajs)

    returns = []
    for traj in group_trajs:
        R = []
        future = 0.0
        for step in reversed(traj):
            future = step["reward"] + gamma * future
            R.insert(0, future)
        returns.append(R)

    advantages = []
    for _ in group_trajs:
        advantages.append([])

    for t in range(max_T):
        vals = []
        idxs = []
        for i, R in enumerate(returns):
            if t < len(R):
                vals.append(R[t])
                idxs.append(i)

        if len(vals) >= 2:
            mu = sum(vals) / len(vals)
            var = sum((v - mu)**2 for v in vals) / (len(vals) - 1)
            sigma = math.sqrt(max(var, 1e-6))
        elif len(vals) == 1:
            mu = vals[0]
            sigma = 1.0
        else:
            mu = 0.0
            sigma = 1.0

        for j, idx in enumerate(idxs):
            advantages[idx].append((vals[j] - mu) / sigma)

    flat_steps = []
    for i, traj in enumerate(group_trajs):
        for t, step in enumerate(traj):
            flat_steps.append({
                "prompt": step["prompt"],
                "action": step["action"],
                "old_logp": step["logp"],
                "adv": advantages[i][t] if t < len(advantages[i]) else 0.0
            })

    return flat_steps


# =====================================================================
# TRAIN LOOP (FULLY CORRECTED)
# =====================================================================
def train_loop(args):
    with open(args.repair_jsonl) as f:
        tasks = [json.loads(l) for l in f]

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForCausalLM.from_pretrained(args.model_name).to(DEVICE)

    if args.lora_adapter and os.path.isdir(args.lora_adapter):
        model = PeftModel.from_pretrained(model, args.lora_adapter).to(DEVICE)

    optimizer = AdamW(model.parameters(), lr=args.lr)

    global_step = 0

    for epoch in range(args.epochs):
        random.shuffle(tasks)

        for g_start in range(0, len(tasks), args.group_size):
            group = tasks[g_start:g_start+args.group_size]
            if len(group) < args.group_size:
                break

            # Sample trajectories
            group_trajs = []
            for task in group:
                init_code = task.get("init_code", task.get("init_code_lines", []))
                tests = task.get("tests", [])
                traj = rollout_one(model, tokenizer, init_code, tests,
                                   max_turns=args.max_turns, temp=args.sampling_temp)
                group_trajs.append(traj)

            # Compute steps with advantages
            steps = compute_returns_and_advantages(group_trajs)

            model.train()
            batch_loss_val = 0.0

            for i in range(0, len(steps), args.batch_size):
                batch = steps[i:i+args.batch_size]

                optimizer.zero_grad()
                loss_total = torch.zeros((), device=DEVICE)  # differentiable accumulator
                contrib = 0

                for step in batch:
                    prompt = step["prompt"]
                    action = step["action"]

                    enc_prompt = tokenizer(prompt, return_tensors="pt").to(DEVICE)
                    enc_action = tokenizer(action, return_tensors="pt", add_special_tokens=False).to(DEVICE)
                    input_ids = torch.cat([enc_prompt["input_ids"], enc_action["input_ids"]], dim=1)
                    attn = torch.ones_like(input_ids).to(DEVICE)

                    outputs = model(input_ids, attention_mask=attn)
                    logits = outputs.logits
                    logps = torch.nn.functional.log_softmax(logits, dim=-1)

                    prefix_len = enc_prompt["input_ids"].shape[1]
                    act_len = enc_action["input_ids"].shape[1]

                    # Skip EMPTY actions (no grad possible)
                    if act_len == 0:
                        continue

                    # Compute differentiable logprob
                    new_logp = torch.zeros((), device=DEVICE, dtype=logps.dtype)
                    for k in range(act_len):
                        pos = prefix_len + k
                        tid = input_ids[0, pos]
                        new_logp = new_logp + logps[0, pos-1, tid]

                    old_logp = torch.tensor(step["old_logp"], device=DEVICE, dtype=new_logp.dtype)
                    adv = torch.tensor(step["adv"], device=DEVICE, dtype=new_logp.dtype)

                    ratio = torch.exp(new_logp - old_logp)
                    clipped = torch.clamp(ratio, 1.0 - args.clip_eps, 1.0 + args.clip_eps)
                    loss = -torch.mean(torch.min(ratio * adv, clipped * adv))

                    loss_total = loss_total + loss
                    contrib += 1

                if contrib == 0:
                    continue  # skip useless minibatch

                loss_total = loss_total / contrib
                loss_total.backward()
                optimizer.step()

                batch_loss_val += float(loss_total.item())

            global_step += 1

            if global_step % args.log_interval == 0:
                print(f"[Step {global_step}] epoch={epoch} group={g_start}, loss={batch_loss_val:.4f}")

            if global_step % args.save_interval == 0:
                ckpt_dir = os.path.join(args.output_dir, f"ckpt_{global_step}")
                os.makedirs(ckpt_dir, exist_ok=True)
                model.save_pretrained(ckpt_dir)
                print(f"Saved checkpoint to {ckpt_dir}")


# =====================================================================
# MAIN
# =====================================================================
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repair-jsonl", required=True)
    p.add_argument("--model-name", default="gpt2")
    p.add_argument("--lora-adapter", default=None)
    p.add_argument("--output-dir", default="experiments/rl")
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--group-size", type=int, default=4)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--max-turns", type=int, default=10)
    p.add_argument("--sampling-temp", type=float, default=0.7)
    p.add_argument("--lr", type=float, default=1e-5)
    p.add_argument("--clip-eps", type=float, default=0.2)
    p.add_argument("--log-interval", type=int, default=10)
    p.add_argument("--save-interval", type=int, default=50)

    args = p.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)


    train_loop(args)


if __name__ == "__main__":
    main()



