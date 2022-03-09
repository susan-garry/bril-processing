# WARNING: This code currently does not work. I got a bit too ambitious and forgot
# how complicated this is.
# Need to iterate through succ nodes and take the union of their working sets
# Note to self - reimpliment all of this in Java?
import json
import sys
from cfg import cfg, get_preds

class VarGen:
  i = 0
  def next(self):
    var = "var6120{}".format(self.i)
    self.i += 1
    return var
  
class CFGIter:
  def __init__(self, lbl2block, lbl2succ):
    self.lbl2block = lbl2block
    self.lbl2succ = lbl2succ
    self.old2new = {}
    self.var_gen = VarGen()
    self.renamed = set()
  
  def rename_vars(self, block):
    for instr in reversed(block):
      local_working_set = self.old2new.keys().copy() # set of vars that may later be used
      if 'dest' in instr:
        dest = instr['dest']
        if dest in local_working_set.keys():
          local_working_set.remove(dest)
          instr['dest'] = self.old2new[dest]
        else:
          var = self.var_gen.next()
          self.old2new[instr['dest']] = var
          instr['dest'] = var
    # Recursively rename the variables of all successor blocks
    for succ in self.lbl2succ[block[0]['label']]:
      if succ not in self.renamed:
        self.renamed.add(succ)
        self.rename_vars(self.lbl2block[succ])

def rename_vars(prog):
  for func in prog['functions']:
    blocks, lbl2block, lbl2succ = cfg(func)
    last = blocks[-1]
    lbl2pred = get_preds(lbl2succ)
    renamer = CFGIter(lbl2block, lbl2pred)
    renamer.rename_vars(last)
    func = [instr for block in blocks for instr in block]
  return prog

if __name__ == "__main__":
  prog = json.load(sys.stdin)
  new_prog = rename_vars(prog)
  json.dump(new_prog, sys.stdout, indent=2, sort_keys=True)