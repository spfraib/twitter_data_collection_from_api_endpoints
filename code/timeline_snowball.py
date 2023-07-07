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


def snowball(df1,df2):
    tmp1 = df1.withColumn("neighbor_id",F.explode("tweet_mentioned_user_id")).select("user_id","user_location","neighbor_id")
    tmp2 = df1.selectExpr("user_id","user_location","tweet_retweeted_user_id as neighbor_id")
    tmp3 = df1.selectExpr("user_id","user_location","tweet_in_reply_to_user_id as neighbor_id")
    tmp4 = tmp1.unionByName(tmp2).unionByName(tmp3)
    tmp4 = tmp4.where(tmp4["neighbor_id"].isNotNull())
    tmp5 = tmp4.join(F.broadcast(df2),on="user_location",how="left")
    tmp5 = tmp5.groupby(["neighbor_id","country_short"]).agg(F.count("user_id").alias("n_users"))
    tmp5 = tmp5.withColumnRenamed("neighbor_id","user_id")
    tmp5.write.mode("overwrite").parquet(os.path.join(path_to_data,"user_timeline","snowball"))


# In[ ]:


test = "part-0000*.snappy.parquet"
df1 = spark.read.parquet(os.path.join(path_to_data,"user_timeline","extract"))
df2 = spark.read.parquet(os.path.join(path_to_data,"preprocessed","locations","locations_geocoded.parquet")).select("user_location","country_short")
snowball(df1,df2)

