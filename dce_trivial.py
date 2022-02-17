import json
import sys
from cfg import form_blocks

def dce_trivial(prog):
    changed = False
    for func in prog['functions']:
        blocks = form_blocks(func['instrs'])
        # perform local dead code elimination
        for i in range(len(blocks)):
            block = blocks[i]
            last_def = {}
            new_block = []
            for instr in block:
                #check for uses
                if 'args' in instr:
                    for arg in instr['args']: last_def.pop(arg, None)
                if 'dest' in instr:
                    if instr['dest'] not in last_def:
                        new_block.append(instr)
                    else:
                        changed = True
                    last_def[instr['dest']] = i
                else:
                    new_block.append(instr)
            blocks[i] = new_block
        # perform global dead code elimination
        # get a list of all used variables
        used = set()
        for block in blocks:
            for instr in block:
                if 'args' in instr: used.update(instr['args'])
        instrs = []
        for block in blocks:
            for instr in block:
                if 'dest' not in instr or instr['dest'] in used:
                    instrs.append(instr)
                else:
                    changed = True
        func['instrs'] = instrs
    return changed

if __name__ == '__main__':
    prog = json.load(sys.stdin)
    while dce_trivial(prog):
        pass
    json.dump(prog, sys.stdout, indent=2, sort_keys=True)