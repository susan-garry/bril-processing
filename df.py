import argparse
import json
import sys
from cfg import cfg, get_preds
from briltxt import instr_to_string

class DataFlow :

  def __init__(self, init, direction, meet, transfer, printer="default"):
    self.init = init
    self.direction = direction
    self.meet = meet
    self.transfer = transfer
    if printer != "default":
      self.printer = printer

  def df(self, cfg):
    blocks, lbl2block, lbl2pred, lbl2succ = cfg
    analysis = {} # label -> (in, out)
    if self.direction == "FORWARD":
      preds = lbl2pred
      succs = lbl2succ
    if self.direction == "BACKWARD":
      preds = lbl2succ
      succs = lbl2pred
    # initialize variables
    worklist = set(lbl2block.keys())
    analysis = {} # label -> (in, out)
    for lbl in worklist:
      analysis[lbl] = (None, self.init)
    # perform analysis
    while worklist:
      lbl = worklist.pop()
      if len(preds[lbl]) == 0: 
        # print("no preds")
        inb = self.init
      else:
        # print("has preds")
        inb = analysis[preds[lbl][0]][1]
        # print("partial in: ", inb)
        for i in range(1, len(preds[lbl])):
          pred = preds[lbl][i]
          inb = self.meet(inb, analysis[pred][1])
          # print("partial in: ", inb)
      outb = self.transfer(lbl2block[lbl], inb)
      if outb != analysis[lbl][1]:
        worklist.update(succs[lbl])
      analysis[lbl] = (inb.copy(), outb.copy())
    # if this is a backwards pass, reverse the input and output
    if self.direction == "BACKWARD":
      for lbl, output in analysis.items():
        analysis[lbl] = (output[1], output[0])
    self.printer(blocks, analysis)

  def printer(self, blocks, analysis):
    lbls = [block[0]['label'] for block in blocks]
    for lbl in lbls:
      data = analysis[lbl]
      print("  ", lbl)
      print("    in: ", data[0])
      print("    out: ", data[1])

def reaching_defs(cfg):

  def meet(reachable1, reachable2):
    reachable = {}
    for dest, instrs in reachable1.items():
      reachable[dest] = instrs.copy()
    for dest, instrs in reachable2.items():
      reachable[dest] = reachable.get(dest, [])
      non_duplicates = [instr for instr in instrs if instr not in reachable[dest]]
      reachable[dest].extend(non_duplicates)
    return reachable

  def transfer(block, inb):
    outb = inb.copy()
    kill = False
    for instr in block:
      if 'dest' in instr:
        outb[instr['dest']] = [instr]
        kill = True
    return outb if kill else inb

  def printer(blocks, analysis):
    lbls = [block[0]['label'] for block in blocks]
    for lbl in lbls:
      data = analysis[lbl]
      print("  block:", lbl)
      inb = [instr for instrs in data[0].values() for instr in instrs]
      print("    in: ")
      for instr in inb:
        print('      {}'.format(instr_to_string(instr)))
      outb = [instr for instrs in data[1].values() for instr in instrs]
      print("    out: ")
      for instr in outb:
        print('      {}'.format(instr_to_string(instr)))

  solver = DataFlow(dict(), "FORWARD", meet, transfer, printer)
  solver.df(cfg)

if __name__ == "__main__":
  # arg_parser = argparse.ArgumentParser()
  # arg_parser.add_argument()
  prog = json.load(sys.stdin)
  for func in prog['functions']:
    print(func['name'], ":")
    func_cfg = cfg(func)
    reaching_defs(func_cfg)