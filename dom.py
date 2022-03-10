import json
import sys

from cfg import cfg

## Returns the intersection of all sets
def intersection(sets):
  if len(sets) == 0: return set()
  result = sets[0].copy()
  for s in sets[1:]:
    result = result.intersection(s)
  return result

# Returns a dictionary that maps from labels to dominators, the set of all
# (labels of) blocks which dominate that label
def get_dom(cfg):
  blocks, lbl2block, lbl2pred, _ = cfg
  dom = {lbl:{lbl for lbl in lbl2block} for lbl in lbl2block}
  # Dominators of the entry block includes only itself
  dom[blocks[0][0]['label']] = {blocks[0][0]['label']}
  changed = True
  while changed:
    changed = False
    for block in blocks[1:]:
      label = block[0]['label']
      doms = intersection([dom.get(lbl, set()) for lbl in lbl2pred[label]])
      doms.add(label)
      if doms != dom.get(label):
        changed = True
        dom[label] = doms
  return dom

# Returns a dictionary that maps lbl to the set of all of its children in the dominance tree
def get_dom_tree(cfg):
  dominators = get_dom(cfg)
  tree = {lbl:set() for lbl in dominators}
  for lbl, doms in dominators.items():
    candidates = doms.copy() # Nodes that may immediately dominate lbl
    candidates.remove(lbl) # Remove reflexive relation
    # Remove blocks that do not immediately dominator tree until one remains
    if candidates: # If the block had dominators other than itself
      doms = list(candidates)
      while len(candidates) > 1:
        dom = doms.pop()
        # If blocks A and B dominate lbl and A dom B,
        # then A does not immediate dominate lbl
        candidates.difference_update(dominators[dom] - {dom})
      idom = candidates.pop()
      tree[idom].add(lbl)
  return tree

def graphviz_printer(name, graph):
  print('digraph {} {{'.format(name))
  for node in graph:
    print('  {};'.format(node))
  for node, succs in graph.items():
    for succ in succs:
      print('  {} -> {};'.format(node, succ))
  print('}')

# Like get_dom_tree, but map every block to the list of blocks that they dominate
def get_dominators2dominated(cfg):
  dominated2dominator = get_dom(cfg)
  # Compute the set of all blocks that A dominates.
  dominator2dominated = {lbl:set() for lbl in dominated2dominator}
  for dominated, dominators in dominated2dominator.items():
    for dominator in dominators:
      dominator2dominated[dominator].add(dominated)
  return dominator2dominated

# Returns a dictionary that maps a label to all of the (labels of) blocks in its
# dominance frontier
def get_dom_frontier(cfg):
  lbl2succ = cfg[3]
  dominator2dominated = get_dominators2dominated(cfg)
  # Maps a label to the set of labels (of blocks) strictly dominated by label
  strictly_dom = {dominator:(dominated - {dominator}) for dominator, dominated in dominator2dominated.items()}
  frontier = {lbl:set() for lbl in dominator2dominated}

  # for block that A dominates, add succ[block] - strictly_dom[A] to A's domination frontier
  for dominator, dominated in dominator2dominated.items():
    for block in dominated:
      frontier[dominator].update(set(lbl2succ[block]) - strictly_dom[dominator])
  return frontier

# Convert a dictionary to a list of tuples, where
#   1). The tuples are sorted alphabetically according to their first value, and
#   2). The second value is converted to a list and sorted alphabetically
def printer(dic):
  new_dic = {}
  for lbl, frontier in dic.items(): 
    new_dic[lbl] = list(frontier)
    new_dic[lbl].sort()
    dic_lst = list(new_dic.items())
    dic_lst.sort(key = lambda x: x[0])
  print(dic_lst)

# Compute the set of a node's dominators as the intersection of all paths which lead to the node
def get_dominators_by_path(cfg):
  blocks = cfg[0]
  lbl2succ = cfg[3]
  dominators = {lbl:[] for lbl in lbl2succ} # lbl -> list of all paths to lbl
  # Compute all unique paths in the cfg
  # keep track of a path, each of which is associated with a node
  # for each succ of node:
  #   if succ is already in path, do nothing
  #   otherwise, 
  #     add a copy of path to the list of paths to succ
  #     repeat with all of succ's succs
  entry = blocks[0][0]['label']
  frontier = [(entry, {entry})]
  while frontier:
    current, path = frontier.pop(0)
    dominators[current].append(path)
    for succ in lbl2succ[current]:
      if succ not in path:
        new_path = path.copy()
        new_path.add(succ)
        frontier.append((succ, new_path))
  return {lbl:intersection(paths) for lbl, paths in dominators.items()}

if __name__ == "__main__":
  prog = json.load(sys.stdin)
  analysis = sys.argv[1]
  if analysis == "dom":
    for func in prog['functions']:
      func_cfg = cfg(func['instrs'])
      printer(get_dom(func_cfg))
  elif analysis == "tree":
    for func in prog['functions']:
      func_cfg = cfg(func['instrs'])
      printer(get_dom_tree(func_cfg))
  elif analysis == "frontier":
    for func in prog['functions']:
      func_cfg = cfg(func['instrs'])
      printer(get_dom_frontier(func_cfg))
  elif analysis == "test":
    for func in prog['functions']:
      func_cfg = cfg(func['instrs'])
      assert get_dominators_by_path(func_cfg) == get_dom(func_cfg)
  else:
    print("Command not recognized")