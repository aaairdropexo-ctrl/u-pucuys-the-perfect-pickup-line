#!/usr/bin/env python3
"""Resume the pickup-line tournament after a judge-call timeout.

Reads completed ordered pairs from tournament.log, runs only the missing
ones (same judge, same prompt, both directions), appends results to the log
and writes tournament.json standings. A call that times out twice is
recorded as failed and skipped instead of aborting the whole run.
"""
import json
import re
import subprocess
import sys
import time

from tournament import CANDIDATES, HELPER, MODEL, PROMPT

LOG = "/home/hatch/workspace/makefun/u-pucuys-the-perfect-pickup-line-entry/tournament.log"
OUT = "/home/hatch/workspace/makefun/u-pucuys-the-perfect-pickup-line-entry/tournament.json"

PAIR_RE = re.compile(r"^([A-E]) vs ([A-E]): winner=([A-E]|None) margin=([0-9])")


def judge(a_key, b_key):
    prompt = PROMPT.format(a=CANDIDATES[a_key], b=CANDIDATES[b_key])
    for attempt in (1, 2):
        try:
            r = subprocess.run(
                ["python3", HELPER, "chat", MODEL, prompt, "2500"],
                capture_output=True, text=True, timeout=180,
            )
        except subprocess.TimeoutExpired:
            print(f"{a_key} vs {b_key}: attempt {attempt} TIMEOUT", flush=True)
            time.sleep(5)
            continue
        out = r.stdout + r.stderr
        content = None
        try:
            data = json.loads(r.stdout)
            content = data["choices"][0]["message"]["content"]
        except Exception:
            pass
        if not content:
            m = re.search(r'"content":\s*"((?:[^"\\]|\\.)*)"', out)
            if m:
                try:
                    content = json.loads('"' + m.group(1) + '"')
                except Exception:
                    content = None
        if content:
            wm = re.search(r"Winner:\s*([AB])", content)
            mm = re.search(r"Margin:\s*([1-5])", content)
            rm = re.search(r"Reason:\s*(.+)", content)
            if wm and mm:
                return {
                    "a": a_key, "b": b_key,
                    "winner_side": wm.group(1),
                    "winner": a_key if wm.group(1) == "A" else b_key,
                    "margin": int(mm.group(1)),
                    "reason": rm.group(1).strip()[:200] if rm else "",
                }
        if attempt == 1:
            time.sleep(5)
    return {"a": a_key, "b": b_key, "winner": None, "margin": 0,
            "reason": "CALL FAILED"}


def main():
    done = {}
    with open(LOG) as f:
        for line in f:
            m = PAIR_RE.match(line.strip())
            if m:
                done[(m.group(1), m.group(2))] = {
                    "a": m.group(1), "b": m.group(2),
                    "winner": None if m.group(3) == "None" else m.group(3),
                    "margin": int(m.group(4)),
                }
    keys = list(CANDIDATES)
    missing = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            for a_key, b_key in ((keys[i], keys[j]), (keys[j], keys[i])):
                if (a_key, b_key) not in done:
                    missing.append((a_key, b_key))
    print(f"completed={len(done)} missing={len(missing)}: {missing}", flush=True)
    results = list(done.values())
    with open(LOG, "a") as log:
        for a_key, b_key in missing:
            res = judge(a_key, b_key)
            results.append(res)
            line = f"{a_key} vs {b_key}: winner={res['winner']} margin={res['margin']} :: {res['reason']}"
            print(line, flush=True)
            log.write(line + "\n")
            log.flush()
            time.sleep(2)
    wins = {k: 0 for k in keys}
    margins = {k: 0 for k in keys}
    games = {k: 0 for k in keys}
    for r in results:
        if r["winner"]:
            wins[r["winner"]] += 1
            margins[r["winner"]] += r["margin"]
            loser = r["b"] if r["winner"] == r["a"] else r["a"]
            margins[loser] -= r["margin"]
        games[r["a"]] += 1
        games[r["b"]] += 1
    print("\n=== STANDINGS (wins out of 8 calls, margin total) ===", flush=True)
    for k in sorted(keys, key=lambda k: (-wins[k], -margins[k])):
        print(f"{k}: {wins[k]}W / {games[k]} calls, margin total {margins[k]} :: {CANDIDATES[k]}", flush=True)
    with open(OUT, "w") as f:
        json.dump({"results": results, "wins": wins, "margins": margins}, f, indent=2)


if __name__ == "__main__":
    main()
