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


def get_defs(graph):
    defs = {} # var -> list of labels of blocks where var is defined
    for block in graph[0]:
        for instr in block:
            if 'dest' in instr:
                dest = instr['dest']
                typ = instr['type']
                defs[(dest, typ)] = defs.get((dest, typ), set()).union({block[0]['label']})
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
    # print("defs: ", get_defs(graph))
    for (var, typ), defs in get_defs(graph).items():
        to_visit = defs.copy() # Set of defs for [var] that haven't been visited yet
        while to_visit:
            def_block = to_visit.pop()
            frontier = dom_frontier[def_block]
            for frontier_block in frontier:
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
                    if frontier_block not in defs: to_visit.add(frontier_block)
    return graph


def rename(func, graph):
    _, lbl2block, _, lbl2succ = graph
    new_vars = {var:deque() for var, _ in get_defs(graph)} # var -> stack of vars
    
    # Initialize the stack for variables passed as arguments to the function
    for input in func.get('args', []): 
        arg = input['name']
        new_vars[arg].append(arg)
    renamed = set()
    immediate_doms = get_dom_tree(graph)
    # print("defs: ", get_defs(graph))

    # Rename all of the blocks rooted at [label]
    def rename_block(label):
        if label not in renamed:
            renames = {} # var -> number of times the variable was renamed in this block
            block = lbl2block[label]
            i = 1
            while i < len(block):
                instr = block[i]
                # print("instr: ", instr)
                # print("new names: ", new_vars)
                if instr.get('op') == 'phi' and len(instr['args']) == 0:
                    block.pop(i)
                else:
                    # Replace args with their new name
                    if 'args' in instr and instr['op'] != 'phi':
                        instr['args'] = [new_vars[a][-1] for a in instr['args']]
                    # Replace the destination with a new name and push it onto the stack
                    if 'dest' in instr:
                        new_dest = VarGen.gen()
                        new_vars[instr['dest']].append(new_dest)
                        renames[instr['dest']] = renames.get(instr['dest'], 0) + 1
                        instr['dest'] = new_dest
                    i += 1
            for succ_lbl in lbl2succ[label]:
                succ = lbl2block[succ_lbl]
                i = 1
                while (i < len(succ) and succ[i]['op'] == 'phi'):
                    var = succ[i]['var']
                    # print("new names: ", vars)
                    if new_vars[var]: # If var has been defined along this path
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
    return rename(func, insert_phi(func))

# Take a control flow graph which has been converted to ssa form,
# with phi nodes inserted and destinations renamed to be unique,
# and remove the phi nodes
def from_ssa(graph):
    lbl2block = graph[1]
    for block in graph[0]:
        while (len(block) > 1 and block[1]['op'] == 'phi'):
            instr = block.pop(1)
            # print(instr)
            for (pred, var) in zip(instr['labels'], instr['args']):
                # print(pred, var)
                pred = lbl2block[pred]
                move = {
                    'dest': instr['dest'],
                    'type': instr['type'],
                    'op': 'id',
                    'args': [var]}
                # print(move)
                if pred[-1].get('op') in CONTROL:
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
        elif sys.argv[1] == 'phi':
            graph = insert_phi(func)
        else:
            graph = ssa(func)
        func['instrs'] = [i for block in graph[0] for i in block]
    json.dump(prog, sys.stdout, indent=2, sort_keys=True)