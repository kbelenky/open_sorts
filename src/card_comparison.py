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


def map_rarity(rarity):
    # Sent this to True to lump commons, uncommons, rares and mythics
    # all together. This is useful for testing.
    #
    # Usually you want it to be false so that cards of different rarities are
    # sorted out.
    DISREGARD_RARITY = False
    if DISREGARD_RARITY:
        if rarity == 'token':
            return rarity
        if rarity == 'basic_land':
            return rarity
        else:
            return 'aaaa'
    else:
        return rarity


class ComparableCard:
    """Adapts a card id to be a comparable object."""
    def __init__(self, comparer, obj):
        self.comparer = comparer
        self.obj = obj

    def __lt__(self, other):
        return self.comparer.less(self.obj, other.obj)

    def __gt__(self, other):
        return self.obj != other.obj and not self.comparer.less(
            self.obj, other.obj)

    def __eq__(self, other):
        return self.obj == other.obj

    def __le__(self, other):
        return self.obj == other.obj or self.comparer.less(self.obj, other.obj)

    def __ge__(self, other):
        return self.comparer.less(other.obj, self.obj)

    def __ne__(self, other):
        return self.obj != other.obj

    def card_id(self):
        return self.obj


class CardComparer:
    """
    Defines the order that cards will be sorted in.
    """
    def __init__(self, cards_by_id):
        self.cards_by_id = cards_by_id

    def less(self, left, right):
        if left == right:
            return False
        elif left == 'UNKNOWN':
            return False
        elif right == 'UNKNOWN':
            return True
        elif right == -1:
            return False
        elif left == -1:
            return True

        left = self.cards_by_id[left]
        right = self.cards_by_id[right]
        SIMPLY_ALPHABETIZE = False
        if SIMPLY_ALPHABETIZE:
            return left['name'] > right['name']

        if map_rarity(left['rarity']) != map_rarity(right['rarity']):
            return map_rarity(left['rarity']) > map_rarity(right['rarity'])

        if map_rarity(left['rarity']) == 'basic land':
            if left['name'] != right['name']:
                return left['name'] > right['name']
            if left['artist'] != right['artist']:
                return left['artist'] > right['artist']
            if left['illustration_id'] != right['illustration_id']:
                return left['illustration_id'] > right['illustration_id']
            if left['full_art'] != right['full_art']:
                return left['full_art'] > right['full_art']
            if left['set'] != right['set']:
                return left['set'] > right['set']
            if left['id'] != right['id']:
                return left['id'] > right['id']
        if map_rarity(left['rarity']) == 'token':
            if left['color_category'] != right['color_category']:
                return left['color_category'] > right['color_category']
            if left['name'] != right['name']:
                return left['name'] > right['name']
            if left['artist'] != right['artist']:
                return left['artist'] > right['artist']
            if left['illustration_id'] != right['illustration_id']:
                return left['illustration_id'] > right['illustration_id']
            if left['full_art'] != right['full_art']:
                return left['full_art'] > right['full_art']
            if left['set'] != right['set']:
                return left['set'] > right['set']
            if left['id'] != right['id']:
                return left['id'] > right['id']
        else:
            if left['color_category'] != right['color_category']:
                return left['color_category'] > right['color_category']
            if left['name'] != right['name']:
                return left['name'] > right['name']
            if left['full_art'] != right['full_art']:
                return left['full_art'] > right['full_art']
            if left['artist'] != right['artist']:
                return left['artist'] > right['artist']
            if left['illustration_id'] != right['illustration_id']:
                return left['illustration_id'] > right['illustration_id']
            if left['set'] != right['set']:
                return left['set'] > right['set']
            if left['id'] != right['id']:
                return left['id'] > right['id']
        return False
