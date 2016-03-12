#!/usr/bin/env python

from __future__ import print_function

import sys
import json

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils

def get_people_with_hashtags(tweet):
    data = json.loads(tweet)
    try:
        hashtags = ["#" + hashtag["text"] for hashtag in data['entities']['hashtags']]
        # Tweets without hashtags are a waste of time
        if len(hashtags) == 0:
            return ()
        author = data['user']['screen_name']
        mentions = ["@" + user["screen_name"] for user in data['entities']['user_mentions']]
        people = mentions + [author]
        return (people, hashtags)
    except KeyError:
        return ()

def filter_out_unicode(x):
    result = []
    for hashtag in x[1]:
        try:
            result.append(str(hashtag))
        except UnicodeEncodeError:
            pass
    return result

if __name__ == "__main__":
    zkQuorum = "localhost:2181"
    topic = "twitter-stream"

    # User-supplied command arguments
    if len(sys.argv) != 3:
        print("Usage: spark-stream-tweets.py <n_top_hashtags> <seconds_to_run>")
        exit(-1)
    n_top_hashtags = int(sys.argv[1])
    seconds_to_run = int(sys.argv[2])

    sc = SparkContext("local[2]", appName="TwitterStreamKafka")
    ssc = StreamingContext(sc, seconds_to_run)

    tweets = KafkaUtils.createStream(ssc, zkQuorum, "spark-streaming-consumer", {topic: 1})

    # Tweet processing
    lines = tweets.map(lambda x: get_people_with_hashtags(x[1])).filter(lambda x: len(x)>0)
    lines.cache()
    
    #hashtags = lines.filter(lambda x: isinstance(x[1], str))
    hashtags = lines.flatMap(filter_out_unicode).map(lambda x: (x, 1)).reduceByKey(lambda x,y: x+y)
    hashtags = hashtags.map(lambda (k,v): (v,k)).transform(lambda x: x.sortByKey(False))
    hashtags = hashtags.transform(lambda x: x.count())
    hashtags.pprint()

    ssc.start()
    ssc.awaitTermination()

