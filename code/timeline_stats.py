#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
from datetime import datetime
from pyspark.sql import SparkSession
import pyspark.sql.functions as F


# In[ ]:


print('Date:',datetime.today().strftime('%d%m%Y'))
spark = SparkSession.builder.config("spark.sql.files.ignoreCorruptFiles","true") .config("spark.serializer","org.apache.spark.serializer.KryoSerializer") .config("spark.yarn.appMasterEnv.LANG","en_US.UTF-8") .config("spark.executorEnv.LANG","en_US.UTF-8") .config("spark.driver.extraJavaOptions","-Duser.timezone=UTC") .config("spark.executor.extraJavaOptions","-Duser.timezone=UTC") .config("spark.sql.session.timeZone","UTC") .config("spark.hadoop.dfs.replication","1") .config("spark.sql.broadcastTimeout",-1) .getOrCreate()
print(spark.sparkContext.getConf().getAll())
path_to_data = "/user/spf248/twitter_data_collection/data"
print(path_to_data)


# In[ ]:


def get_stats(country_short):
    users_in_country = profiles.where(profiles['country_short']==country_short).select("user_id")
    snowball_in_country = timelines.join(F.broadcast(users_in_country),on='user_id')
    snowball_in_country = snowball_in_country.withColumn("snowball_id",F.explode("tweet_mentioned_user_id")).drop('tweet_mentioned_user_id')
    snowball_in_country = snowball_in_country.join(F.broadcast(users_in_country.withColumnRenamed('user_id','snowball_id')),on='snowball_id').drop_duplicates()
    print("Snowball list",snowball_in_country.cache().count())
    seeds_in_country = seeds.join(users_in_country,on='user_id')
    print("# Seeds in country",seeds_in_country.cache().count())
    snowball_1 = snowball_in_country.join(F.broadcast(seeds_in_country),on='user_id').join(seeds_in_country.withColumnRenamed('user_id','snowball_id'),on='snowball_id',how='left_anti').selectExpr('snowball_id as user_id').distinct()
    snowball_2 = snowball_in_country.join(F.broadcast(snowball_1),on='user_id').join(seeds_in_country.unionByName(snowball_1).withColumnRenamed('user_id','snowball_id'),on='snowball_id',how='left_anti').selectExpr('snowball_id as user_id').distinct()
    snowball_3 = snowball_in_country.join(F.broadcast(snowball_2),on='user_id').join(seeds_in_country.unionByName(snowball_1).unionByName(snowball_2).withColumnRenamed('user_id','snowball_id'),on='snowball_id',how='left_anti').selectExpr('snowball_id as user_id').distinct()
    snowball_4 = snowball_in_country.join(F.broadcast(snowball_3),on='user_id').join(seeds_in_country.unionByName(snowball_1).unionByName(snowball_2).unionByName(snowball_3).withColumnRenamed('user_id','snowball_id'),on='snowball_id',how='left_anti').selectExpr('snowball_id as user_id').distinct()
    stats = spark.createDataFrame([{
    'n_seeds': seeds_in_country.count(), 
    'n_snowball_1': snowball_1.count(), 
    'n_snowball_2': snowball_2.count(), 
    'n_snowball_3': snowball_3.count(), 
    'n_snowball_4': snowball_4.count(), 
    }])
    stats.write.mode("overwrite").parquet(os.path.join(path_to_data,"preprocessing","stats",country_code))


# In[ ]:


timelines = spark.read.parquet(os.path.join(path_to_data,"user_timeline","extract")).select("user_id","tweet_mentioned_user_id")
locations = spark.read.parquet(os.path.join(path_to_data,"preprocessed","locations","locations_geocoded.parquet")).select("user_location","country_short")
profiles = spark.read.parquet(os.path.join(path_to_data,"user_timeline","profiles")).select("user_id","country_short")
seeds = spark.read.parquet(os.path.join(path_to_data,"lookup_users","seeds"))
get_stats("NG")
