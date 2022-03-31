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

import card_comparison


class PivotExpander:
    """
    Pivot expansion solves a problem that can occur when cards are recognized
    differently on different sets.

    The recognizer is quite good at recognizing the name, artwork and frame of 
    a card, but often confuses reprintings that share the same name, artwork and
    frame. This can have an outsized effect when a card that is a pivot is
    recognized differently. It can lead to the card being assigned to the wrong
    side of the pivot, going to the wrong bucket, and often ending up _way_ out
    of position in the final sort order.

    There's an example of this happening at 4:57 in this video:
    https://youtu.be/nCjfuDlN2IE

    The solution is to, whenever possible, shift the pivots so that all cards
    with the same name, artwork and frame, will end up on the same side of the
    pivot. That way, even if the card is misrecognized, it will still mostly end
    up in the right place.

    The keyword there is "whenever possible". You could have two different
    printings of the same card being consecutive pivots. In that case it would
    be wrong to expand one of them. So, we have to expand the pivots for each
    pass, every time the pivots are halved, because new expansions may become
    possible.
    """
    def __init__(self, cards_by_id):
        cards_by_key = {}
        print('Building equivalency map')
        # Build a map, the keys are a tuple of (name, illustration id, full art)
        # and the values are a list of all cards that fit.
        for id, card in cards_by_id.items():
            name = card['name']
            illustration_id = card['illustration_id']
            full_art = card['full_art']
            key = (name, illustration_id, full_art)
            if key not in cards_by_key.keys():
                cards_by_key[key] = [id]
            else:
                cards_by_key[key].append(id)

        comparer = card_comparison.CardComparer(cards_by_id)
        # For every key that has more than one card, the pivot expansion is
        # the last card (by sorting) in the list.
        print('Computing pivot expansion map')
        self.expansion_map = {}
        for key, cards in cards_by_key.items():
            first_card_with_key = sorted([
                card_comparison.ComparableCard(comparer, card_id)
                for card_id in cards
            ])[-1].card_id()
            if len(cards) > 1:
                for card_id in cards:
                    self.expansion_map[card_id] = first_card_with_key

    def expand_pivot(self, current, previous):
        # We can only expand the pivot if the current pivot is different
        # from the previous pivot.
        if current == -1:
            return current
        if previous == -1:
            return current
        if current not in self.expansion_map.keys():
            return current
        if previous not in self.expansion_map.keys():
            print(
                f'Expanding pivot {current} -> {self.expansion_map[current]}')
            return self.expansion_map[current]
        if self.expansion_map[previous] == self.expansion_map[current]:
            return current
        print(f'Expanding pivot {current} -> {self.expansion_map[current]}')
        return self.expansion_map[current]

    def expand_pivots(self, pivots):
        # We can never expand the first pivot.
        result = [pivots[0]]
        # Expand all subsequent pivots (if possible).
        for current, previous in zip(pivots[1:], pivots[0:-1]):
            result.append(self.expand_pivot(current, previous))
        return result
