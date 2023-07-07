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


today = date.today().strftime('%d%m%Y')
cutoff = 100000
path_to_data = "/scratch/spf248/twitter_data_collection/data"
id_type = 'user_id'
max_users_per_app = 60
apps = ['spfraib_sentiments','WorldBankGroup6'] # ['spfraib_sentiments','WorldBankGroup6']

print('today:',today)
print('cutoff:',cutoff)
print('path_to_data:',path_to_data)
print('id_type:',id_type)
print('max_users_per_app:',max_users_per_app)


# In[3]:


def select_key_files(path_to_data,max_users_per_app,apps):
    key_files = []
    key_usernames = []
    app2username = {}
    all_files = sorted(glob(os.path.join(path_to_data,'../keys','v1','*.json')))
    for file in all_files:
        username = file.split('/')[-1].split('-')[1].split('.json')[0]
        app = file.split('/')[-1].split('-')[0]
        app2username.setdefault(app, [])
        if app in apps and username not in key_usernames and len(app2username[app])<max_users_per_app:
            app2username[app].append(username)
            key_files.append(file)
            key_usernames.append(username)
    return key_files

key_files = select_key_files(path_to_data,max_users_per_app,apps)
print('key files:', len(key_files))


# In[4]:


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
SLURM_ARRAY_TASK_COUNT  = get_env_var('SLURM_ARRAY_TASK_COUNT',len(key_files))
SLURM_ARRAY_TASK_ID     = get_env_var('SLURM_ARRAY_TASK_ID',0)


# In[5]:


print('Load users:')
start = timer()
files = pd.Series(sorted(glob(os.path.join(path_to_data,"lookup_users","batch","*.parquet")))).sample(frac=1,random_state=0).to_list()
files_node = list(np.array_split(files,SLURM_ARRAY_TASK_COUNT)[SLURM_ARRAY_TASK_ID])
users = pd.read_parquet(files_node)['user_id']
print('# users_batch:', len(users))
end = timer()
print('Computing Time:', round(end - start), 'sec')


# In[6]:


def get_key_file(key_files,SLURM_ARRAY_TASK_ID,SLURM_ARRAY_TASK_COUNT):
    print('# keys:', len(key_files))
    if SLURM_ARRAY_TASK_COUNT!=len(key_files) or SLURM_ARRAY_TASK_ID>=len(key_files) or SLURM_ARRAY_TASK_ID<0:
        print("CHECK JOBARRAY")
    return key_files[SLURM_ARRAY_TASK_ID]
        
key_file = get_key_file(key_files,SLURM_ARRAY_TASK_ID,SLURM_ARRAY_TASK_COUNT)
print('key file:', key_file)


# In[7]:


def get_API_auth(key_file):
    # Import Key
    with open(key_file) as f:
        key = json.load(f)
    # OAuth process, using the keys and tokens
    auth = tweepy.OAuthHandler(key['consumer_key'], key['consumer_secret'])
    auth.set_access_token(key['access_token'], key['access_token_secret'])
    # Creation of the actual interface, using authentication
    api_auth = tweepy.API(auth, wait_on_rate_limit=True)
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


# In[8]:


# Create a function called "chunks" with two arguments, l and n:
def chunks(l, n):
    # For item i in a range that is a length of l,
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i+n]
        
# Split users by chunks of size 100 to accomodate Twitter lookup limit
users_chunks = list(chunks(list(users),100))
print("# Chunks:", len(users_chunks))


# In[9]:


def lookup_users(api,users,id_type='user_id'):
    # Lookup users by chunks of size 100
    if len(users)>100:
        print('Reduce # Users')
        return []
    try:
        if id_type=='user_id':
            lookups = api.lookup_users(user_id=list(users),include_entities='true',tweet_mode='extended')
        elif id_type=='screen_name':
            lookups = api.lookup_users(screen_name=list(users),include_entities='true',tweet_mode='extended')
        return [lookup._json for lookup in lookups]
    except tweepy.errors.TweepyException as e:
        print('Lookup error', e)
        return []
    
# print('Lookup Users...\n')
# start = timer()
# lookups = lookup_users(get_API_auth(key_file), users_chunks[0], 'user_id')
# end = timer()
# print('Computing Time:', round(end - start), 'sec')


# In[14]:


print('Lookup Users...\n')
start = timer()
# Initialize Output File ID
output_id = str(uuid.uuid4())
# Initialize Output Data
lookups = []
for i_chunk,users_chunk in enumerate(users_chunks):
    lookups.extend(lookup_users(api,users_chunk,id_type))
    if i_chunk and not i_chunk%100:
        print("# blocks:",i_chunk)
        print("# lookups:",len(lookups))
    if len(lookups)>=cutoff or i_chunk==len(users_chunks)-1:
        filename = 'lookup_users_'+str(len(lookups))+'_'+today+'_'+str(SLURM_JOB_ID)+'_'+str(SLURM_ARRAY_TASK_ID)+'_'+output_id+'.json'
        print('Data up to block',i_chunk,'with',len(lookups),'users stored in file',filename)
        os.makedirs(os.path.join(path_to_data,'lookup_users','API',today),exist_ok=True)
        pd.DataFrame(lookups).to_json(
        os.path.join(path_to_data,'lookup_users','API',today,filename),
        orient='records',
        force_ascii=False,
        date_format=None,
        double_precision=15)
        end = timer()
        print('Computing Time:', round(end - start), 'sec')
        # Reset
        start = timer()
        output_id = str(uuid.uuid4())
        lookups = []


# In[ ]:




