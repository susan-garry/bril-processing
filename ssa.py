import json
import sys
from collections import deque

from cfg import cfg
from dom import *

CONTROL = ('jmp', 'br', 'ret')

class VarGen:
    num_vars = 0
    @classmethod
    def gen(cls):
        cls.num_vars += 1
        return "v{}".format(cls.num_vars)

# TODO: Test this first
def get_defs(graph):
    defs = {}
    for block in graph[0]:
        for instr in block:
            if 'dest' in instr:
                dest = instr['dest']
                typ = instr['type']
                defs[(dest, typ)] = defs.get((dest, typ), []) + [block[0]['label']]
    return defs

def insert_phi(func):

    # Add a preheader block for any arguments in the function
    if 'args' in func:
        preheader = [{'label': 'preheader'}]
        for arg in func.get('args', []):
            move_arg = {
                'dest': arg['name'],
                'type': arg['type'],
                'op': 'id',
                'args': [arg['name']]
            }
            preheader.append(move_arg)
        while preheader: 
            func['instrs'].insert(0, preheader.pop())

    graph = cfg(func['instrs'])
    lbl2block = graph[1]
    dom_frontier = get_dom_frontier(graph)
    block2phi = {} # label -> the set of variables for which phi nodes have already been inserted


    # Add phi nodes to the graph
    for (var, typ), defs in get_defs(graph).items():
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
                        'labels': [],
                        'var': var
                    }
                    block.insert(1, phi)
                    block2phi[frontier_block] = block2phi.get(frontier_block, set()).union({var})
                    frontier.update(dom_frontier[frontier_block])
    return graph

def rename(graph):
    _, lbl2block, _, lbl2succ = graph
    new_vars = {var:deque() for var, _ in get_defs(graph)} # var -> stack of vars
    renamed = set()
    immediate_doms = get_dom_tree(graph)
    # print("defs: ", get_defs(graph))

    # Rename all of the blocks rooted at [label]
    def rename_block(label):
        if label not in renamed:
            renames = {} # var -> number of times the variable was renamed in this block
            block = lbl2block[label]
            for instr in block:
                # Replace args with their new name
                if 'args' in instr and instr['op'] != 'phi':
                    instr['args'] = [new_vars[a][-1] if new_vars[a] else a for a in instr['args']]
                # Replace the destination with a new name and push it onto the stack
                if 'dest' in instr:
                    new_dest = VarGen.gen()
                    new_vars[instr['dest']].append(new_dest)
                    renames[instr['dest']] = renames.get(instr['dest'], 0) + 1
                    instr['dest'] = new_dest
            for succ_lbl in lbl2succ[label]:
                succ = lbl2block[succ_lbl]
                i = 1
                while (i < len(succ) and succ[i]['op'] == 'phi'):
                    var = succ[i]['var']
                    # print(new_vars)
                    if new_vars[var]:
                        succ[i]['args'].append(new_vars[var][-1])
                        succ[i]['labels'].append(label)
                    i += 1
            renamed.add(label)
            for b in immediate_doms[label]:
                rename_block(b)
            for var, n in renames.items():
                while n > 0:
                    new_vars[var].pop()
                    n -= 1

    # Recursively rename the program, starting at the root
    rename_block(graph[0][0][0]['label'])
    return graph


# Convert a func to ssa form, leaving the phi nodes in the transformed graph
def to_ssa(func):
    return rename(insert_phi(func))

# Take a control flow graph which has been converted to ssa form,
# with phi nodes inserted and destinations renamed to be unique,
# and remove the phi nodes
def from_ssa(graph):
    lbl2block = graph[1]
    for block in graph[0]:
        while (len(block) > 1 and block[1]['op'] == 'phi'):
            instr = block.pop(1)
            for (pred, var) in zip(instr['labels'], instr['args']):
                # print(pred, var)
                pred = lbl2block[pred]
                move = {
                    'dest': instr['dest'],
                    'type': instr['type'],
                    'op': 'id',
                    'args': [var]}
                if pred[-1]['op'] in CONTROL:
                    pred.insert(-1, move)
                else: 
                    pred.append(move)
    return graph

# func is a bril functions
def ssa(func):
    # Rename variables and return the new instructions
    return from_ssa(to_ssa(func))

if __name__ == "__main__":
    prog = json.load(sys.stdin)
    for func in prog['functions']:
        if sys.argv[1] == 'ssa':
            graph = to_ssa(func)
        else:
            graph = ssa(func)
        func['instrs'] = [i for block in graph[0] for i in block]
    json.dump(prog, sys.stdout, indent=2, sort_keys=True)