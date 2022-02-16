import json
import sys

TERMINATORS = ['jmp', 'br', 'ret']

def form_blocks(body):
    blocks = [[]]
    for i in body:
        if 'label' in i: #A label
            blocks.append([i])
        else: #An actual instruction
            blocks[-1].append(i)
            if i['op'] in TERMINATORS: #A terminator instruction
                blocks.append([])
    return [block for block in blocks if block != []]

def label_blocks(blocks):
    lbl2block = {}
    i = 0
    for block in blocks:
        if 'label' in block[0]: # block already has a label
            lbl2block[block[0]['label']] = block
            block = block[1:]
        else: # block has no label
            label = 'block' + str(i) #create a unique label for it
            i += 1
            block.insert(0, {'label': label})
            lbl2block[label] = block
    return lbl2block

def get_preds(lbl2succ):
    lbl2pred = {} # label -> list of labels of predecessors
    for node, succrs in lbl2succ.items():
        for succ in succrs:
            lbl2pred[succ] = lbl2pred.get(succ, [])
            lbl2pred[succ].append(node)
    return lbl2pred

def cfg(func):
    blocks = form_blocks(func['instrs'])
    lbl2block = label_blocks(blocks)
    # build cfg
    cfg = {} # label -> list of labels of successive blocks
    for i in range(len(blocks)):
        last = blocks[i][-1]
        label = blocks[i][0]['label']
        if last['op'] in ['jmp', 'br']:
            cfg[label] = last['labels']
        else:
            if i < len(blocks) - 1:
                cfg[label] = blocks[i+1][0]['label']
            else:
                cfg[label] = []
    return blocks, lbl2block, cfg

if __name__ == '__main__':
    prog = json.load(sys.stdin)
    for func in prog['functions']:
        blocks, lbl2block, lbl2succ = cfg(func)
    # for block in blocks:
    #     print(block)
    # for node, succ in lbl2succ.items():
    #     print("{}: {}".format(node, succ))
