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
        if convert_brackets:
            # replace any non-square brackets by square brackets
            for opening, closing in [('[',']'), ('(',')'), ('{','}')]:
                input = input.replace(opening,'[')
                input = input.replace(closing,']')
        # remove leading and trailing whitespace
        input = input.strip()
        # replace any whitespace by a simple space
        input = re.sub('\s+', ' ', input)
        # remove whitespace between brackets
        input = input.replace('[ [', '[[')
        input = input.replace('] [', '][')
        input = input.replace('] ]', ']]')
        # patch brackets with comma
        input = input.replace('[', ',[')
        input = input.replace(']', '],')
        # remove multiple subsequent commas
        input = re.sub(',+', ',', input)
        # remove leading and trailing commas
        if input.startswith(','):
            input = input[1:]
        if input.endswith(','):
            input = input[:-1]
        # remove commas between double opening/closing brackets
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
        input = re.sub('\s*,\s*', ',', input)
        # patch any substring not containing functional characters with quotation marks
        input = re.sub('([^][,]+)', '"\\1"', input)
        return literal_eval(input)

    def __init__(self, array, string_input=False):
        if string_input:
            self.__init__(TreeParser.parse(array))
        else:
            self.logger = logging.getLogger(__name__+'.TreeParser')
            self.parent = None
            self.leaf_idx = None
            self.label = array[0]
            self.children = []
            if len(array) > 1:
                for child_idx in range(1,len(array)):
                    self.children.append(TreeParser(array[child_idx]))
                    self.children[-1].parent = self
            # get leaf indices
            for node, (x_pos, depth) in self.layout().items():
                if not node.children:
                    node.leaf_idx = x_pos
                node.depth = depth

    def __str__(self):
        return "{} ({},{})".format(self.label, self.leaf_idx, self.depth)

    def __repr__(self):
        return "TreeParser()"

    def root_path(self):
        node = self
        path = self.label
        while node.parent is not None:
            node = node.parent
            path += "-->" + node.label
        return path

    def leaf_pairs(self, left_tie_breaking, right_tie_breaking, depth=0, node_idx=0):
        # check number of children
        if len(self.children) != 2:
            raise UserWarning("Nodes are expected to have exactly two children (this one has {})".format(len(self.children)))
        # find leaf pairs
        leaf_pair_list = []
        prelim_leaf_pair_list = [(self.children[0], self.children[1], 1)]
        while prelim_leaf_pair_list:
            left_leaf, right_leaf, pair_weight = prelim_leaf_pair_list.pop()
            if not left_leaf.children and not right_leaf.children:
                leaf_pair_list += [{'left': left_leaf,
                                    'right': right_leaf,
                                    'parent': self,
                                    'depth': depth,
                                    'weight': pair_weight}]
            else:
                # left leaf
                left_children = []
                for child in left_leaf.children:
                    if child.label == left_leaf.label:
                        if left_children:
                            # What to do in case of multiple options for LEFT children?
                            if left_tie_breaking == 'left':
                                left_children = [left_leaf.children[0]]
                                break
                            elif left_tie_breaking == 'all':
                                left_children += [child]
                            else:
                                raise UserWarning("Unknown left tie breaking policy: '{}'".format(left_tie_breaking))
                        else:
                            left_children = [child]
                if not left_leaf.children:
                    left_children = [left_leaf]
                if not left_children:
                    raise UserWarning("Could not find chord label '{}' (root path: {}, labels: {})".format(left_leaf.label,
                                                                                                           left_leaf.root_path(),
                                                                                                           [n.label for n in left_leaf.children]))
                # right leaf
                right_children = []
                for child in right_leaf.children:
                    if child.label == right_leaf.label:
                        if right_children:
                            # What to do in case of multiple options for RIGHT children?
                            if right_tie_breaking == 'right':
                                right_children = [right_leaf.children[1]]
                                break
                            elif right_tie_breaking == 'all':
                                right_children += [child]
                            else:
                                raise UserWarning("Unknown right tie breaking policy: '{}'".format(right_tie_breaking))
                        else:
                            right_children = [child]
                if not right_leaf.children:
                    right_children = [right_leaf]
                if not right_children:
                    raise UserWarning("Could not find chord label '{}' (root path: {}, labels: {})".format(right_leaf.label,
                                                                                                           right_leaf.root_path(),
                                                                                                           [n.label for n in right_leaf.children]))
                # insert back into preliminary list
                weight_spread = len(left_children)*len(right_children)
                for left_leaf in left_children:
                    for right_leaf in right_children:
                        prelim_leaf_pair_list.append((left_leaf, right_leaf, pair_weight/weight_spread))
        # recursively add pairs of children
        for child_idx, child in enumerate(self.children):
            if child.children:
                child_list = child.leaf_pairs(left_tie_breaking=left_tie_breaking,
                                              right_tie_breaking=right_tie_breaking,
                                              depth=depth+1,
                                              node_idx=node_idx+child_idx)
                leaf_pair_list += child_list
        # return list
        return leaf_pair_list

    def layout(self, leaf_positions=None, bottom_align=False, y_is_depth=None, y_is_span=None, x_mean=None):
        # default for y_is_depth
        if y_is_depth is None:
            if bottom_align:
                y_is_depth = False
            else:
                y_is_depth = True
        # default for y_is_span
        if y_is_span is None:
            if bottom_align:
                y_is_span = True
            else:
                y_is_span = False
        # default for x_mean
        if x_mean is None:
            if y_is_span:
                x_mean = False
            else:
                x_mean = True
        # check
        if y_is_depth and y_is_span:
            raise ValueError("Cannot do both, determine y-position by span (y_is_span=True) and determine y-position by"
                             " depth (y_is_depth=True)")
        if bottom_align and y_is_depth:
            raise ValueError("Cannot do both, bottom align leaves (bottom_align=True) and determine y-position by depth"
                             " (y_is_depth=True)")
        # depth first search
        leaf_nodes = []
        node_stack = [(self, 0)]
        depths = {self: 0}
        while node_stack:
            node, child_idx = node_stack[-1]
            if child_idx >= len(node.children):
                node_stack.pop()
                if not node.children:
                    leaf_nodes.append(node)
            else:
                node_stack[-1] = (node, child_idx+1)
                child = node.children[child_idx]
                node_stack.append((child, 0))
                depths[child] = depths[node] + 1
        # determine node positions starting at leaf nodes
        if leaf_positions is not None and len(leaf_positions) < len(leaf_nodes):
            self.logger.warning("Number of given leaf positions is less than number of leaf nodes ({}<{})".format(len(leaf_positions),len(leaf_nodes)))
            leaf_positions = None
        node_positions = {}
        for leaf_idx, leaf in enumerate(leaf_nodes):
            # use positions if given
            if leaf_positions is not None:
                leaf_x, leaf_y = leaf_positions[leaf_idx]
            else:
                leaf_x, leaf_y = (None, None)
            # fill value if not given
            if leaf_x is None:
                leaf_x = leaf_idx
            if leaf_y is None:
                if bottom_align:
                    leaf_y = 0
                else:
                    leaf_y = -depths[leaf]
            node_positions[leaf] = (leaf_x, leaf_y, leaf_x, leaf_x)
        # set for other nodes
        for node, depth in sorted(depths.items(), key=operator.itemgetter(1), reverse=True):
            if node.children:
                child_mean_x = 0
                child_min_x = np.inf
                child_max_x = -np.inf
                child_min_y = np.inf
                child_max_y = -np.inf
                span_min = np.inf
                span_max = -np.inf
                span_child_min = np.inf
                span_child_max = -np.inf
                for child in node.children:
                    child_x, child_y, span_start, span_end = node_positions[child]
                    child_mean_x += node_positions[child][0]
                    child_min_x = min(child_min_x, child_x)
                    child_max_x = max(child_max_x, child_x)
                    child_min_y = min(child_min_y, child_y)
                    child_max_y = max(child_max_y, child_y)
                    span_min = min(span_min, span_start)
                    span_max = max(span_max, span_end)
                    span_child_min = min(span_child_min, child_x - (span_end - span_start) / 2)
                    span_child_max = max(span_child_max, child_x - (span_end - span_start) / 2)
                child_mean_x /= len(node.children)
                if x_mean:
                    x_pos = child_mean_x
                else:
                    x_pos = span_child_min + (span_max - span_min) / 2
                if y_is_depth:
                    node_positions[node] = (x_pos, -depth, span_min, span_max)
                elif y_is_span:
                    node_positions[node] = (x_pos, span_max - span_min, span_min, span_max)
                else:
                    node_positions[node] = (x_pos, child_max_y + 1, span_min, span_max)
        return {n: (x, y) for n, (x, y, s, e) in node_positions.items()}

    def plot(self,
             ax=None,
             line_color='k',
             line_style='-',
             line_width=2,
             padding=0,
             offset=(0,0),
             scaling=(1,1),
             layout_kwargs=None,
             adjust_axes=None,
             fontdict=None,
             textkwargs=None,
             plot_nodes=True):
        if layout_kwargs is None:
            layout_kwargs = {}
        if fontdict is None:
            fontdict = {}
        for key, val in {'fontsize': 12}.items():
            if key not in fontdict:
                fontdict[key] = val
        if textkwargs is None:
            textkwargs = {}
        for key, val in {'bbox': {'facecolor': 'red', 'pad': 10},
                         'style': 'italic'}.items():
            if key not in textkwargs:
                textkwargs[key] = val
        if 'horizontalalignment' not in textkwargs and 'ha' not in textkwargs:
            textkwargs['ha'] = 'center'
        if 'verticalalignment' not in textkwargs and 'va' not in textkwargs:
            textkwargs['va'] = 'center'
        node_positions = self.layout(**layout_kwargs)
        # apply offset and scaling
        for node, (x_pos, y_pos) in node_positions.items():
            node_positions[node] = (x_pos * scaling[0] + offset[0], y_pos * scaling[1] + offset[1])
        # create plot if none was provided
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        # add connections between nodes
        for node, (x_pos, y_pos) in node_positions.items():
            for child in node.children:
                child_x, child_y = node_positions[child]
                ax.plot([x_pos, child_x], [y_pos, child_y], color=line_color, linestyle=line_style, linewidth=line_width)
        # get boundaries and add nodes
        x_min = np.inf
        y_min = np.inf
        x_max = -np.inf
        y_max = -np.inf
        for node, (x_pos, y_pos) in node_positions.items():
            x_min = min(x_min, x_pos)
            x_max = max(x_max, x_pos)
            y_min = min(y_min, y_pos)
            y_max = max(y_max, y_pos)
            if plot_nodes:
                ax.text(x_pos, y_pos, node.label, fontdict=fontdict, **textkwargs)
        # adjust axes
        if adjust_axes is None:
            adjust_axes = plot_nodes
        if adjust_axes:
            ax.axis([x_min-padding, x_max+padding, y_min-padding, y_max+padding])
