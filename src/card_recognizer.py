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

import pickle
import numpy as np
import tensorflow as tf
import tensorflow.keras.applications as applications
import random

import prof_timer

from collections import namedtuple

CardDescriptor = namedtuple(
    'CardDescriptor', ' '.join(
        ['illustration_id', 'is_full_art', 'is_showcase', 'is_extended_art']))

CardIdentifier = namedtuple('CardIdentifier',
                            ' '.join(['name', 'set_code', 'face_index']))


class Recognizer:
    def __init__(self, catalog):
        self.catalog = catalog
        print('Loading card recognizer.')
        # The embedding model turns an image of a card into an embedding vector.
        self.embedding_interpreter = tf.lite.Interpreter(
            model_path='embedding_model.tflite')
        self.embedding_interpreter.allocate_tensors()
        self.embedding_input_details = self.embedding_interpreter.get_input_details(
        )[0]
        self.embedding_output_details = self.embedding_interpreter.get_output_details(
        )[0]
        self.image_dimensions = (self.embedding_input_details['shape'][1],
                                 self.embedding_input_details['shape'][2])
        print(f'Model image dimensions: {self.image_dimensions}')

        # The embedding dictionary maps embedding vectors to card ids.
        with open('embedding_dictionary.pickle', 'rb') as handle:
            embedding_dictionary = pickle.load(handle)
        # Turn the embedding dictionary into a numpy matrix for efficiency.
        self.card_ids = []
        embedding_list = []
        for card_id, embedding in embedding_dictionary.items():
            self.card_ids.append(card_id)
            embedding_list.append(embedding)
        self.embedding_matrix = np.array(embedding_list)

    def recognize_by_embedding(self, image):
        # Scale the image values to what the network expects.
        with prof_timer.PerfTimer('preprocess'):
            image = applications.mobilenet_v2.preprocess_input(image * 255.0)

        # Generate the embedding from the image.
        with prof_timer.PerfTimer('predict embedding'):
            image = np.expand_dims(image, axis=0).astype(np.single)
            self.embedding_interpreter.set_tensor(
                self.embedding_input_details['index'], image)
            self.embedding_interpreter.invoke()
            target_embedding = self.embedding_interpreter.get_tensor(
                self.embedding_output_details["index"])[0]
        # Find the card with the nearest embedding vector.
        with prof_timer.PerfTimer('nearest'):
            distances = 1 - np.dot(self.embedding_matrix,
                                   np.squeeze(target_embedding))
            nearest = np.argmin(distances)
        distance = distances[nearest]
        card_id = self.card_ids[nearest]
        return card_id, distance

    def recognize(self, large_image):
        small_image = tf.image.resize(large_image,
                                      self.image_dimensions,
                                      antialias=True)
        with prof_timer.PerfTimer('embedding'):
            card_id, distance = self.recognize_by_embedding(small_image)
        return card_id, distance
