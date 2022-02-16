# Implement local value numbering
import json
import sys
from cfg import cfg
from rename_vars import VarGen
from dce_trivial import dce_trivial

def subexpr_elim(prog):
  for func in prog['functions']:
    blocks, _, _ = cfg(func)
    old2new = {} # map old variable names to new variable names
    var_gen = VarGen()
    for block in blocks:
      table = {} # var -> (subexpr, cannonical_var)
      working_set = set() # set of all vars reused later in the block
      for instr in reversed(block):
        if 'dest' in instr:
          if instr['dest'] in working_set:
            dest = var_gen.next()
            instr['dest'] = dest
            working_set.add(dest)
          if 'args' in instr:
            working_set.difference_update(set(instr['args']))
      for instr in block:
        if 'args' in instr:
          #map 'args' to cannonical variables, inelegantly
          instr['args'] = [table.get(arg, ["", arg])[1] for arg in instr['args']]
        if 'dest' in instr:
          dest = instr['dest']
          # check if subexpr is in the table
          subexpr = const_fold(instr, table)
          for _, val in table.items():
            if subexpr == val[0]:
              table[dest] = val
              instr['op'] = 'id'
              instr['args'] = [val[1]]
              break
          if dest not in table or table[dest][0] != subexpr:
            table[dest] = (subexpr, dest)
  return prog

def const_fold(instr, table):
  # Precondition: 'dest' in instr
  op = instr['op']
  if instr['op'] == 'const':
    return (op, instr['value'])
  else:
    # don't implement constant folding yet; just return the subexpr
    return (op, instr['args'].sort())
  
    
if __name__ == "__main__":
  prog = json.load(sys.stdin)
  subexpr_elim(prog)
  json.dump(prog, sys.stdout, indent=2, sort_keys=True)