import sys
from collections import defaultdict

EPS = None

class NFA:
    def __init__(self):
        self.trans = defaultdict(lambda: defaultdict(set))
        self.start = 0
        self.next_state = 1
        self.finals = set()

    def new_state(self):
        s = self.next_state
        self.next_state += 1
        return s

    def add_transition(self, frm, sym, to):
        self.trans[frm][sym].add(to)

    def epsilon_closure(self, states):
        stack = list(states)
        closure = set(states)
        while stack:
            s = stack.pop()
            for nxt in self.trans[s].get(EPS, ()):
                if nxt not in closure:
                    closure.add(nxt)
                    stack.append(nxt)
        return closure

    def accepts(self, inp):
        cur = self.epsilon_closure({self.start})
        for c in inp:
            nxt = set()
            for s in cur:
                for sym, dests in self.trans[s].items():
                    if sym is EPS:
                        continue
                    if match(sym, c):
                        nxt.update(dests)
            cur = self.epsilon_closure(nxt)
            if not cur:
                return False
        return bool(cur & self.finals)


def sym_char(c): return ('c', c)
def sym_class(name): return ('cl', name)

def match(sym, c):
    t, v = sym
    if t == 'c':
        return c == v
    if t == 'cl':
        if v == 'digit': return c.isdigit()
        if v == 'nonzero': return c in '123456789'
        if v == 'oct': return c in '01234567'
        if v == 'hex': return c.isdigit() or c.lower() in 'abcdef'
        if v == 'sign': return c in '+-'
    return False

# ---------- Integer NFAs ----------

def decimal_frag():
    trans = defaultdict(lambda: defaultdict(set))
    s0, s1, s2, s3 = 0,1,2,3
    trans[s0][sym_char('0')].add(s1)
    trans[s0][sym_class('nonzero')].add(s2)
    trans[s2][sym_class('digit')].add(s2)
    trans[s2][sym_char('_')].add(s3)
    trans[s3][sym_class('digit')].add(s2)
    trans[s1][sym_char('_')].add(s3)
    return {'start': s0, 'finals': {s1,s2}, 'trans': trans}

def octal_frag():
    trans = defaultdict(lambda: defaultdict(set))
    s0,s01,sO,sD,sU=0,1,2,3,4
    trans[s0][sym_char('0')].add(s01)
    trans[s01][sym_char('o')].add(sO)
    trans[s01][sym_char('O')].add(sO)
    trans[sO][sym_class('oct')].add(sD)
    trans[sO][sym_char('_')].add(sU)
    trans[sD][sym_class('oct')].add(sD)
    trans[sD][sym_char('_')].add(sU)
    trans[sU][sym_class('oct')].add(sD)
    return {'start': s0, 'finals': {sD}, 'trans': trans}

def hex_frag():
    trans = defaultdict(lambda: defaultdict(set))
    s0,s01,sX,sD,sU = 0,1,2,3,4
    trans[s0][sym_char('0')].add(s01)
    trans[s01][sym_char('x')].add(sX)
    trans[s01][sym_char('X')].add(sX)
    trans[sX][sym_class('hex')].add(sD)
    trans[sX][sym_char('_')].add(sU)
    trans[sD][sym_class('hex')].add(sD)
    trans[sD][sym_char('_')].add(sU)
    trans[sU][sym_class('hex')].add(sD)
    return {'start': s0, 'finals': {sD}, 'trans': trans}

def combined_int_nfa():
    nfa = NFA()
    def add_frag(frag):
        old_to_new = {}
        for s in range(max(frag['trans'].keys())+1):
            old_to_new[s] = nfa.new_state()
        for old_s, smap in frag['trans'].items():
            for sym,dests in smap.items():
                for d in dests:
                    nfa.add_transition(old_to_new[old_s], sym, old_to_new[d])
        return old_to_new[frag['start']], {old_to_new[f] for f in frag['finals']}

    ds, df = add_frag(decimal_frag())
    os, of = add_frag(octal_frag())
    hs, hf = add_frag(hex_frag())

    for start in [ds, os, hs]:
        nfa.add_transition(nfa.start, EPS, start)
    nfa.finals.update(df)
    nfa.finals.update(of)
    nfa.finals.update(hf)
    return nfa

# ---------- Float NFA ----------

def float_nfa():
    nfa = NFA()
    s = nfa.start
    i_run = nfa.new_state()
    dot = nfa.new_state()
    frac = nfa.new_state()
    e_mark = nfa.new_state()
    e_sign = nfa.new_state()
    e_run = nfa.new_state()

    nfa.add_transition(s, sym_class('digit'), i_run)
    nfa.add_transition(s, sym_char('.'), dot)
    nfa.add_transition(i_run, sym_class('digit'), i_run)
    nfa.add_transition(i_run, sym_char('.'), frac)
    nfa.add_transition(dot, sym_class('digit'), frac)
    nfa.add_transition(frac, sym_class('digit'), frac)
    for src in [i_run, frac]:
        for e in ['e','E']:
            nfa.add_transition(src, sym_char(e), e_mark)
    nfa.add_transition(e_mark, sym_class('sign'), e_sign)
    nfa.add_transition(e_mark, sym_class('digit'), e_run)
    nfa.add_transition(e_sign, sym_class('digit'), e_run)
    nfa.add_transition(e_run, sym_class('digit'), e_run)
    nfa.finals.update({frac, e_run})
    return nfa

# ---------- Run tests ----------

def run_tests(nfa, infile, outfile):
    lines = [l.strip() for l in open(infile, 'r', encoding='utf8') if l.strip()]
    results = []
    for ln in lines:
        if '\t' in ln: test, exp = ln.split('\t',1)
        elif '|' in ln: test, exp = ln.split('|',1)
        else: test, exp = ln.split()[0], 'accept'
        exp = exp.strip().lower()
        act = 'accept' if nfa.accepts(test) else 'reject'
        results.append(f"{test}\t{exp}\t{act}\t{'PASS' if act==exp else 'FAIL'}")
    with open(outfile, 'w', encoding='utf8') as f:
        f.write('\n'.join(results))
    print("Results written to", outfile)

# ---------- Main ----------

if __name__ == "__main__":
    if len(sys.argv)<3:
        print("Usage: python nfa_recognizer.py in_ans.txt out.txt")
        sys.exit(1)

    nfa = combined_int_nfa()
    f_nfa = float_nfa()
    nfa.add_transition(nfa.start, EPS, f_nfa.start)
    nfa.finals.update(f_nfa.finals)
    run_tests(nfa, sys.argv[1], sys.argv[2])
