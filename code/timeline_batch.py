#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
from datetime import datetime
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from pyspark.sql.types import *


# In[ ]:


print('Date:',datetime.today().strftime('%Y-%m-%d'))
spark = SparkSession.builder.config("spark.serializer","org.apache.spark.serializer.KryoSerializer") .config("spark.hadoop.dfs.replication","1") .config("spark.sql.files.ignoreCorruptFiles","true") .config("spark.yarn.appMasterEnv.LANG","en_US.UTF-8") .config("spark.executorEnv.LANG","en_US.UTF-8") .config("spark.driver.extraJavaOptions","-Duser.timezone=UTC") .config("spark.executor.extraJavaOptions","-Duser.timezone=UTC") .config("spark.sql.session.timeZone","UTC") .config("spark.sql.broadcastTimeout",-1) .config("spark.sql.shuffle.partitions","2000") .config("spark.default.parallelism","2000") .getOrCreate()
print(spark.sparkContext.getConf().getAll())
path_to_data = "/user/spf248/twitter_data_collection/data"
print(path_to_data)


# In[ ]:


df1 = spark.read.parquet(os.path.join(path_to_data,"user_timeline","profiles")).select("user_id","country_short","tweet_id","tweet_timestamp")
df2 = spark.read.parquet(os.path.join(path_to_data,"lookup_users","profiles")).select("user_id","country_short")
df3 = spark.read.parquet(os.path.join(path_to_data,"user_timeline","snowball")).selectExpr("user_id","country_short","n_users")


# In[ ]:


# Store timeline users' latest tweet
df1 = df1.withColumn("tweet_timestamp",F.to_timestamp("tweet_timestamp"))
tmp1 = df1.select("user_id","tweet_id","tweet_timestamp")
# Store their geocode
tmp2 = df1.select("user_id","country_short")
# Combine all unique geocodes
tmp2 = tmp2.unionByName(df2)
tmp2 = tmp2.drop_duplicates(subset=["user_id","country_short"])
tmp2 = tmp2.withColumn("n_users", F.lit(None).cast(LongType()))
# Combine snowballed geocodes removing users geocodes
tmp3 = df3.join(tmp2.select("user_id","country_short"),on=["user_id","country_short"],how="left_anti")
# A user can be included for being geocoded in a country or mentioned by users in another country
tmp2 = tmp2.unionByName(tmp3)
# Drop existing timelines if no geocode is present (user could be pulled again later on if they reappear with a new geocode)
tmp2 = tmp2.where(tmp2["country_short"].isNotNull())
# Merge back with tweet_ids (dropping users with timeline but no geocode)
tmp2 = tmp2.join(tmp1,on="user_id",how="left")
tmp2.write.mode("overwrite").parquet(os.path.join(path_to_data,"user_timeline","batch"))

