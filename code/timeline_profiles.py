#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
from datetime import datetime
from pyspark.sql import SparkSession
import pyspark.sql.functions as F


# In[ ]:


print('Date:',datetime.today().strftime('%d%m%Y'))
spark = SparkSession.builder.config("spark.sql.files.ignoreCorruptFiles","true") .config("spark.hadoop.dfs.replication","1") .config("spark.serializer","org.apache.spark.serializer.KryoSerializer") .config("spark.yarn.appMasterEnv.LANG","en_US.UTF-8") .config("spark.executorEnv.LANG","en_US.UTF-8") .config("spark.driver.extraJavaOptions","-Duser.timezone=UTC") .config("spark.executor.extraJavaOptions","-Duser.timezone=UTC") .config("spark.sql.session.timeZone","UTC") .config("spark.sql.broadcastTimeout",-1) .config("spark.driver.maxResultSize",0) .getOrCreate()
print(spark.sparkContext.getConf().getAll())
path_to_data = "/user/spf248/twitter_data_collection/data"
print(path_to_data)


# In[ ]:


def profiles(df1,df2):
    tmp1 = df1.groupby('user_id').agg(F.max('tweet_timestamp').alias('tweet_timestamp'))
    tmp2 = df1.join(tmp1,on=['user_id','tweet_timestamp'])
    tmp2 = tmp2.drop_duplicates(subset=['user_id'])
    tmp3 = tmp2.join(F.broadcast(df2),on='user_location',how="left")
    tmp3 = tmp3.select([
    'tweet_id', 
    'tweet_timestamp', 
    'user_timestamp', 
    'user_default_profile_image', 
    'user_description', 
    'user_favourites_count', 
    'user_followers_count', 
    'user_friends_count', 
    'user_geo_enabled', 
    'user_id', 
    'user_location', 
    'user_name', 
    'user_notifications', 
    'user_profile_image_url_https', 
    'user_protected', 
    'user_screen_name', 
    'user_statuses_count',
    'user_url', 
    'user_verified',
    'country_short'])
    tmp3.write.mode("overwrite").parquet(os.path.join(path_to_data,"user_timeline","profiles"))


# In[ ]:


test = "part-0000*.snappy.parquet"
df1 = spark.read.parquet(os.path.join(path_to_data,"user_timeline","extract"))
df2 = spark.read.parquet(os.path.join(path_to_data,"preprocessed","locations","locations_geocoded.parquet")).select("user_location","country_short")
profiles(df1,df2)

