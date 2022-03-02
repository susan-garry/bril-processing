import json
import sys
from cfg import cfg
from dce_trivial import dce_trivial

COMMUTATIVE = ('add', 'mul', 'eq', 'and', 'or')

# Local value numbering
def lvn(prog):
  for func in prog['functions']:
    blocks = cfg(func)[0]
    # Calculate the number of times each var is written to in this block
    for block in blocks:
      table = {} # var -> (cannonical_var, subexpr)
      used = {} # var -> num times var is assigned to in this block, if var is assigned to in this block
      for instr in block:
        if 'dest' in instr:
          dest = instr['dest']
          used[dest] = used.get(dest, 0) + 1
      # LVN
      for instr in block:
        if 'args' in instr:
          #map 'args' to cannonical variables, inelegantly
          instr['args'] = [table.get(arg, [arg])[0] for arg in instr['args']]
        if 'dest' in instr:
          dest = instr['dest']
          old_dest = dest
          # check if the variable will be clobbered later; rename if necessary
          if used.get(dest, 0) > 1: # If the variable will later be overwritten
            dest = dest + "dksldfioj103" + str(used[dest]) # Generate (hopefully) unique variable name
            instr['dest'] = dest
            used[old_dest] -= 1
          # compute the value
          op = instr['op']
          added = False
          if op == 'const':
            value = (op, instr['value'])
          # Copy propagation and Constant Propagation
          elif op == 'id':
            var = instr['args'][0]
            if var in table:
              table[dest] = table[var]
              val = table[var][1]
              if val[0] == 'id': # var is in scope and is a copy
                instr['args'] = val[1]
              elif val[0] == 'const': # Constant propagation
                instr['op'] = 'const'
                instr['value'] = val[1]
            else:
              value = (op, instr['args'])
              table[dest] = (instr['args'][0], value)
            added = True
          else:
            # Constant folding 
            const_fold(instr, table)
            if instr['op'] == 'const':
              value = ('const', instr['value'])
            else: 
              if op in COMMUTATIVE:
                value = (op, sorted(instr['args']))
              else:
                value = (op, instr['args'])
              # check if value is in the table
              for val in table.values():
                if value == val[1]: # This value has already been calculated
                  table[dest] = val
                  instr['op'] = 'id'
                  instr['args'] = [val[0]]
                  added = True
                  break
          # Add this variable to the table if it is not already pointing to a different value
          if not added:
            table[dest] = (dest, value)
          table[old_dest] = table[dest]
  return prog

def const_fold(instr, table):
  # Precondition: 'dest' in instr

  def int_to_64bit(n):
    n = ((n + (2 ** 64)) % (2**65)) - (2 ** 64)
    return n
  
  op = instr['op']
  # Operations that can take a single argument
  if op == 'not':
    arg = instr['args'][0]
    value = table.get(arg, ["messy", "code"])[1]
    if value[0] == 'const':
      instr['op'] = 'const'
      instr['value'] = not value[1]
    return
  elif op == 'id' or op == 'call':
    return

  # Operations that take at least two arguments
  value1 = table.get(instr['args'][0], ["messy", "code"])[1] #The value for arg1
  value2 = table.get(instr['args'][1], ["messy", "code"])[1]
  if 'const' in value1 and 'const' in value2: # both arguments are constants
    v1 = value1[1]
    v2 = value2[1]
    # Logical operators
    if op == 'and':
      instr['value'] = v1 and v2
    elif op == 'or':
      instr['value'] = v1 or v2
    # Arithmetic operators
    else: 
      v1 = int(v1)
      v2 = int(v2)
      # Check for division by zero
      if op == 'div':
        if v2 == 0:
          return
        else:
          instr['value'] = int_to_64bit(v1//v2)
      if op == 'add':
        instr['value'] = int_to_64bit(v1 + v2)
      elif op == 'sub':
        instr['value'] = int_to_64bit(v1 - v2)
      elif op == 'mul':
        instr['value'] = int_to_64bit(v1 * v2)
      elif op == 'eq':
        instr['value'] = v1 == v2
      elif op == 'lt':
        instr['value'] = v1 < v2
      elif op == 'gt':
        instr['value'] = v1 > v2
      elif op == 'le':
        instr['value'] = v1 <= v2
      elif op == 'ge':
        instr['value'] = v1 >= v2
    instr['op'] = 'const'
    instr.pop('args')
  
    
if __name__ == "__main__":
  prog = json.load(sys.stdin)
  lvn(prog)
  json.dump(prog, sys.stdout, indent=2, sort_keys=True)