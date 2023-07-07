#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
from datetime import datetime
from pyspark.sql import SparkSession
import pyspark.sql.functions as F


# In[ ]:


print('Date:',datetime.today().strftime('%d%m%Y'))
spark = SparkSession.builder.config("spark.sql.files.ignoreCorruptFiles","true") .config("spark.hadoop.dfs.replication","1") .config("spark.serializer","org.apache.spark.serializer.KryoSerializer") .config("spark.yarn.appMasterEnv.LANG","en_US.UTF-8") .config("spark.executorEnv.LANG","en_US.UTF-8") .config("spark.driver.extraJavaOptions","-Duser.timezone=UTC") .config("spark.executor.extraJavaOptions","-Duser.timezone=UTC") .config("spark.sql.session.timeZone","UTC") .getOrCreate()
print(spark.sparkContext.getConf().getAll())
path_to_data = "/user/spf248/twitter_data_collection/data"
print(path_to_data)


# In[ ]:


# output data: 1M rows ~ 100mB 
def extract(df,numOfPartitions):
    tmp1 = df.selectExpr(
    'id_str as tweet_id',
    'created_at as tweet_timestamp',
    'lang as tweet_lang',
    'full_text as tweet_text',
    'retweeted_status.user.id_str as tweet_retweeted_user_id',
    'in_reply_to_user_id_str as tweet_in_reply_to_user_id',
    'entities.user_mentions.id_str as tweet_mentioned_user_id',
    'entities.urls.expanded_url as tweet_urls',
    'place as tweet_place',
    'coordinates.coordinates as tweet_coordinates',
    'user.created_at as user_timestamp', 
    'user.default_profile_image as user_default_profile_image', 
    'user.description as user_description', 
    'user.favourites_count as user_favourites_count',
    'user.followers_count as user_followers_count', 
    'user.friends_count as user_friends_count',
    'user.geo_enabled as user_geo_enabled',
    'user.id_str as user_id',
    'user.location as user_location', 
    'user.name as user_name', 
    'user.notifications as user_notifications', 
    'user.profile_image_url_https as user_profile_image_url_https', 
    'user.protected as user_protected',
    'user.screen_name as user_screen_name', 
    'user.statuses_count as user_statuses_count', 
    'user.url as user_url',
    'user.verified as user_verified',
    )
    tmp1 = tmp1.withColumn("tweet_timestamp",F.unix_timestamp("tweet_timestamp","EEE MMM dd HH:mm:ss ZZZZZ yyyy"))
    tmp1 = tmp1.withColumn("user_timestamp",F.unix_timestamp("user_timestamp","EEE MMM dd HH:mm:ss ZZZZZ yyyy"))
#     tmp1 = tmp1.withColumn("input_file_name",F.input_file_name())
    tmp1 = tmp1.drop_duplicates(subset=["tweet_id"])
    tmp1 = tmp1.repartition(numOfPartitions)
    tmp1.write.mode("overwrite").parquet(os.path.join(path_to_data,"user_timeline","extract"))


# In[ ]:


path2schema = os.path.join(path_to_data,"user_timeline","API","US","032022","full","user_timeline_500_US_032022_full_15965084_41_dd36715b-ec01-44a8-ab5d-38d965a3c3ff.json.bz2")
schema = spark.read.option("compression","bzip2").option("multiLine","true").option("encoding","UTF-8").json(path2schema).schema
path2files = os.path.join(path_to_data,"user_timeline","API","*","*","*","*.bz2")
# Used for testing
# path2files = os.path.join(path_to_data,"user_timeline","API","US","032022","full","*.bz2")
df = spark.read.option("compression","bzip2").option("multiLine","true").option("encoding","UTF-8").option("badRecordsPath", os.path.join(path_to_data,"user_timeline","badRecords")).json(path2files,schema=schema)
extract(df,10000)

