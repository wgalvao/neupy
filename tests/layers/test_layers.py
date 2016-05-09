import math
import unittest

import numpy as np
import theano
import theano.tensor as T

from neupy.utils import asfloat
from neupy import layers, algorithms
from neupy.algorithms import GradientDescent
from neupy.layers.connections import NetworkConnectionError
from neupy.layers import *

from base import BaseTestCase
from data import simple_classification


class LayersBasicsTestCase(BaseTestCase):
    def test_without_output_layer(self):
        with self.assertRaises(NetworkConnectionError):
            GradientDescent(layers.Sigmoid(10) > layers.Sigmoid(1))

    def test_list_of_layers(self):
        bpnet = GradientDescent([Sigmoid(2), Sigmoid(3),
                                 Sigmoid(1), Output(10)])
        self.assertEqual(
            [layer.size for layer in bpnet.all_layers],
            [2, 3, 1, 10]
        )

    def test_layers_iteratinos(self):
        network = GradientDescent((2, 2, 1))

        layers = list(network.all_layers)
        output_layer = layers.pop()

        self.assertIsNone(output_layer.relate_to_layer)
        for layer in layers:
            self.assertIsNotNone(layer.relate_to_layer)

    def test_connection_initializations(self):
        possible_connections = (
            (2, 3, 1),
            [Sigmoid(2), Tanh(3), Output(1)],
            Relu(2) > Tanh(10) > Output(1),
        )

        for connection in possible_connections:
            network = GradientDescent(connection)
            self.assertEqual(len(network.all_layers), 3)

    @unittest.skip("Not ready yet")
    def test_recurrent_connections(self):
        inp = Sigmoid(2)
        hd = [Sigmoid(2), Sigmoid(2)]
        out = Output(1)

        GradientDescent(
            connection=(
                inp > hd[0] > out,
                      hd[0] > hd[1],
                              hd[1] > hd[0],
            )
        )

    def test_activation_layers_without_size(self):
        input_data = np.array([1, 2, -1, 10])
        expected_output = np.array([1, 2, 0, 10])

        layer = layers.Relu()
        actual_output = layer.output(input_data)

        np.testing.assert_array_equal(actual_output, expected_output)


class HiddenLayersOperationsTestCase(BaseTestCase):
    def test_sigmoid_layer(self):
        layer1 = Sigmoid(1)
        self.assertGreater(1, layer1.activation_function(1).eval())

    def test_hard_sigmoid_layer(self):
        layer1 = HardSigmoid(6)

        test_value = asfloat(np.array([[-3, -2, -1, 0, 1, 2]]))
        expected = np.array([[0, 0.1, 0.3, 0.5, 0.7, 0.9]])

        x = T.matrix()
        output = layer1.activation_function(x).eval({x: test_value})

        np.testing.assert_array_almost_equal(output, expected)

    def test_step_layer(self):
        layer1 = Step(1)

        input_vector = theano.shared(np.array([-10, -1, 0, 1, 10]))
        expected = np.array([0, 0, 0, 1, 1])
        output = layer1.activation_function(input_vector).eval()
        np.testing.assert_array_equal(output, expected)

    def test_linear_layer(self):
        layer = Linear(1)
        self.assertEqual(layer.activation_function(1), 1)

    def test_tanh_layer(self):
        layer1 = Tanh(1)
        self.assertGreater(1, layer1.activation_function(1).eval())

    def test_relu_layer(self):
        layer = Relu(1)
        self.assertEqual(0, layer.activation_function(-10))
        self.assertEqual(0, layer.activation_function(0))
        self.assertEqual(10, layer.activation_function(10))

    def test_leaky_relu(self):
        input_data = np.array([[10, 1, 0.1, 0, -0.1, -1]]).T
        expected_output = np.array([[10, 1, 0.1, 0, -0.01, -0.1]]).T
        layer = Relu(1, alpha=0.1)

        actual_output = layer.activation_function(input_data)
        np.testing.assert_array_almost_equal(
            expected_output,
            actual_output
        )

    def test_softplus_layer(self):
        layer = Softplus(1)
        self.assertAlmostEqual(
            math.log(2),
            layer.activation_function(0).eval()
        )

    def test_softmax_layer(self):
        test_input = np.array([[0.5, 0.5, 0.1]])

        softmax_layer = Softmax(3)
        correct_result = np.array([[0.37448695, 0.37448695, 0.25102611]])
        np.testing.assert_array_almost_equal(
            correct_result,
            softmax_layer.activation_function(test_input).eval()
        )

    def test_elu_layer(self):
        test_input = np.array([[10, 1, 0.1, 0, -1]]).T
        expected_output = np.array([
            [10, 1, 0.1, 0, 0.1 * math.exp(-1) - 0.1]
        ]).T

        layer = layers.Elu(alpha=0.1)
        actual_output = layer.activation_function(test_input).eval()

        np.testing.assert_array_almost_equal(
            expected_output,
            actual_output
        )


class PReluTestCase(BaseTestCase):
    def test_invalid_alpha_axes_parameter(self):
        # there are can be specified axis 1, but not 2
        prelu_layer = layers.PRelu(10, alpha_axes=2)
        connection = prelu_layer > layers.Output(10)
        with self.assertRaises(ValueError):
            prelu_layer.initialize()

        # cannot specify alpha per input sample
        prelu_layer = layers.PRelu(10, alpha_axes=0)
        connection = prelu_layer > layers.Output(10)
        with self.assertRaises(ValueError):
            prelu_layer.initialize()

    def test_prelu_layer_param_dense(self):
        prelu_layer = layers.PRelu(10, alpha=0.25)
        connection = prelu_layer > layers.Output(10)
        prelu_layer.initialize()

        alpha = prelu_layer.alpha.get_value()

        self.assertEqual(alpha.shape, (10,))
        np.testing.assert_array_almost_equal(alpha, np.ones(10) * 0.25)

    def test_prelu_layer_param_conv(self):
        input_layer = layers.Input((3, 10, 10))
        conv_layer = layers.Convolution((5, 3, 3))
        prelu_layer = layers.PRelu(alpha=0.25, alpha_axes=(1, 3))
        connection = input_layer > conv_layer > prelu_layer

        conv_layer.initialize()
        prelu_layer.initialize()

        alpha = prelu_layer.alpha.get_value()
        expected_alpha = np.ones((5, 8)) * 0.25

        self.assertEqual(prelu_layer.alpha.get_value().shape, (5, 8))
        np.testing.assert_array_almost_equal(alpha, expected_alpha)

    def test_prelu_output(self):
        prelu_layer = layers.PRelu(1, alpha=0.25)
        connection = prelu_layer > layers.Output(1)
        prelu_layer.initialize()

        input_data = np.array([[10, 1, 0.1, 0, -0.1, -1]]).T
        expected_output = np.array([[10, 1, 0.1, 0, -0.025, -0.25]]).T
        actual_output = prelu_layer.activation_function(input_data).eval()

        np.testing.assert_array_almost_equal(expected_output, actual_output)

    def test_prelu_param_updates(self):
        x_train, _, y_train, _ = simple_classification()
        prelu_layer1 = layers.PRelu(10, alpha=0.25)
        prelu_layer2 = layers.PRelu(20, alpha=0.25)

        gdnet = algorithms.GradientDescent(
            [
                prelu_layer1,
                prelu_layer2,
                layers.Output(1),
            ]
        )

        prelu1_alpha_before_training = prelu_layer1.alpha.get_value()
        prelu2_alpha_before_training = prelu_layer2.alpha.get_value()

        gdnet.train(x_train, y_train, epochs=10)

        prelu1_alpha_after_training = prelu_layer1.alpha.get_value()
        prelu2_alpha_after_training = prelu_layer2.alpha.get_value()

        self.assertTrue(all(np.not_equal(
            prelu1_alpha_before_training,
            prelu1_alpha_after_training,
        )))
        self.assertTrue(all(np.not_equal(
            prelu2_alpha_before_training,
            prelu2_alpha_after_training,
        )))


class TransformationLayersTestCase(BaseTestCase):
    def test_reshape_layer(self):
        # 1D shape
        x = np.random.random((5, 4, 3, 2, 1))

        input_layer = layers.Input((4, 3, 2, 1))
        reshape_layer = layers.Reshape()
        connection = input_layer > reshape_layer

        y = reshape_layer.output(x).eval()
        self.assertEqual(y.shape, (5, 4 * 3 * 2 * 1))

        # 2D shape
        x = np.random.random((5, 20))

        input_layer = layers.Input(20)
        reshape_layer = layers.Reshape((4, 5))
        connection = input_layer > input_layer

        y = reshape_layer.output(x).eval()
        self.assertEqual(y.shape, (5, 4, 5))
