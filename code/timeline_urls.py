#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
from datetime import datetime
from pyspark.sql import SparkSession
import pyspark.sql.functions as F


# In[ ]:


print('Date:',datetime.today().strftime('%Y-%m-%d'))
spark = SparkSession.builder.config("spark.serializer","org.apache.spark.serializer.KryoSerializer") .config("spark.sql.files.ignoreCorruptFiles","true") .config("spark.sql.broadcastTimeout",-1) .config("spark.yarn.appMasterEnv.LANG","en_US.UTF-8") .config("spark.executorEnv.LANG","en_US.UTF-8") .config("spark.driver.extraJavaOptions","-Duser.timezone=UTC") .config("spark.executor.extraJavaOptions","-Duser.timezone=UTC") .config("spark.sql.session.timeZone","UTC") .config("spark.sql.shuffle.partitions","2000") .config("spark.default.parallelism","2000") .getOrCreate()
print(spark.sparkContext.getConf().getAll())
path_to_data = "/user/spf248/twitter_data_collection/data"
print(path_to_data)


# In[ ]:


def urls(df,countries_short):
    for country_short in countries_short:
        tmp = df.where(df["country_short"]==country_short)
        tmp = tmp.withColumn('url',F.explode('tweet_urls'))
        tmp = tmp.drop_duplicates(subset=["tweet_id"])
        tmp = tmp.select("tweet_id","url")
        tmp.write.mode("overwrite").parquet(os.path.join(path_to_data,"preprocessed","urls",country_short))


# In[ ]:


# test = "part-99999-869bc081-101d-4975-80b6-04be53b82ee0-c000.snappy.parquet"
df1 = spark.read.parquet(os.path.join(path_to_data,"user_timeline","extract")).select("tweet_id","user_location","tweet_urls")
df2 = spark.read.parquet(os.path.join(path_to_data,"preprocessed","locations","locations_geocoded.parquet")).select("user_location","country_short")
df = df1.join(F.broadcast(df2), on="user_location")
countries_short = ["NG"]
urls(df,countries_short)

