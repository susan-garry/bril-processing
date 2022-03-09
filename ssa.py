import json
import sys
from collections import deque

from cfg import cfg
from dom import *

class VarGen:
    num_vars = 0
    @classmethod
    def gen(cls):
        num_vars += 1
        return "v{}".format(num_vars)

# TODO: Test this first
def get_defs(cfg):
    defs = {}
    for block in cfg[0]:
        for instr in block:
            if 'dest' in instr:
                dest = instr['dest']
                typ = instr['type']
                defs[dest] = defs.get(dest, []) + [(typ, block[0]['label'])]
    return defs

def insert_phi(cfg):
    lbl2block = cfg[1]
    dom_frontier = get_dom_frontier(cfg)
    block2phi = {} # label -> the set of variables for which phi nodes have already been inserted
    for var, (typ, defs) in get_defs(cfg):
        for def_block in defs:
            frontier = dom_frontier[def_block].copy()
            while frontier:
                frontier_block = dom_frontier[def_block].pop()
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
    new_vars = set() # var -> stack of vars
    renamed = set()
    dom = get_dom(cfg)
    def rename_block(block):
        renames = {} # var -> number of times the variable was renamed in this block
        for instr in block:
            # Replace args with their new name
            if 'args' in instr:
                instr['args'] = [new_vars[a][-1] for a in instr['args']] # Replace args with their new names
            # Replace the destination with a new name and push it onto the stack
            if 'dest' in instr:
                # If this is a phi instruction, make it read from the top of the stack
                new_dest = VarGen.gen()
                new_vars[instr['dest']].append(new_dest)
                renames[instr['dest']] = renames.get(instr['dest'], 0) + 1
                instr['dest'] = new_dest
        label = block[0]['label']
        for succ in cfg[3]:
            i = 1
            while(succ[i].get('phi')):
                var = instr['dest']
                if not new_vars[var]:
                    instr['args'].append(new_vars[var][-1][-1])
                    instr['labels'].append(label)
                i += 1
        renamed.add(label)
        for b in cfg[3].intersection(dom[label]):
            rename(b)
        for var, n in renames.items():
            while n > 0:
                new_vars[var].pop()

    rename_block(cfg[0][0])

# def to_ssa(prog):
#     graph = cfg(prog)
#     insert_phi(graph)
#     rename(graph)
#     new_prog = [i for block in cfg[0] for i in block]
#     return new_prog

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
    return cfg

def ssa(prog):
    # Convert the program to ssa
    graph = cfg(prog)
    insert_phi(graph)
    rename(graph)
    # Convert the program from SSA (remove the phi nodes)
    from_ssa(graph)
    new_prog = [i for block in graph[0] for i in block]
    return new_prog

if __name__ == "__main__":
    prog = json.load(sys.stdin)
    transformed = ssa(prog)
    json.dump(transformed, sys.stdout, indent=2, sort_keys=True)