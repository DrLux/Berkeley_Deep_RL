import tensorflow as tf
import numpy as np

import utils


class ModelBasedPolicy(object):

    def __init__(self,
                 env,
                 init_dataset,
                 horizon=20,
                 num_random_action_selection=4096,
                 nn_layers=1):
        self._cost_fn = env.cost_fn
        self._state_dim = env.observation_space.shape[0]
        self._action_dim = env.action_space.shape[0]
        self._action_space_low = env.action_space.low
        self._action_space_high = env.action_space.high
        self._init_dataset = init_dataset
        self._horizon = horizon
        self._num_random_action_selection = num_random_action_selection
        self._nn_layers = nn_layers
        self._learning_rate = 1e-3

        self._sess, self._state_ph, self._action_ph, self._next_state_ph,\
            self._next_state_pred, self._loss, self._optimizer, self._best_action = self._setup_graph()

    def _setup_placeholders(self):
        """
            Creates the placeholders used for training, prediction, and action selection

            returns:
                state_ph: current state
                action_ph: current_action
                next_state_ph: next state

            implementation details:
                (a) the placeholders should have 2 dimensions,
                    in which the 1st dimension is variable length (i.e., None)
        """
        ### PROBLEM 1
        ### YOUR CODE HERE
        state_ph = tf.placeholder(shape=[None, self._state_dim], name='state', dtype=tf.float32)
        action_ph = tf.placeholder(shape=[None, self._action_dim], name='action', dtype=tf.float32)
        next_state_ph = tf.placeholder(shape=[None, self._state_dim], name='next_state', dtype=tf.float32)
        
        return state_ph, action_ph, next_state_ph

    def _dynamics_func(self, state, action, reuse):
        """
            Takes as input a state and action, and predicts the next state

            returns:
                next_state_pred: predicted next state

            implementation details (in order):
                (a) Normalize both the state and action by using the statistics of self._init_dataset and
                    the utils.normalize function
                (b) Concatenate the normalized state and action
                (c) Pass the concatenated, normalized state-action tensor through a neural network with
                    self._nn_layers number of layers using the function utils.build_mlp. The resulting output
                    is the normalized predicted difference between the next state and the current state
                (d) Unnormalize the delta state prediction, and add it to the current state in order to produce
                    the predicted next state
        """
        
        # Normalize state and action
        state_norm = utils.normalize(state, self._init_dataset.state_mean, self._init_dataset.state_std) 
        action_norm = utils.normalize(action, self._init_dataset.action_mean, self._init_dataset.action_std)

        # Concatenate the normalized state and action
        input_layer = tf.concat([state_norm, action_norm], axis=1)

        # Send normalized data to NN
        delta_pred_norm = utils.build_mlp(input_layer,self._state_dim,scope='dynamics_func',n_layers=self._nn_layers,reuse=reuse)
        
        # Unnormalize output network
        delta_pred = utils.unnormalize(delta_pred_norm, self._init_dataset.delta_state_mean, self._init_dataset.delta_state_std)
        
        # next state is calculated by summing state with is delta
        next_state_pred = state + delta_pred
        
        return next_state_pred

    def _setup_training(self, state_ph, next_state_ph, next_state_pred):
        """
            Takes as input the current state, next state, and predicted next state, and returns
            the loss and optimizer for training the dynamics model

            returns:
                loss: Scalar loss tensor
                optimizer: Operation used to perform gradient descent

            implementation details (in order):
                (a) Compute both the actual state difference and the predicted state difference
                (b) Normalize both of these state differences by using the statistics of self._init_dataset and
                    the utils.normalize function
                (c) The loss function is the mean-squared-error between the normalized state difference and
                    normalized predicted state difference
                (d) Create the optimizer by minimizing the loss using the Adam optimizer with self._learning_rate

        """
        ### PROBLEM 1
        ### YOUR CODE HERE

        # (a) Compute both the actual state difference and the predicted state difference
        state_difference = state_ph - next_state_ph
        predicted_state_difference = state_ph - next_state_pred

        # (b) Normalize both of these state differences
        normalized_state_diff = utils.normalize(state_difference,self._init_dataset.state_mean,self._init_dataset.state_std)
        normalized_pred_state_diff = utils.normalize(predicted_state_difference,self._init_dataset.state_mean,self._init_dataset.state_std)

        # (c) The loss function is the mean-squared-error between the normalized state difference and normalized predicted state difference
        loss = tf.compat.v1.losses.mean_squared_error(normalized_state_diff,normalized_pred_state_diff)

        # (d) Create the optimizer by minimizing the loss using the Adam optimizer with self._learning_rate
        optimizer = tf.compat.v1.train.AdamOptimizer(self._learning_rate).minimize(loss)

        return loss, optimizer

    def _setup_action_selection(self, state_ph):
        """
            Computes the best action from the current state by using randomly sampled action sequences
            to predict future states, evaluating these predictions according to a cost function,
            selecting the action sequence with the lowest cost, and returning the first action in that sequence

            returns:
                best_action: the action that minimizes the cost function (tensor with shape [self._action_dim])

            implementation details (in order):
                (a) We will assume state_ph has a batch size of 1 whenever action selection is performed -> mi da solo lo stato iniziale
                (b) Randomly sample uniformly self._num_random_action_selection number of action sequences,
                    each of length self._horizon -> genera self._num_random_action_selection sequenze di azioni casuali lunghe ognuna self._horizon
                (c) Starting from the input state, unroll each action sequence using your neural network
                    dynamics model -> esegui le sequenza casuali nel modello appreso (NN)
                (d) While unrolling the action sequences, keep track of the cost of each action sequence
                    using self._cost_fn -> ad ogni step compiuto calcolari il costo
                (e) Find the action sequence with the lowest cost, and return the first action in that sequence -> ritorna solo la prima azione della sequenza migliore

            Hints:
                (i) self._cost_fn takes three arguments: states, actions, and next states. These arguments are
                    2-dimensional tensors, where the 1st dimension is the batch size and the 2nd dimension is the
                    state or action size
                (ii) You should call self._dynamics_func and self._cost_fn a total of self._horizon times -> fai tutti 1 step alla volta in parallelo tra tutte le random shoot                                                        
                (iii) Use tf.random_uniform(...) to generate the random action sequences

                faccio già subito il filtro e prendo solo l' azione migliore
        """
        ### PROBLEM 2
        ### YOUR CODE HERE
        # Take count of total cost of each random path
        costs = np.zeros((self._num_random_action_selection,))
        

        #Generates all the random shoots
        shoots = tf.random.uniform([self._horizon*self._num_random_action_selection, self._action_dim],minval=self._action_space_low,maxval=self._action_space_high,dtype=tf.dtypes.float32)      

        # Isolate the first Actions of each path
        first_actions = shoots[0:self._num_random_action_selection]
        
        # Count how many action in shoots as sampled and used
        action_sampled = 0

        current_state = tf.stack([state_ph[0]] * self._num_random_action_selection)
        new_states = None
        for i in range(self._horizon):
            current_actions = shoots[action_sampled:action_sampled+self._num_random_action_selection]
            action_sampled += self._num_random_action_selection
                        
            new_states = self._dynamics_func(current_state, current_actions, True)
            
            costs += self._cost_fn(current_state, current_actions, new_states)

            current_state = new_states

        # Find index of the best path
        best_path_index = tf.math.argmin(costs)

        # Extract the best action from the list of first_actions
        best_action = first_actions[best_path_index]

        return best_action
        

    def _setup_graph(self):
        """
        Sets up the tensorflow computation graph for training, prediction, and action selection

        The variables returned will be set as class attributes (see __init__)
        """
        tf_config = tf.ConfigProto()
        tf_config.gpu_options.allow_growth = True
        sess = tf.Session(config=tf_config)

        ### PROBLEM 1
        ### YOUR CODE HERE
        state_ph,action_ph,next_state_ph = self._setup_placeholders()
        next_state_pred = self._dynamics_func(state_ph, action_ph, reuse=False) 

        loss, optimizer = self._setup_training(state_ph, next_state_ph, next_state_pred)
        
        ### PROBLEM 2
        ### YOUR CODE HERE
        best_action = self._setup_action_selection(state_ph)

        sess.run(tf.global_variables_initializer())

        return sess, state_ph, action_ph, next_state_ph, \
                next_state_pred, loss, optimizer, best_action

    def train_step(self, states, actions, next_states):
        """
        Performs one step of gradient descent

        returns:
            loss: the loss from performing gradient descent
        """

        ### PROBLEM 1
        ### YOUR CODE HERE
        feed_dict = {
            self._state_ph: states, 
            self._action_ph: actions, 
            self._next_state_ph: next_states
        }
        loss, _ = self._sess.run([self._loss, self._optimizer], feed_dict=feed_dict)
        
        return loss

    def predict(self, state, action):
        """
        Predicts the next state given the current state and action

        returns:
            next_state_pred: predicted next state

        implementation detils:
            (i) The state and action arguments are 1-dimensional vectors (NO batch dimension)
        """
        assert np.shape(state) == (self._state_dim,)
        assert np.shape(action) == (self._action_dim,)

        ### PROBLEM 1
        ### YOUR CODE HERE
        next_state_pred = self._sess.run(self._next_state_pred, feed_dict={self._state_ph: [state], self._action_ph: [action]})[0] 

        assert np.shape(next_state_pred) == (self._state_dim,)
        return next_state_pred

    def get_action(self, state):
        """
        Computes the action that minimizes the cost function given the current state

        returns:
            best_action: the best action
        """
        assert np.shape(state) == (self._state_dim,)

        ### PROBLEM 2
        ### YOUR CODE HERE
        best_action = self._sess.run(self._best_action, feed_dict={self._state_ph: [state]})

        assert np.shape(best_action) == (self._action_dim,)
        return best_action
