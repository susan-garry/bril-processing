# A very simple program to count the number of constants in a program
import json
import sys

def count_consts(prog):
    consts = 0
    for func in prog['functions']:
        for instr in func['instrs']:
            if instr.get('op') == 'const':
                consts += 1
    return consts

if __name__ == '__main__':
    prog = json.load(sys.stdin)
    print(count_consts(prog))
