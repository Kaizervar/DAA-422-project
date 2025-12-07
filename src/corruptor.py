import random

def delete_line(code_lines):
    if not code_lines:
        return code_lines
    idx = random.randrange(len(code_lines))
    return code_lines[:idx] + code_lines[idx+1:]

def add_line(code_lines, donor_lines):
    idx = random.randrange(len(code_lines) + 1)
    line = random.choice(donor_lines)
    return code_lines[:idx] + [line] + code_lines[idx:]

def replace_line(code_lines, donor_lines):
    if not code_lines:
        return code_lines
    idx = random.randrange(len(code_lines))
    line = random.choice(donor_lines)
    new = code_lines[:]
    new[idx] = line
    return new

def typo_word(code_lines):
    if not code_lines:
        return code_lines
    idx = random.randrange(len(code_lines))
    words = code_lines[idx].split()
    if not words:
        return code_lines
    wi = random.randrange(len(words))
    w = words[wi]
    if len(w) > 1:
        pos = random.randrange(len(w))
        w2 = w[:pos] + random.choice('abcdefghijklmnopqrstuvwxyz') + w[pos+1:]
    else:
        w2 = w + random.choice('abcdefghijklmnopqrstuvwxyz')
    words[wi] = w2
    new_line = " ".join(words)
    new = code_lines[:]
    new[idx] = new_line
    return new







