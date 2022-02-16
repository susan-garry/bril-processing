import json
import sys
from cfg import form_blocks

SIDE_EFFECTS = ('ret', 'call', 'print', 'jmp', 'br')

def dce_naive():
    prog = json.load(sys.stdin)
    for func in prog['functions']:
        instrs = func['instrs']
        blocks = form_blocks(instrs)
        global_working_set = set() # vars needed later in the function
        for block in reversed(blocks):
            local_working_set = global_working_set.copy() # variables that may be needed from earlier in this block
            for idx in reversed(range(len(block))):
                instr = block[idx]
                if 'op' in instr: # Not a label
                    if instr['op'] in SIDE_EFFECTS: # Add dependencies to working sets
                        global_working_set.update(instr.get('args', []))
                        local_working_set.update(instr.get('args', []))
                    if 'dest' in instr: # Assigns to a variable
                        if instr['dest'] in local_working_set: # If the var may be needed
                            global_working_set.update(instr.get('args', []))
                            local_working_set.remove(instr['dest'])
                            local_working_set.update(instr.get('args', []))
                        elif instr['op'] not in SIDE_EFFECTS:
                            block.pop(idx) # Remove this instruction
        func['instrs'] = [instr for block in blocks for instr in block]
    json.dump(prog, sys.stdout, indent=2, sort_keys=True)

if __name__ == '__main__':
    dce_naive()