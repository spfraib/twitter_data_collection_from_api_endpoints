#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
from datetime import datetime
from pyspark.sql import SparkSession
import pyspark.sql.functions as F


# In[ ]:


print('Date:',datetime.today().strftime('%d%m%Y'))
spark = SparkSession.builder.config("spark.sql.files.ignoreCorruptFiles","true") .config("spark.hadoop.dfs.replication","1") .config("spark.serializer","org.apache.spark.serializer.KryoSerializer") .config("spark.yarn.appMasterEnv.LANG","en_US.UTF-8") .config("spark.executorEnv.LANG","en_US.UTF-8") .config("spark.driver.extraJavaOptions","-Duser.timezone=UTC") .config("spark.executor.extraJavaOptions","-Duser.timezone=UTC") .config("spark.sql.session.timeZone","UTC") .config("spark.sql.broadcastTimeout",-1) .getOrCreate()
print(spark.sparkContext.getConf().getAll())
path_to_data = "/user/spf248/twitter_data_collection/data"
print(path_to_data)


# In[ ]:


path_to_schema = "lookup_users_100059_20220404_17107939_56_25338542-5975-40ac-a0f6-296d95c5757c.json"
schema = spark.read.option("multiLine","true").option("encoding","UTF-8").json(os.path.join(path_to_data,"lookup_users","API","042022",path_to_schema)).schema
df1 = spark.read.option("multiLine","true").option("encoding","UTF-8").json(os.path.join(path_to_data,"lookup_users","API","*"),schema=schema).selectExpr(
"status.id_str as tweet_id",
"status.created_at as tweet_timestamp",
'created_at as user_timestamp', 
'default_profile_image as user_default_profile_image', 
'description as user_description', 
'favourites_count as user_favourites_count',
'followers_count as user_followers_count', 
'friends_count as user_friends_count',
'geo_enabled as user_geo_enabled',
'id_str as user_id',
'location as user_location', 
'name as user_name', 
'notifications as user_notifications', 
'profile_image_url_https as user_profile_image_url_https', 
'protected as user_protected',
'screen_name as user_screen_name', 
'statuses_count as user_statuses_count', 
'url as user_url',
'verified as user_verified',
)
df2 = spark.read.parquet(os.path.join(path_to_data,"preprocessed","locations","locations_geocoded.parquet")).select("user_location","country_short")
tmp = df1.join(F.broadcast(df2),on="user_location",how='left')
tmp = tmp.drop_duplicates(subset=["user_id","user_location"])
tmp = tmp.withColumn("tweet_timestamp",F.unix_timestamp("tweet_timestamp","EEE MMM dd HH:mm:ss ZZZZZ yyyy"))
tmp = tmp.withColumn("user_timestamp",F.unix_timestamp("user_timestamp","EEE MMM dd HH:mm:ss ZZZZZ yyyy"))
tmp.write.mode("overwrite").parquet(os.path.join(path_to_data,"lookup_users","profiles"))

