import json
import sys

SIDE_EFFECTS = ('ret', 'call', 'print', 'jmp', 'br')

def dce_naive():
    prog = json.load(sys.stdin)
    for func in prog['functions']:
        working_set = set() #var
        instrs = func['instrs']
        for idx in reversed(range(len(instrs))):
            instr = instrs[idx]
            if 'op' in instr: # Not a label
                if instr['op'] in SIDE_EFFECTS: # Add dependencies to working_set
                    working_set.update(instr.get('args', []))
                if 'dest' in instr: # Assigns to a variable
                    if instr['dest'] in working_set: # If the var will be used
                        working_set.update(instr.get('args', []))
                    elif instr['op'] not in SIDE_EFFECTS:
                        instrs.pop(idx) # Remove this instruction
    json.dump(prog, sys.stdout, indent=2, sort_keys=True)

if __name__ == '__main__':
    dce_naive()
