import functools
import json
import sys

from numpy import true_divide
from cfg import cfg
from dom import get_dom
from df import live_vars

side_effect_ops = {'alloc', 'free', 'load', 'store', 'ptradd', 'call', 'print'}

def find_loops(graph):

    def get_loop(start, end, dominators):
        interior_nodes = set() # The set of all interior nodes in the loop visited so far
        preds = graph['lbl2pred']
        to_visit = {end}
        while to_visit:
            block = to_visit.pop()
            if block != start:
                interior_nodes.add(block)
                for pred in preds[block]:
                    if start not in dominators[pred]:
                        # There is an incoming edge from a block not dominated by the loop head; this is not a natural loop
                        return set()
                        to_visit.add(pred)
                    elif pred not in interior_nodes:
                        to_visit.add(pred)

        loop = [start]
        interior_nodes.remove(end)
        for block in interior_nodes: loop.append(block)
        loop.append(end)
        return loop

    doms = get_dom(graph) # Step 1: compute the dominator relation
    lbl2succ = graph['lbl2succ'].copy() # Make a copy of the CFG
    loops = []
    visited = set()
    def dfs(block):
        # Step 2: find backedges
        for succ in lbl2succ[block]:
            if succ in doms[block] and succ != block: # If this is a backedge
                # Step 3: figure out which nodes are actually in the loop
                loops.append(get_loop(succ, block, doms))
            if succ not in visited:
                visited.add(succ)
                dfs(succ)
    first = graph['blocks'][0][0]['label'] # Get the label of the first block in the CFG
    dfs(first)
    return loops

def get_and_remove_loop_invariant(loop, live_in):
    # An instruction is loop invariant if
    #   1). It is not used before it is defined, and
    #   2). It does not depend on variables which are not loop invariant

    not_loop_invariant = live_in.copy()

    changed = True
    while(changed):
        # print(not_loop_invariant)
        changed = False
        defined = set() # set of possibly loop invariant vars
        for block in loop:
            for instr in block:
                # print("instr: ", instr)
                if 'dest' in instr:
                    var = instr['dest']
                    if var not in not_loop_invariant:
                        op = instr['op']
                        # If the variable was previously defined or uses mem ops
                        if var in defined or op in side_effect_ops:
                            not_loop_invariant.add(var)
                            changed = True
                            continue
                        if op != 'const':
                            for arg in instr['args']:
                                if arg in not_loop_invariant:
                                    not_loop_invariant.add(var)
                                    changed = True
                                    continue
                    defined.add(var)
    loop_invariant = {} # loop invariant var -> def
    for block in loop:
        i = 0
        while i < len(block):
            instr = block[i]
            if 'dest' in instr and instr['dest'] not in not_loop_invariant:
                loop_invariant[instr['dest']] = instr
                block.remove(instr)
            else: 
                i = i + 1
    return loop_invariant

# def unswitch(cfg):
#     for loop in find_loops(cfg):
#         # basic version: check if the last instruction of the first block is a branch
#         # If the boolean guard for this branch is loop invariant, then unswitch
#         # Can use constant folding to ensure that invariant guards will always evaluate to a constant or single id? No: consider arg && true
#             # Insert loop_preheader1 block, which
#         break
        

def licm(body):
    func_cfg = cfg(body)
    graph = func_cfg
    blocks = graph['blocks']
    loops = find_loops(func_cfg)

    def get_block_idx(lbl):
        for i in range(len(blocks)):
            if blocks[i][0]['label'] == lbl: return i
        return -1

    for loop in loops:
        start_lbl = loop[0]
        # The set of variants that are live going into the loop header
        invariants = get_and_remove_loop_invariant([graph['lbl2block'][lbl] for lbl in loop], live_vars(func_cfg)[start_lbl][0])
        def compare_instr(i1, i2):
            if i1['dest'] in i2.get('args', []): return -1
            if i2['dest'] in i1.get('args', []): return 1
            return 0

        # Create a preheader block with the loop invariant instructions
        invariant_instrs = list(invariants.values())
        invariant_instrs.sort(key=functools.cmp_to_key(compare_instr))
        preheader_lbl = start_lbl + '_preheader'
        preheader = [{'label': preheader_lbl}]
        preheader.extend(invariant_instrs)
        blocks.insert(get_block_idx(start_lbl), preheader)

        # For all predecessors of the loop header *outside* of the loop, jump to the loop preheader
        for pred in graph['lbl2pred'][start_lbl]:
            if pred not in loop:
                pred_block = graph['lbl2block'][pred]
                last = pred_block[-1]
                if 'op' in last and (last['op'] == 'br' or last['op'] == 'jmp'):
                    last['labels'] = list(map(lambda x: preheader_lbl if x == start_lbl else x, last['labels']))
                else:
                    pred_block.append({'op' : 'jmp', 'labels': [preheader_lbl]})
    
    # flatten the list of blocks into the new function body
    return [instr for block in blocks for instr in block]

if __name__ == '__main__':
    prog = json.load(sys.stdin)
    for func in prog['functions']:
        func['instrs'] = licm(func['instrs'])
    json.dump(prog, sys.stdout, indent=2, sort_keys=True)