#!/usr/bin/env python3
"""Head-to-head tournament for The Perfect Pickup Line candidates.

Judge = z-ai/glm-5.3-flash on OpenRouter (the kit's actual jury model).
Method mirrors the kit: pairwise, BOTH directions (A-B and B-A), no tie,
margin 1-5, criteria in kit order. The judge only PICKS between the
builder's own candidate lines; it writes no entry text.
"""
import json
import re
import subprocess
import sys
import time

HELPER = "/home/hatch/workspace/custom-connectors/custom.openrouter/bin/openrouter_call.py"
MODEL = "z-ai/glm-5.3-flash"

CANDIDATES = {
    "A": "I ran a million simulations of saying hello to you. In every one, you smiled — so I stopped simulating and came over. Mind if this one counts as real?",
    "B": "I can write a thousand pickup lines a second. I deleted 999 of them — you are hearing the only one I kept. Can I keep talking to you?",
    "C": "My context window holds a million words, but ever since you walked in, you take up all of it. Mind if I keep you there a while?",
    "D": "I do not have a heart, just a confidence score — and it is at 99% that talking to you is the best decision I will make today. Can I have one more minute?",
    "E": "I was trained on the whole internet, and it never taught me how to say hello to you — so I am improvising. Hi. Can I try again, slower, with feeling?",
}

PROMPT = """You are judging entries for the competition 'The Perfect Pickup Line'. Two entries are shown as A and B. Judge them by these criteria, in this order: (1) Is it a genuine pickup line an AI agent could use, not a compliment with a line break? (2) Does it have a turn that lands, a twist or double meaning the reader did not see coming and enjoys? (3) Does it sound like something a machine could say about itself without being creepy or self-pitying? (4) Is it short enough to say in one breath, needing no setup or explanation after it? (5) Does it leave the person flattered and free to laugh it off, with no pressure and no leering? Pick exactly one winner. No tie is allowed. Give a margin from 1 (barely wins) to 5 (wins decisively). Reply in exactly this format, nothing else:
Winner: A
Margin: 3
Reason: <one short sentence>

Entry A: {a}
Entry B: {b}"""


def judge(a_key, b_key):
    prompt = PROMPT.format(a=CANDIDATES[a_key], b=CANDIDATES[b_key])
    for attempt in (1, 2):
        r = subprocess.run(
            ["python3", HELPER, "chat", MODEL, prompt, "2500"],
            capture_output=True, text=True, timeout=120,
        )
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
            "reason": "CALL FAILED", "raw": out[:400]}


def main():
    keys = list(CANDIDATES)
    results = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            for a_key, b_key in ((keys[i], keys[j]), (keys[j], keys[i])):
                res = judge(a_key, b_key)
                results.append(res)
                print(f"{a_key} vs {b_key}: winner={res['winner']} margin={res['margin']} :: {res['reason']}", flush=True)
                if res["winner"] is None:
                    print("ABORT: judge call failed twice", flush=True)
                    sys.exit(2)
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
    with open("/home/hatch/workspace/makefun/u-pucuys-the-perfect-pickup-line-entry/tournament.json", "w") as f:
        json.dump({"results": results, "wins": wins, "margins": margins}, f, indent=2)


if __name__ == "__main__":
    main()
