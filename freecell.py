#!/usr/bin/env python3
"""freecell - 终端 FreeCell 接龙(纯标准库)。

规则: 8 列牌堆(7,7,7,7,6,6,6,6)、4 个自由格、4 个基础堆。
列内降序红黑交替; 基础堆同花色 A->K; 空列可放任意牌(或序列, 受
supermove 上限 (1+空闲自由格) * 2^空列数 限制)。
"""

import argparse
import random
import secrets
import sys

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_VALUE = {r: i for i, r in enumerate(RANKS, start=1)}
SUITS = ["\u2660", "\u2665", "\u2666", "\u2663"]  # ♠♥♦♣
RED = {"\u2665", "\u2666"}
SUIT_NAME = {"\u2660": "黑桃", "\u2665": "红桃", "\u2666": "方块", "\u2663": "梅花"}


def card_name(card):
    r, s = card
    return f"{SUIT_NAME[s]}{r}"


def is_red(card):
    return card[1] in RED


def new_deck(rng):
    deck = [(r, s) for s in SUITS for r in RANKS]
    rng.shuffle(deck)
    return deck


def can_stack_tableau(card, dest_top):
    """列堆叠: 空列可放任意牌; 否则降序红黑交替。"""
    if dest_top is None:
        return True
    return (RANK_VALUE[card[0]] == RANK_VALUE[dest_top[0]] - 1
            and is_red(card) != is_red(dest_top))


def can_stack_foundation(card, pile):
    """基础堆: 空堆只能放 A; 否则同花色升序。"""
    if not pile:
        return card[0] == "A"
    top = pile[-1]
    return card[1] == top[1] and RANK_VALUE[card[0]] == RANK_VALUE[top[0]] + 1


class Game:
    def __init__(self, seed=None):
        rng = random.Random(seed) if seed is not None else secrets.SystemRandom()
        deck = new_deck(rng)
        self.cols = [[] for _ in range(8)]
        for i, card in enumerate(deck):
            self.cols[i % 8].append(card)
        self.cells = [None] * 4
        self.found = [[] for _ in range(4)]
        self.moves = 0

    def free_cells(self):
        return sum(1 for c in self.cells if c is None)

    def empty_cols(self):
        return sum(1 for c in self.cols if not c)

    def max_movable(self, dest_empty_col=True):
        """supermove 上限: (1+空闲自由格) * 2^空列数(目标空列不计)。"""
        e = self.empty_cols()
        if dest_empty_col:
            e = max(0, e - 1)
        return (1 + self.free_cells()) * (2 ** e)

    def movable_sequence(self, col, n):
        """列 col 顶部 n 张是否构成合法可移序列。"""
        pile = self.cols[col]
        if n < 1 or n > len(pile):
            return False
        seq = pile[len(pile) - n:]
        return all(
            RANK_VALUE[a[0]] == RANK_VALUE[b[0]] + 1 and is_red(a) != is_red(b)
            for a, b in zip(seq, seq[1:])
        )

    def move(self, src, dst, n=1):
        """src/dst: ('col', i) / ('cell', i) / ('found', i)。非法返回错误信息, 否则 None。"""
        sk, si = src
        dk, di = dst
        if not (0 <= si < (8 if sk == "col" else 4)):
            return "起点不存在"
        if not (0 <= di < (8 if dk == "col" else 4)):
            return "终点不存在"
        if sk == "cell":
            if n != 1:
                return "自由格一次只能移动 1 张"
            card = self.cells[si]
            if card is None:
                return "该自由格是空的"
            seq = [card]
        elif sk == "col":
            if not self.cols[si]:
                return "该列是空的"
            if not self.movable_sequence(si, n):
                return f"顶部 {n} 张不是合法序列"
            seq = self.cols[si][len(self.cols[si]) - n:]
        else:
            return "基础堆的牌不能移回"
        if dk == "cell":
            if n != 1:
                return "自由格一次只能放 1 张"
            if self.cells[di] is not None:
                return "该自由格已被占用"
        elif dk == "found":
            if n != 1:
                return "基础堆一次只能放 1 张"
            if not can_stack_foundation(seq[0], self.found[di]):
                return f"{card_name(seq[0])} 不能放到基础堆 {di + 1}"
        elif dk == "col":
            dest_top = self.cols[di][-1] if self.cols[di] else None
            if not can_stack_tableau(seq[0], dest_top):
                return f"{card_name(seq[0])} 不能放到第 {di + 1} 列"
            if n > self.max_movable(dest_empty_col=(dest_top is None)):
                return (f"一次最多移动 {self.max_movable(dest_empty_col=(dest_top is None))} 张"
                        f"(supermove 上限)")
        # 执行
        if sk == "cell":
            self.cells[si] = None
        else:
            del self.cols[si][len(self.cols[si]) - n:]
        if dk == "cell":
            self.cells[di] = seq[0]
        elif dk == "found":
            self.found[di].append(seq[0])
        else:
            self.cols[di].extend(seq)
        self.moves += 1
        return None

    def won(self):
        return all(len(p) == 13 for p in self.found)


def render(g):
    out = []
    out.append("自由格: " + " ".join(card_name(c) if c else "[ ]" for c in g.cells))
    out.append("基础堆: " + " ".join(card_name(p[-1]) if p else "[A]" for p in g.found))
    out.append("")
    height = max(len(c) for c in g.cols)
    header = "  ".join(f"列{i + 1:<3}" for i in range(8))
    out.append(header)
    for row in range(height):
        line = []
        for c in g.cols:
            line.append(card_name(c[row]) if row < len(c) else "    ")
        out.append("  ".join(f"{x:<4}" for x in line))
    out.append(f"\n已走 {g.moves} 步。命令: c3 f1 | c3 c5 [张数] | c3 fc1 | fc1 c2 | h 帮助 | q 退出")
    return "\n".join(out)


def parse_tok(tok):
    t = tok.strip().lower()
    if t.startswith("fc") and t[2:].isdigit():
        i = int(t[2:]) - 1
        if 0 <= i < 4:
            return ("cell", i)
    elif t.startswith("c") and t[1:].isdigit():
        i = int(t[1:]) - 1
        if 0 <= i < 8:
            return ("col", i)
    elif t.startswith("f") and t[1:].isdigit():
        i = int(t[1:]) - 1
        if 0 <= i < 4:
            return ("found", i)
    return None


def play_interactive(seed):
    if not sys.stdin.isatty():
        print("error: 交互模式需要终端, 管道请用 --auto", file=sys.stderr)
        return 2
    g = Game(seed)
    print("FreeCell 接龙 | 目标: 4 个基础堆全部 A->K")
    while True:
        print("\n" + render(g))
        if g.won():
            print(f"\n🎉 胜利! 共用 {g.moves} 步。")
            return 0
        try:
            text = input("> ").strip()
        except EOFError:
            print()
            return 0
        if not text:
            continue
        if text.lower() in ("q", "quit", "退出"):
            print(f"已退出, 共走 {g.moves} 步。")
            return 0
        if text.lower() in ("h", "help", "帮助"):
            print("c3 f1: 第3列顶牌 -> 基础堆1; c3 c5 [张数]: 列间移动; "
                  "c3 fc1: 列 -> 自由格; fc1 c2: 自由格 -> 列")
            continue
        parts = text.split()
        if len(parts) not in (2, 3):
            print("命令格式不对, 试试 h 看帮助。")
            continue
        src = parse_tok(parts[0])
        dst = parse_tok(parts[1])
        n = 1
        if len(parts) == 3:
            if not parts[2].isdigit():
                print("张数必须是数字。")
                continue
            n = int(parts[2])
        if src is None or dst is None:
            print("位置格式不对: 列 c1-c8, 自由格 fc1-fc4, 基础堆 f1-f4。")
            continue
        err = g.move(src, dst, n)
        if err:
            print(f"非法: {err}")
    return 0


def auto_moves(g, rng, steps):
    """弱策略 bot: 只做随机合法移动, 返回(步数, 非法尝试数)。"""
    illegal = 0
    for _ in range(steps):
        if g.won():
            break
        sk = rng.choice(["col", "col", "col", "cell"])
        si = rng.randrange(8 if sk == "col" else 4)
        dk = rng.choice(["col", "cell", "found"])
        di = rng.randrange(8 if dk == "col" else 4)
        n = 1
        if sk == "col" and dk == "col":
            pile = g.cols[si]
            n = rng.randint(1, min(4, len(pile))) if pile else 1
        err = g.move((sk, si), (dk, di), n)
        if err:
            illegal += 1
    return g.moves, illegal


def main(argv=None):
    ap = argparse.ArgumentParser(description="终端 FreeCell 接龙")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--auto", type=int, default=0, metavar="N",
                    help="自动随机游走 N 步(验证用)")
    args = ap.parse_args(argv)
    if args.auto:
        if args.auto < 1:
            print("error: --auto 需要正整数", file=sys.stderr)
            return 2
        rng = random.Random(args.seed)
        g = Game(args.seed)
        moves, illegal = auto_moves(g, rng, args.auto)
        print(f"自动游走结束: 成功 {moves} 步, 非法尝试 {illegal} 次, "
              f"胜利={'是' if g.won() else '否'}")
        return 0
    return play_interactive(args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
