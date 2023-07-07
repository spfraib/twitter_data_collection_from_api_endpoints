#!/usr/bin/env python
# coding: utf-8

# In[1]:


from timeit import default_timer as timer
import time
from datetime import date, datetime
import os
import sys
import uuid
from glob import glob
import json
import tweepy
import numpy as np
import pandas as pd
from pathlib import Path
import requests


# In[2]:


path_to_data = os.path.join('/',os.getcwd().split('/')[1],'spf248','twitter_data_collection','data')
start_pull = date.today().strftime("%d%m%Y")
id_type = 'user_id'
max_tweets_window = 100000
with open(os.path.join(path_to_data,'../../twitter_social_cohesion/data/data_collection','keys','proxies','proxy_key')) as f:
    proxy_key = f.readlines()[0].strip('\n|"')
    
print('Date:',datetime.today().strftime('%d/%m/%Y %H:%M'))
print('path_to_data:',path_to_data)
print('start_pull:',start_pull)
print('id_type:',id_type)
print('max_tweets_window:',max_tweets_window)


# In[3]:


def get_proxies(proxy_key):
    """
    Get proxies from webshare.
    Call the function at the top of script to get proxies.
    Returns a list of formatted proxies.
    """

    proxies_path = Path("proxies.txt")
    if not proxies_path.exists():
        print("Retrieving proxies and saving as proxies.txt")
        # get proxies
        resp = requests.get(
            "https://proxy.webshare.io/api/proxy/list/",
            headers={"Authorization": f"Token {proxy_key}"},
        )
        proxies = resp.json()["results"]
        for p in proxies:
            prox = f"http://{p['username']}:{p['password']}@{p['proxy_address']}:{p['ports']['http']}"
            p["proxy"] = prox
        proxies = pd.DataFrame(proxies)["proxy"].to_list()
        proxies_path.write_text("\n".join(proxies))
    else:
        print("Using cached proxy list proxies.txt")
        proxies = proxies_path.read_text().split("\n")

    return proxies

def change_proxy(proxylist, proxy_idx=None):
    """
    Args:
        proxylist (list): _description_
        proxy_idx (int, optional): proxy index. Defaults to None.

    Returns:
        int: proxy_idx
    """

    # reset/remove proxies first
    os.system("unset no_proxy")
    os.system("unset NO_PROXY")
    # os.system("unset OBJC_DISABLE_INITIALIZE_FORK_SAFETY")

    if proxy_idx is not None:
        proxy = proxylist[proxy_idx]
        print(f"Switch to proxy {proxy_idx} ({proxy}))")

        os.environ["http_proxy"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        os.environ["https_proxy"] = proxy
        os.environ["HTTPS_PROXY"] = proxy

    return proxy_idx


# In[4]:


def select_key_files(path_to_data):
    return sorted(glob(os.path.join(path_to_data,'../../twitter_social_cohesion/data/data_collection','keys','v1','oauth1','apps','*.json')))
    
key_files = select_key_files(path_to_data)
print('key files:', len(key_files))


# In[5]:


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
SLURM_ARRAY_TASK_COUNT  = get_env_var('SLURM_ARRAY_TASK_COUNT',len(key_files))


# In[6]:


# run this before making any twitter request
proxies = get_proxies(proxy_key)
# change_proxy(proxies, proxy_idx=None)  # doesn't do anything
change_proxy(proxies, proxy_idx=SLURM_ARRAY_TASK_ID)


# In[7]:


def get_key_file(key_files,SLURM_ARRAY_TASK_ID,SLURM_ARRAY_TASK_COUNT):
    print('# keys:', len(key_files))
    if SLURM_ARRAY_TASK_COUNT!=len(key_files) or SLURM_ARRAY_TASK_ID>=len(key_files) or SLURM_ARRAY_TASK_ID<0:
        print("CHECK JOBARRAY")
    return key_files[SLURM_ARRAY_TASK_ID]
        
key_file = get_key_file(key_files,SLURM_ARRAY_TASK_ID,SLURM_ARRAY_TASK_COUNT)
print('key file:', key_file)


# In[8]:


def get_API_auth(key_file):
    # Import Key
    with open(key_file) as f:
        key = json.load(f)
    # OAuth process, using the keys and tokens
    auth = tweepy.OAuthHandler(key['API_Key'], key['API_Key_Secret'])
    auth.set_access_token(key['Access_Token'], key['Access_Token_Secret'])
    # Creation of the actual interface, using authentication
    api_auth = tweepy.API(auth,wait_on_rate_limit=True)
    try:
        api_auth.verify_credentials()
    except:
        print(key_file,": error during authentication")
    return api_auth

# for key_file in key_files:
#     get_API_auth(key_file)
# print('Credentials Checked!')

# Create API auth
api = get_API_auth(key_file)


# In[ ]:


def n_requests_for_full_timeline(user_timeline,count=200):
    if user_timeline.shape[0]:
        return user_timeline.shape[0]//count+(user_timeline.shape[0]%count>0)
    else:
        return 1

def pull_from_user_timeline_API_endpoint(api,user,id_type,since_id):
    user_timeline=[]
    error=None
    try:
        if since_id:
            if id_type == 'user_id':
                cursor=tweepy.Cursor(api.user_timeline,user_id=user,since_id=since_id,count=200,tweet_mode="extended",include_rts=True).items()
            elif id_type == 'screen_name':
                cursor=tweepy.Cursor(api.user_timeline,screen_name=user,since_id=since_id,count=200,tweet_mode="extended",include_rts=True).items()
        else:
            if id_type == 'user_id':
                cursor=tweepy.Cursor(api.user_timeline,user_id=user,count=200,tweet_mode="extended",include_rts=True).items()
            elif id_type == 'screen_name':
                cursor=tweepy.Cursor(api.user_timeline,screen_name=user,count=200,tweet_mode="extended",include_rts=True).items()
        for status in cursor:
            user_timeline.append(status._json)
    except tweepy.errors.TweepyException as e:
        error = str(e)
    return pd.DataFrame(user_timeline), error

# timeline_test_1,error = pull_from_user_timeline_API_endpoint(api,'@deaneckles','screen_name','1388683708195086336')
# timeline_test_2,error = pull_from_user_timeline_API_endpoint(api,'@deaneckles','screen_name',None)


# In[ ]:


def pull_users(users,country,pull_type):
    n_users_queried = 0
    n_users_pulled = 0
    n_users_error = 0
    output_id = str(uuid.uuid4())
    tweets_window = pd.DataFrame()
    n_tweets_window = 0
    n_requests_window = 0
    n_users_window = 0
    start = timer()
    for user_id,tweet_id in users.to_records(index=False):
        print('# queried users:',n_users_queried)
        print('# pulled users:',n_users_pulled)
        print('# pulled missed:',n_users_error)
        print('# pulled users in window:',n_users_window)
        print('# pulled requests in window:',n_requests_window)
        print('# pulled tweets in window:',n_tweets_window)
        n_users_queried += 1
        tweets_user, error = pull_from_user_timeline_API_endpoint(api,user_id,id_type,tweet_id)
        if not error:
            tweets_window = pd.concat([tweets_window, tweets_user],sort=False)
            n_tweets_window += tweets_user.shape[0]
            n_requests_window += n_requests_for_full_timeline(tweets_user)
            n_users_window += 1
            n_users_pulled += 1
        else:
            n_users_error += 1
            print('Error pulling user',n_users_queried,':',error)
        if n_tweets_window > max_tweets_window or user_id == users.to_records(index=False)[-1][0]:
            dirname = os.path.join(path_to_data,'user_timeline','API',country,start_pull,pull_type)
            os.makedirs(dirname, exist_ok=True)
            filename = 'user_timeline_'+str(n_users_window)+'_users_'+str(n_requests_window)+'_requests_'+str(n_tweets_window)+'_tweets_'+start_pull+'_'+pull_type+'_'+str(SLURM_JOB_ID)+'_'+str(SLURM_ARRAY_TASK_ID)+'_'+output_id+'.json.bz2'
            tweets_window.to_json(
            os.path.join(dirname,filename),
            orient='records',
            force_ascii=False,
            date_format=None,
            double_precision=15)
            end = timer()
            print('Saved in', filename)
            print('Computing Time:', round(end - start), 'sec')
            print()
            output_id = str(uuid.uuid4())
            tweets_window = pd.DataFrame()
            n_tweets_window = 0
            n_requests_window = 0
            n_users_window = 0
            start = timer()


# In[ ]:


print('Load and select users:')
start = timer()

files = pd.Series(sorted(glob(os.path.join(path_to_data,'user_timeline','batch_tmp','*parquet')))).sample(frac=1,random_state=0).to_list()
tmp = pd.read_parquet(list(np.array_split(files,SLURM_ARRAY_TASK_COUNT)[SLURM_ARRAY_TASK_ID]))

for pull_type in ['update','full']:
    print('Pull type:',pull_type)
    for country in ['MX','PK']:
        print('Country:',country)
        users = tmp[tmp['country_short']==country][['user_id','tweet_id']]
        if pull_type=='update':
            users.dropna(inplace=True)
        elif pull_type=='full':
            users.drop(users.dropna().index,inplace=True)
        users = users.sort_values(by='user_id').sample(frac=1,random_state=0).reset_index(drop=True)
        print('# users:', len(users))
        pull_users(users,country,pull_type)
        
end = timer()
print('Computing Time:', round(end - start), 'sec')


# In[ ]:




