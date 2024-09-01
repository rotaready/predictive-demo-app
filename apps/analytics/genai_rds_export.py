# copies job status normal export file (in eu-west-1 ldfe/debug bucket) to RDS Local ldfe_jobs table
# Reference: https://github.com/dogukannulu/read_from_s3_upload_to_rds/blob/main/read_from_s3_upload_rds.py?source=post_page-----aaf5f4195480--------------------------------
 
import boto3
from botocore.exceptions import ClientError

import os
import io

import pandas as pd

import mysql.connector
from sqlalchemy import create_engine

s3 = boto3.resource('s3', 'eu-west-1')

s3_client = boto3.client('s3',
                        aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
                        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                        region_name='eu-west-1'
                        )

s3_bucket = 'rotaready-machine-learning'
s3_key = 'ldfe/debug/inference/job_status.csv'

local_host = os.getenv("RDS_HOST")
local_user = os.getenv("RDS_USER")
local_pwd = os.getenv("RDS_PASSWORD")
local_db = 'rr_core'



def create_dataframe():
    s3=s3_client
    name=s3_bucket
    key=s3_key
    try:
        get_response = s3.get_object(Bucket=name, Key=key)
        print("job status report retrieved from S3 bucket successfully")
    except ClientError as e:
        print("S3 object cannot be retrieved:", e)
    
    file_content = get_response['Body'].read()
    df = pd.read_csv(io.BytesIO(file_content)) # necessary transformation from S3 to pandas

    return df



def modify_dataframe(df):
    
    df.rename(columns={"Unnamed: 0": "id"}, inplace = True)

    # change timestamp column to myql timestamp format
    df['timestamp'] = pd.to_datetime(df['timestamp'], dayfirst=True).dt.strftime('%Y-%m-%d %H:%M:%S')

    # *check* shouldnt need function below - but keeping here for reference
    # modify_columns = ModifyColumns()

    # df['STORE_LOCATION'] = df['STORE_LOCATION'].apply(modify_columns.extract_city_name)
    # df['PRODUCT_ID'] = df['PRODUCT_ID'].apply(modify_columns.extract_only_numbers)

    # column_list = ['MRP','CP','DISCOUNT','SP']
    # for i in column_list:
    #     df[i] = df[i].apply(modify_columns.extract_floats_without_sign)

    return df


def upload_dataframe_into_rds(df):
    
    table_name = 'ldfe_jobs'

    try:

        engine = create_engine(f"mysql+pymysql://{local_user}:{local_pwd}@{local_host}/{local_db}")

        df.to_sql(table_name, con=engine, if_exists='replace', index=False) # overwrite existing table
        print(f'Dataframe uploaded into {table_name} successfully')

    except Exception as e:
        
        print('Error happened while uploading dataframe into database:', e)


df_unmodified = create_dataframe()
df_modified = modify_dataframe(df_unmodified)
upload_dataframe_into_rds(df_modified)
