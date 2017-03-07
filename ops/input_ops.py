# -*- coding: utf-8 -*-

#Author: Jay Yip
#Date 04Mar2017

"""Batching, padding and masking the input sequence and output sequence"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


import tensorflow as tf

def parse_example_queue(example_queue, context_feature_name, tag_feature_name):
  """ Read one example.
  This function read one example and return context sequence and tag sequence
  correspondingly. 

  Args:
    filename_queue: A filename queue returned by string_input_producer
    context_feature_name: Context feature name in TFRecord. Set in ModelConfig
    tag_feature_name: Tag feature name in TFRecord. Set in ModelConfig

  Returns:
    input_seq: An int32 Tensor with different length.
    tag_seq: An int32 Tensor with different length.
  """
  #Read TFRecord from filename queue
  #_, serialized_example = reader.read(filename_queue)
  serialized_example = example_queue.dequeue()

  #Parse one example
  _, features = tf.parse_single_sequence_example(serialized_example, 
    sequence_features = {
      context_feature_name: tf.FixedLenSequenceFeature([], dtype=tf.int64),
      tag_feature_name: tf.FixedLenSequenceFeature([], dtype = tf.int64)
    })

  return (features[context_feature_name], features[tag_feature_name])

def example_queue_shuffle(reader, filename_queue, is_training, example_queue_name = 'example_queue', capacity = 50000, num_reader_threads = 1):
  """
  This function shuffle the examples within the filename queues. Since there's no 
  padding option in shuffle_batch, we have to manually shuffle the example queue.

  The process is given as below.
  create filename queue >> read examples from filename queue >> enqueue example to example queue(RandomShuffleQueue)

  However, this is not totally random shuffle since the memory limiation. Therefore, 
  we need to specify a capacity of the example queue.

  Args:
    reader: A TFRecord Reader
    filename_queue: A queue generated by string_input_producer
    is_traning: If not training then use FIFOqueue(No need to shuffle).
    example_queue_name: Name of the example queue
    capacity: Value queue capacity. Should be large enough for better mixing
    num_reader_threads: Number of thread to enqueue the value queue

  Returns:
    example_queue: An example queue that is shuffled. Ready for parsing and batching.
  """

  #Init queue
  if is_training:
    example_queue = tf.RandomShuffleQueue(
        capacity=capacity,
        min_after_dequeue=capacity % 2,
        dtypes=[tf.string],
        name="random_" + example_queue_name)
  else:
    example_queue = tf.FIFOQueue(
        capacity=capacity, dtypes=[tf.string], name="fifo_" + example_queue_name)

  #Manually create ops to enqueue
  enqueue_example_ops = []
  for _ in range(num_reader_threads):
    _, example = reader.read(filename_queue)
    enqueue_example_ops.append(example_queue.enqueue([example]))

  #Add queue runner
  tf.train.queue_runner.add_queue_runner(tf.train.queue_runner.QueueRunner(
      example_queue, enqueue_example_ops))
  tf.summary.scalar(
      "queue/%s/fraction_of_%d_full" % (example_queue.name, capacity),
      tf.cast(example_queue.size(), tf.float32) * (1. / capacity))

  return example_queue


