
import tensorflow as tf
from keras.callbacks import ModelCheckpoint
import random

parameters = {
    "max_layers": 5,
    "conv_num_filters": [64],
    "conv_filter_sizes": [2],
    "conv_strides": [1],
    "conv_representation_sizes": [0],
    "pooling_sizes_strides": [(2, 1)],
    "pooling_representation_sizes": [0],
    "dense_consecutive": 2,
    "dense_nodes": [128],
    "classes": 10
}

#creates all possible layers from specified parameters
def get_layers():
  #create convolution layers
  convolutions = []
  for i in parameters['conv_num_filters']:
    for j in parameters['conv_filter_sizes']:
      for k in parameters['conv_strides']:
        for l in parameters['conv_representation_sizes']:
          convolutions.append({'type':'convolution','num_filters':i,'filter_size':j,'stride':k,'representation_size':l})

  #create pooling layers
  poolings = []
  for i in parameters['pooling_sizes_strides']:
    for j in parameters['pooling_representation_sizes']:
      poolings.append({'type':'pooling','pool_size':i[0],'stride':i[1],'representation_size':j})

  #create dense layers
  denses = []
  for i in parameters['dense_nodes']:
    denses.append({'type':'dense','nodes':i})

  #create termination layers
  terminations = [{'type':'softmax','nodes':parameters['classes']}]

  layers = {
      "convolution": convolutions,
      "pooling": poolings,
      "dense": denses,
      "termination": terminations
  }
  return layers

#given current layer, randomly choose next layer
#pass in 0 for current if starting

#NOTES
#-currently does not account for representation size
#-no global average pooling
def add_layer(current):
  #get possible layers and current layer depth
  layers = get_layers()
  current_depth = 0
  if current != 0: 
    current_depth = current['layer_depth']

  #at beginning, can go to convolution or pooling
  if current == 0:
    next_layers = layers['convolution'] + layers['pooling']
  #if at max depth, return termination state
  elif current_depth == parameters['max_layers'] - 1: 
    next_layers = layers['termination']
  #if at convolution, can go to anything
  elif current['type'] == 'convolution':
    next_layers = layers['convolution'] + layers['pooling'] + layers['dense'] + layers['termination']
  #if at pooling, can go to anything but pooling
  elif current['type'] == 'pooling':
    next_layers = layers['convolution'] + layers['dense'] + layers['termination']
  #if at dense and not at max fully connected, can go to another dense or termination
  elif current['type'] == 'dense' and current['consecutive'] != parameters['dense_consecutive']:
    next_layers = layers['dense'] + layers['termination']
  #if at dense and at max fully connected, must go to termination
  elif current['type'] == 'dense' and current['consecutive'] == parameters['dense_consecutive']:
    next_layers = layers['termination']
  
  #randomly select next layer 
  rand = random.randint(0, len(next_layers) - 1)
  next_layer = next_layers[rand]

  #update layer depth 
  next_layer['layer_depth'] = current_depth + 1

  if current == 0:
    return next_layer

  #update consecutive dense layer if next layer is dense
  if next_layer['type'] == 'dense' and current['type'] != 'dense':
    next_layer['consecutive'] = 1
  if next_layer['type'] == 'dense' and current['type'] == 'dense':
    next_layer['consecutive'] = current['consecutive'] + 1
  return next_layer

#generate a random architecture with specified parameters
def generate_architecture():
  layers = [add_layer(0)]
  while (layers[-1]['type'] != 'softmax'):
    layers.append(add_layer(layers[-1]))
  return layers

#given layer dictionary, create TensorFlow layer
def create_tf_layer(layer):
  layer_type = layer['type']
  layer_depth = layer['layer_depth']
  if layer_type == 'convolution' and layer_depth == 1:
    tf_layer = tf.keras.layers.Conv2D(filters=layer['num_filters'], kernel_size=layer['filter_size'], strides=layer['stride'], padding='same', input_shape = (28, 28, 1))
  elif layer_type == 'pooling' and layer_depth == 1:
    tf_layer = tf.keras.layers.MaxPooling2D(pool_size=layer['pool_size'], strides=layer['stride'], input_shape = (28, 28, 1))
  elif layer_type == 'convolution':
    tf_layer = tf.keras.layers.Conv2D(filters=layer['num_filters'], kernel_size=layer['filter_size'], strides=layer['stride'], padding='same')
  elif layer_type == 'pooling':
    tf_layer = tf.keras.layers.MaxPooling2D(pool_size=layer['pool_size'], strides=layer['stride'])
  elif layer_type == 'dense':
    tf_layer = tf.keras.layers.Dense(layer['nodes'], activation='relu')
  elif layer_type == 'softmax':
    tf_layer = tf.keras.layers.Dense(layer['nodes'], activation='softmax')
  return tf_layer

#given list of layer dictionaries, create TensorFlow model
def create_model(architecture):
  model = tf.keras.Sequential()
  for layer in architecture:
    if (layer['type'] == 'dense' and layer['consecutive'] == 1) or layer['type'] == 'softmax':
      model.add(tf.keras.layers.Flatten())
    model.add(create_tf_layer(layer))
  return model

#return validation accuracy of architecture
def evaluate_model(model, batch_size, epochs, x_train, y_train, x_val, y_val):
  model.compile(loss='categorical_crossentropy',
             optimizer='adam',
             metrics=['accuracy'])
  checkpointer = ModelCheckpoint(filepath='model.weights.best.hdf5', verbose = 1, save_best_only=True)
  model.fit(x_train,
         y_train,
         batch_size=batch_size,
         epochs=epochs,
         validation_data=(x_val, y_val),
         callbacks=[checkpointer])
  
  #return validation accuracy
  model.load_weights('model.weights.best.hdf5')
  score = model.evaluate(x_val, y_val, verbose=0)
  print('\n', 'Accuracy:', score[1])
  return score[1]

# Load the fashion-mnist pre-shuffled train data and test data
(x_train, y_train), (x_test, y_test) = tf.keras.datasets.fashion_mnist.load_data()
print("x_train shape:", x_train.shape, "y_train shape:", y_train.shape)

# normalize
x_train = x_train.astype('float32') / 255
x_test = x_test.astype('float32') / 255

# Further break training data into train / validation sets (# put 5000 into validation set and keep remaining 55,000 for train)
(x_train, x_valid) = x_train[5000:], x_train[:5000] 
(y_train, y_valid) = y_train[5000:], y_train[:5000]

# Reshape input data from (28, 28) to (28, 28, 1)
w, h = 28, 28
x_train = x_train.reshape(x_train.shape[0], w, h, 1)
x_valid = x_valid.reshape(x_valid.shape[0], w, h, 1)
x_test = x_test.reshape(x_test.shape[0], w, h, 1)

# One-hot encode the labels
y_train = tf.keras.utils.to_categorical(y_train, 10)
y_valid = tf.keras.utils.to_categorical(y_valid, 10)
y_test = tf.keras.utils.to_categorical(y_test, 10)

# Print training set shape
print("x_train shape:", x_train.shape, "y_train shape:", y_train.shape)

# Print the number of training, validation, and test datasets
print(x_train.shape[0], 'train set')
print(x_valid.shape[0], 'validation set')
print(x_test.shape[0], 'test set')

#generate random architecture and evaluate
architecture = generate_architecture()
model = create_model(architecture)
print(model.summary())
evaluate_model(model, 128, 1, x_train, y_train, x_valid, y_valid)