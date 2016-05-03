import logging
import re
from ast import literal_eval
import operator
import matplotlib.pyplot as plt
import numpy as np

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger(__name__+'.TreeParser').setLevel(logging.DEBUG)

class TreeParser(object):

    @staticmethod
    def parse(input, convert_brackets=False):
        # print(input)
        if convert_brackets:
            # replace any non-square brackets by square brackets
            for opening, closing in [('[',']'), ('(',')'), ('{','}')]:
                input = input.replace(opening,'[')
                input = input.replace(closing,']')
        # remove leading and trailing whitespace
        # print(input)
        input = input.strip()
        # replace any whitespace by a simple space
        # print(input)
        input = re.sub('\s+', ' ', input)
        # remove whitespace between brackets
        # print(input)
        input = input.replace('[ [', '[[')
        input = input.replace('] [', '][')
        input = input.replace('] ]', ']]')
        # patch brackets with comma
        # print(input)
        input = input.replace('[', ',[')
        input = input.replace(']', '],')
        # remove multiple subsequent commas
        # print(input)
        input = re.sub(',+', ',', input)
        # remove leading and trailing commas
        # print(input)
        if input.startswith(','):
            input = input[1:]
        if input.endswith(','):
            input = input[:-1]
        # remove commas between double opening/closing brackets
        # print(input)
        while True:
            mod_input = input.replace('],]', ']]')
            if input != mod_input:
                input = mod_input
            else:
                break
        while True:
            mod_input = input.replace('[,[', '[[')
            if input != mod_input:
                input = mod_input
            else:
                break
        # remove whitespace before and after commas
        # print(input)
        input = re.sub('\s*,\s*', ',', input)
        # patch any substring not containing functional characters with quotation marks
        # print(input)
        input = re.sub('([^][,]+)', '"\\1"', input)
        # print(input)
        return literal_eval(input)

    def __init__(self, array, string_input=False):
        if string_input:
            self.__init__(TreeParser.parse(array))
        else:
            self.logger = logging.getLogger(__name__+'.TreeParser')
            self.parent = None
            self.label = array[0]
            self.children = []
            if len(array) > 1:
                for child_idx in range(1,len(array)):
                    self.children.append(TreeParser(array[child_idx]))
                    self.children[-1].parent = self

    def layout(self, leaf_positions=None):
        # depth first search
        leaf_nodes = []
        node_stack = [(self, 0)]
        depths = {self: 0}
        while node_stack:
            node, child_idx = node_stack[-1]
            if child_idx >= len(node.children):
                node_stack.pop()
                if len(node.children) == 0:
                    leaf_nodes.append(node)
                    # print("leaf node: '{}'".format(node.label))
            else:
                node_stack[-1] = (node, child_idx+1)
                child = node.children[child_idx]
                node_stack.append((child, 0))
                depths[child] = depths[node] + 1
                # print("add node: '{}'".format(child.label))
        # determine node positions starting at leaf nodes
        if leaf_positions is not None and len(leaf_positions) < len(leaf_nodes):
            self.logger.warning("Number of given leaf positions is less than number of leaf nodes ({}<{})".format(len(leaf_positions),len(leaf_nodes)))
            leaf_positions = None
        node_positions = {}
        for leaf_idx, leaf in enumerate(leaf_nodes):
            if leaf_positions is not None:
                node_positions[leaf] = (leaf_positions[leaf_idx], -depths[leaf])
            else:
                node_positions[leaf] = (leaf_idx, -depths[leaf])
        for node, depth in sorted(depths.items(), key=operator.itemgetter(1), reverse=True):
            if len(node.children) > 0:
                children_mean = 0
                for child in node.children:
                    children_mean += node_positions[child][0]
                children_mean /= len(node.children)
                node_positions[node] = (children_mean, -depth)
        return node_positions

    def plot(self,
             ax=None,
             line_color='k',
             line_style='-',
             line_width=2,
             label_style='italic',
             node_style={'facecolor':'red', 'pad':10},  # todo: dict as default argument is dangerous (it's mutable)
             padding=0,
             offset=(0,0),
             scaling=(1,1),
             leaf_positions=None,
             adjust_axes=True):
        node_positions = self.layout(leaf_positions=leaf_positions)
        # apply offset and scaling
        for node, (x_pos, y_pos) in node_positions.items():
            node_positions[node] = (x_pos*scaling[0] + offset[0], y_pos*scaling[1] + offset[1])
        # create plot if none was provided
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        # add connections between nodes
        for node, (x_pos, y_pos) in node_positions.items():
            for child in node.children:
                child_x, child_y = node_positions[child]
                ax.plot([x_pos, child_x], [y_pos, child_y], color=line_color, linestyle=line_style, linewidth=line_width)
        # add nodes (get boundaries)
        x_min = np.inf
        y_min = np.inf
        x_max = -np.inf
        y_max = -np.inf
        for node, (x_pos, y_pos) in node_positions.items():
            x_min = min(x_min, x_pos)
            x_max = max(x_max, x_pos)
            y_min = min(y_min, y_pos)
            y_max = max(y_max, y_pos)
            ax.text(x_pos, y_pos, node.label, style=label_style, bbox=node_style)
        if adjust_axes:
            ax.axis([x_min-padding, x_max+padding, y_min-padding, y_max+padding])