import json
import sys
from collections import deque

from cfg import cfg
from dom import *

class VarGen:
    num_vars = 0
    @classmethod
    def gen(cls):
        cls.num_vars += 1
        return "v{}".format(cls.num_vars)

# TODO: Test this first
def get_defs(cfg):
    defs = {}
    for block in cfg[0]:
        for instr in block:
            if 'dest' in instr:
                dest = instr['dest']
                typ = instr['type']
                defs[(dest, typ)] = defs.get((dest, typ), []) + [block[0]['label']]
    return defs

def insert_phi(cfg):
    lbl2block = cfg[1]
    dom_frontier = get_dom_frontier(cfg)
    # print("dom frontier: ", dom_frontier)
    block2phi = {} # label -> the set of variables for which phi nodes have already been inserted
    for (var, typ), defs in get_defs(cfg).items():
        for def_block in defs:
            frontier = dom_frontier[def_block].copy()
            while frontier:
                frontier_block = frontier.pop()
                if var not in block2phi.get(frontier_block, []):
                    block = lbl2block[frontier_block]
                    phi = {
                        'dest' : var,
                        'type' : typ,
                        'op' : 'phi',
                        'args' : [],
                        'labels': []
                    }
                    block.insert(1, phi)
                    block2phi[frontier_block] = block2phi.get(frontier_block, set()).union({var})
                    frontier.update(dom_frontier[frontier_block])

def rename(cfg):
    _, lbl2block, _, lbl2succ = cfg
    new_vars = {var:deque() for var, _ in get_defs(cfg)} # var -> stack of vars
    renamed = set()
    dominator2dominated = get_dominators2dominated(cfg)
    # print(dominator2dominated)
    def rename_block(label):
        if label not in renamed:
            renames = {} # var -> number of times the variable was renamed in this block
            block = lbl2block[label]
            for instr in block:
                # Replace args with their new name
                if 'args' in instr and 'phi' not in instr:
                    instr['args'] = [new_vars[a][-1] if new_vars.get(a) else a for a in instr['args']]
                # Replace the destination with a new name and push it onto the stack
                if 'dest' in instr:
                    new_dest = VarGen.gen()
                    new_vars[instr['dest']].append(new_dest)
                    renames[instr['dest']] = renames.get(instr['dest'], 0) + 1
                    instr['dest'] = new_dest
            for succ_lbl in lbl2succ[label]:
                succ = lbl2block[succ_lbl]
                i = 1
                while(succ[i]['op'] == 'phi'):
                    var = succ[i]['dest']
                    # print(new_vars)
                    if new_vars[var]:
                        succ[i]['args'].append(new_vars[var][-1])
                        succ[i]['labels'].append(label)
                    i += 1
            renamed.add(label)
            for b in dominator2dominated[label].intersection(lbl2succ[label]):
                rename_block(b)
            for var, n in renames.items():
                while n > 0:
                    new_vars[var].pop()
                    n -= 1
    rename_block(cfg[0][0][0]['label'])

def to_ssa(cfg):
    insert_phi(cfg)
    rename(cfg)
    new_body = [i for block in cfg[0] for i in block]
    return new_body

def from_ssa(cfg):
    lbl2block = cfg[1]
    for block in cfg[0]:
        i = 1
        while block[i].get('phi'):
            instr = block[i]
            for (pred, var) in zip(instr['labels'], instr['args']):
                pred = lbl2block[pred]
                move = {
                    'dest': instr['dest'],
                    'type': instr['type'],
                    'op': id,
                    'args': [var]}
                pred.add(move)
            del instr
    return cfg

def ssa(body):
    # Convert the program to ssa
    graph = cfg(body)
    insert_phi(graph)
    rename(graph)
    # Convert the program from SSA (remove the phi nodes)
    from_ssa(graph)
    return [i for block in graph[0] for i in block] # Flatten the cfg

if __name__ == "__main__":
    prog = json.load(sys.stdin)
    for func in prog['functions']:
        graph = cfg(func['instrs'])
        # func['instrs'] = to_ssa(graph)
        func['instrs'] = ssa(func['instrs'])
    json.dump(prog, sys.stdout, indent=2, sort_keys=True)