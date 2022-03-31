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

import cv2

import numpy as np

from numpy.linalg import inv


# based on https://engineering.purdue.edu/~bethel/503hw1.pdf
def transform_formula(width, height, top_left, top_right, bottom_left,
                      bottom_right):
    def x_row_from_point(source, dest):
        x = dest[0]
        y = dest[1]
        r = source[0]
        c = source[1]
        return [x, y, 1, 0, 0, 0, -1 * r * x, -1 * r * y]

    def y_row_from_point(source, dest):
        x = dest[0]
        y = dest[1]
        r = source[0]
        c = source[1]
        return [0, 0, 0, x, y, 1, -1 * c * x, -1 * c * y]

    mat = [
        x_row_from_point(top_left, (0, 0)),
        y_row_from_point(top_left, (0, 0)),
        x_row_from_point(top_right, (width, 0)),
        y_row_from_point(top_right, (width, 0)),
        x_row_from_point(bottom_left, (0, height)),
        y_row_from_point(bottom_left, (0, height)),
        x_row_from_point(bottom_right, (width, height)),
        y_row_from_point(bottom_right, (width, height))
    ]
    vec = [
        top_left[0],  #
        top_left[1],  #
        top_right[0],  #
        top_right[1],  #
        bottom_left[0],  #
        bottom_left[1],  #
        bottom_right[0],  #
        bottom_right[1]
    ]
    return mat, vec


def keypoints_to_transform(width, height, top_left, top_right, bottom_left,
                           bottom_right):
    mat, vec = transform_formula(width, height, top_left, top_right,
                                 bottom_left, bottom_right)
    mat = np.array(mat, dtype=np.single)
    vec = np.array(vec, dtype=np.single)
    transform_vector = inv(mat).dot(vec)
    return transform_vector


# Lifted from: https://stackoverflow.com/questions/57030125
def automatic_brightness_and_contrast(image, clip_hist_percent=1):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Calculate grayscale histogram
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist_size = len(hist)

    # Calculate cumulative distribution from the histogram
    accumulator = []
    accumulator.append(float(hist[0]))
    for index in range(1, hist_size):
        accumulator.append(accumulator[index - 1] + float(hist[index]))

    # Locate points to clip
    maximum = accumulator[-1]
    clip_hist_percent *= (maximum / 100.0)
    clip_hist_percent /= 2.0

    # Locate left cut
    minimum_gray = 0
    while accumulator[minimum_gray] < clip_hist_percent:
        minimum_gray += 1

    # Locate right cut
    maximum_gray = hist_size - 1
    while accumulator[maximum_gray] >= (maximum - clip_hist_percent):
        maximum_gray -= 1

    # Calculate alpha and beta values
    alpha = 255 / (maximum_gray - minimum_gray)
    beta = -minimum_gray * alpha
    '''
    # Calculate new histogram with desired range and show histogram 
    new_hist = cv2.calcHist([gray],[0],None,[256],[minimum_gray,maximum_gray])
    plt.plot(hist)
    plt.plot(new_hist)
    plt.xlim([0,256])
    plt.show()
    '''

    auto_result = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    return (auto_result, alpha, beta)
