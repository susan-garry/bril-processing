import json
import sys
from cfg import form_blocks

def dce_trivial(prog):
    changed = False
    for func in prog['functions']:
        blocks = form_blocks(func['instrs'])
        # perform local dead code elimination
        for block in blocks:
            last_def = {} # var -> index where var was last defined if not used
            dead = set() # indices of all dead instructions
            for i in range(len(block)):
                instr = block[i]
                #check for uses
                if 'args' in instr:
                    for arg in instr['args']: last_def.pop(arg, None)
                if 'dest' in instr:
                    dest = instr['dest']
                    if dest in last_def: # if the previous definition was not used:
                        dead.add(last_def[dest])
                        changed = True
                    last_def[instr['dest']] = i
            for i in dead: del block[i]
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