# Copyright 2022 Kennet Belenky
#
# This file is part of OpenSorts.
#
# OpenSorts is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# OpenSorts is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# OpenSorts. If not, see <https://www.gnu.org/licenses/>.

import math
import random
from collections import namedtuple

import card_comparison
import pivot_expander


def make_readable(card_lookup, values):
    """Makes a singleton or list of card ids human readable"""
    if values == -1:
        return 'BEGINNING'
    elif type(values) is list:
        result = []
        for v in values:
            card = card_lookup[v]
            result.append(make_readable(card_lookup, v))
        return result
    else:
        card = card_lookup[values]
        return f'{card["name"]} [{card["set"]}]'


def flip_direction(direction):
    """Returns the opposite of the direction provided."""
    if direction == 'right':
        return 'left'
    else:
        return 'right'


class FirstPassSorter:
    """
    On the first pass, we can't do a perfect job of sorting because we don't
    yet know what all the cards are or what order they're in. This sorter makes
    choices so as to not make things worse, and when possible, improve the
    sort order by building a set of pivots as we go along.

    It starts by sending all cards to the right basket. When the first out-of-
    order card comes along, it send it to the left basket, and inserts pivots so
    as to ensure that pivot-sorting is maintained.
    """
    def __init__(self, card_lookup):
        self.card_lookup = card_lookup
        # Start with a single, all-inclusive pivot.
        self.pivots = [('UNKNOWN', 'left')]
        self.left_basket = []
        self.right_basket = []
        self.comparer = card_comparison.CardComparer(card_lookup)

    def decide_direction(self, card_id):
        # Find the first pivot that is not less than the card.
        for i in range(len(self.pivots)):
            if not self.comparer.less(self.pivots[i][0], card_id):
                break
        # If the card is already a pivot, do what the pivot says.
        # Otherwise, insert a new pivot for this card, in the opposite direction
        # as the pivot we found.
        if self.pivots[i][0] == card_id:
            d = self.pivots[i][1]
        else:
            d = flip_direction(self.pivots[i][1])
            self.pivots.insert(i, (card_id, d))
        # Keep track of the cards as they go by and which basket they're in.
        if d == 'left':
            self.left_basket.append(card_id)
        else:
            self.right_basket.append(card_id)
        return d

    def get_results(self):
        return self.left_basket + self.right_basket


class SubsequentPassSorter:
    """
    After the first pass, we have full knowledge of the cards, so we can do an
    optimal Log2(N) pass sort algorithm. The algorithm we use is basically a
    QuickSort, but we start at the leaves and work backwards to the trunk
    (where QuickSort does the most coarse pivot first, we do it last).

    We can do even better than that if we can recognize subgroups of cards that
    will be contiguous in the final sort order and are already in the correct
    order (although likely non-contiguous). Those subgroups can be treated as
    a single unit, with a single pivot, cutting down on the total number of
    pivots
    """
    def __init__(self, card_lookup, hopper):
        self.card_lookup = card_lookup
        self.comparer = card_comparison.CardComparer(card_lookup)
        self.pivot_expander = pivot_expander.PivotExpander(card_lookup)
        self.pivots = self.compute_pivots(hopper)

    def print_pivots(self):
        print('====== Pivots ======')
        for v in self.pivots:
            print(make_readable(self.card_lookup, v))
        print('====================')

    def find_pivot(self, current):
        """Finds the first pivot greater than or equal to the current card."""
        # This could theoretically be sped up with a binary search, but honestly
        # it's so fast already that it's no problem.
        for i in range(len(self.pivots)):
            if not self.comparer.less(self.pivots[i], current):
                return i
        return len(self.pivots)

    def compute_pivots(self, hopper):
        """
        Takes the contents of the hopper from the first pass and computes an
        optimal set of pivots for sorting.
        """
        Range = namedtuple('Range', 'min max')
        card_ranges = dict()
        # For each unique card, find its first and last location in the hopper.
        for i in range(len(hopper)):
            value = hopper[i]
            if value in card_ranges.keys():
                card_ranges[value] = Range(card_ranges[value].min, i)
            else:
                card_ranges[value] = Range(i, i)
        # Sort the unique cards by the position they should be in when we're
        # done sorting.
        card_ranges = sorted(
            card_ranges.items(),
            key=lambda t: card_comparison.ComparableCard(self.comparer, t[0]))
        print('Target output sequence:')
        for c, _ in card_ranges:
            d = self.card_lookup[c]
            print(f'{d["name"]} [{d["set"]}]')

        pivots = []
        # Add the cards to the list of pivots, in order, dropping all but the
        # last card in each sorted run.
        for i in range(len(card_ranges) - 1):
            if card_ranges[i + 1][1].min < card_ranges[i][1].max:
                pivots.append(card_ranges[i][0])
        # Always add the last card as a pivot
        pivots.append(card_ranges[-1][0])

        # Insert dummy pivots at the beginning until we have a power of 2
        # number of pivots.
        while len(pivots) not in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512):
            pivots.insert(0, -1)
        return self.pivot_expander.expand_pivots(pivots)

    def decide_direction(self, card_id):
        # If it's an even-numbered pivot, send it left, otherwise right.
        i = self.find_pivot(card_id)
        if i % 2 == 0:
            d = 'left'
        else:
            d = 'right'
        return d

    def reload_hopper(self):
        # Whenever we reload the hopper, remove every second pivot.
        self.pivots = self.pivot_expander.expand_pivots(self.pivots[1::2])

    def is_sorted(self):
        # The cards are sorted when there's no more pivots left.
        return len(self.pivots) <= 1
