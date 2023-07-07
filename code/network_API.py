#!/usr/bin/env python
# coding: utf-8

# In[1]:


from timeit import default_timer as timer
from datetime import date
import os
import sys
import uuid
from glob import glob
import json
import tweepy
import numpy as np
import pandas as pd


# In[2]:


country_code = 'NG'
print('Country:', country_code)


# In[3]:


cutoff = 1000
print('Store after',cutoff,'queries')


# In[4]:


path_to_data = "/scratch/spf248/twitter_data_collection/data"
print(path_to_data)


# In[5]:


endpoint_name = 'friends_ids'
print('endpoint:', endpoint_name)


# In[6]:


id_type = 'user_id'
print('id_type:',id_type)


# In[7]:


def get_env_var(varname,default):
    if os.environ.get(varname) != None:
        var = int(os.environ.get(varname))
        print(varname,':', var)
    else:
        var = default
        print(varname,':', var,'(Default)')
    return var

# Choose Number of Nodes To Distribute Credentials: e.g. jobarray=0-4, cpu_per_task=20, credentials = 90 (<100)
SLURM_JOB_ID            = get_env_var('SLURM_JOB_ID',0)
SLURM_ARRAY_TASK_ID     = get_env_var('SLURM_ARRAY_TASK_ID',0)
SLURM_ARRAY_TASK_COUNT  = get_env_var('SLURM_ARRAY_TASK_COUNT',1)


# In[8]:


batch = pd.read_csv(os.path.join(path_to_data,'friends_ids',country_code,'batch.csv'),squeeze=True).tolist()
print('# users batch:', len(batch))


# In[9]:


def get_key_file(path_to_data,SLURM_ARRAY_TASK_ID,SLURM_ARRAY_TASK_COUNT):
    key_files = sorted(glob(os.path.join(path_to_data,'../keys','v1','*.json')))
    print('# keys:', len(key_files))
    if SLURM_ARRAY_TASK_COUNT!=len(key_files) or SLURM_ARRAY_TASK_ID>=len(key_files) or SLURM_ARRAY_TASK_ID<0:
        print("CHECK JOBARRAY")
    return key_files[SLURM_ARRAY_TASK_ID]
        
key_file = get_key_file(path_to_data,SLURM_ARRAY_TASK_ID,SLURM_ARRAY_TASK_COUNT)
print('key file:', key_file)


# In[10]:


def get_API_auth(key_file):
    # Import Key
    with open(key_file) as f:
        key = json.load(f)
    # OAuth process, using the keys and tokens
    auth = tweepy.OAuthHandler(key['consumer_key'], key['consumer_secret'])
    auth.set_access_token(key['access_token'], key['access_token_secret'])
    # Creation of the actual interface, using authentication
    api_auth = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    try:
        api_auth.verify_credentials()
    except:
        sys.exit(key_file,": error during authentication")
    return api_auth

# for key_file in glob(os.path.join(path_to_data,'../keys','v1','*.json')):
#     get_API_auth(key_file)
# print('Credentials Checked!')

# Create API auth
api = get_API_auth(key_file)


# # API pull

# In[12]:


def allocate_users(batch,SLURM_ARRAY_TASK_ID,SLURM_ARRAY_TASK_COUNT):
    np.random.seed(0)
    users = np.random.permutation(batch)
    print('# Users:', len(users))
    print('First User:', users[0])
    users = np.array_split(users,SLURM_ARRAY_TASK_COUNT)[SLURM_ARRAY_TASK_ID].copy()
    print('Node"s # Users:', len(users))
    print('Node"s First User:', users[0])    
    return users

print('Allocate users:')
start = timer()
users = allocate_users(batch,SLURM_ARRAY_TASK_ID,SLURM_ARRAY_TASK_COUNT)
end = timer()
print('Computing Time:', round(end - start), 'sec')


# In[16]:


def pull_from_API_endpoint(api,endpoint_name,user,id_type):
    dump = []
    error = None
    try:
        if endpoint_name == 'friends_ids':
            if id_type == 'user_id':
                cursor = tweepy.Cursor(api.friends_ids, user_id=user, stringify_ids=True).pages()
            elif id_type == 'screen_name':
                cursor = tweepy.Cursor(api.friends_ids, screen_name=user, stringify_ids=True).pages()
        elif endpoint_name == 'followers_ids':
            if id_type == 'user_id':
                cursor = tweepy.Cursor(api.followers_ids, user_id=user, stringify_ids=True).pages()
            elif id_type == 'screen_name':
                cursor = tweepy.Cursor(api.followers_ids, screen_name=user, stringify_ids=True).pages()
        for page in cursor:
            dump.extend(page)
    except tweepy.error.TweepError as e:
        error = str(e)
    return dump, error
dump, error = pull_from_API_endpoint(api,"followers_ids","@deaneckles","screen_name")


# In[21]:


output_id = str(uuid.uuid4())
dumps = {}
n_requests = 0
start = timer()
for counter,user in enumerate(users):
    if counter and not counter % (cutoff // 10):
        print('# users queried:', counter)
        print('# users pulled:', n_requests)
    dump, error = pull_from_API_endpoint(api,endpoint_name,user,id_type)
    if not error:
        dumps[str(user)] = dump
        n_requests += 1
    if n_requests == cutoff or user == users[-1]:
        folder_name = os.path.join(path_to_data,endpoint_name,country_code,'API',date.today().strftime("%m%Y"))
        os.makedirs(folder_name, exist_ok=True)
        filename = endpoint_name+'_'+country_code+'_'+str(n_requests)+'_users_'+str(date.today()).replace('-','_')+'_'+str(SLURM_JOB_ID)+'_'+str(SLURM_ARRAY_TASK_ID)+'_'+output_id+'.json'
        with open(os.path.join(folder_name,filename), 'w') as fp:
            json.dump(dumps, fp)
        print('Data stored in',filename)
        end = timer()
        print('Computing Time:', round(end - start), 'sec')
        output_id = str(uuid.uuid4())
        dumps = {}
        n_requests = 0
        start = timer()


# In[ ]:




