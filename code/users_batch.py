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


df1 = spark.read.parquet(os.path.join(path_to_data,"lookup_users","seeds")).select("user_id")
df2 = spark.read.parquet(os.path.join(path_to_data,"user_timeline","snowball")).selectExpr("user_id")
df3 = spark.read.parquet(os.path.join(path_to_data,"lookup_users","geocoded")).select("user_id")
# lookup_users from the seeds or the snowball
tmp = df1.join(df2,on='user_id',how='outer')
# remove users who have been geocoded
tmp = tmp.join(df3,on='user_id',how='left_anti')
tmp = tmp.distinct()
tmp.write.mode("overwrite").parquet(os.path.join(path_to_data,"lookup_users","batch"))

