# case-scrnaseq/fastq-registration/main.py

import argparse
import tempfile
import os
from collections import defaultdict
import gzip
import datetime
import glob

from pydantic import BaseModel
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from Bio import SeqIO

from zihelper import aws
from zihelper import utils
from zihelper import exceptions as ziexceptions

__author__ = "Jonathan Alles"
__email__ = "Jonathan.Alles@gmx.de"
__copyright__ = "Copyright 2024"

load_dotenv()

MAX_INPUT_GB = int(utils.load_check_env_var('FASTQ_REGISTRATION_MAX_INPUT_GB'))
VALID_FASTQ_EXTENSIONS = utils.load_check_env_var('FASTQ_REGISTRATION_VALID_FASTQ_EXTENSIONS').split(',')
VALID_READ1_SUFFIX = utils.load_check_env_var('FASTQ_REGISTRATION_VALID_READ1_SUFFIX').split(',')
VALID_READ2_SUFFIX = utils.load_check_env_var('FASTQ_REGISTRATION_VALID_READ2_SUFFIX').split(',')

OUTPUT_BUCKET = utils.load_check_env_var('FASTQ_REGISTRATION_OUTPUT_BUCKET')
OUTPUT_BUCKET_PREFIX = utils.load_check_env_var('FASTQ_REGISTRATION_OUTPUT_BUCKET_PREFIX')

SERVICE_USER_SECRET_KEY_NAME = utils.load_check_env_var('FASTQ_REGISTRATION_SERVICE_USER_SECRET_KEY_NAME')
SERVICE_USER=utils.load_check_env_var('FASTQ_REGISTRATION_SERVICE_USER')
SERVICE_USER_PWD=utils.load_check_env_var('FASTQ_REGISTRATION_SERVICE_USER_PWD')

BACKEND_URL = utils.load_check_env_var('FASTQ_REGISTRATION_BACKEND_URL').rstrip('/') # Remove trailing slash for format list URL

# PARSER

parser = argparse.ArgumentParser()
parser.add_argument(
    "--s3-input-tar-key", 
    dest='s3_input_tar_key',
    required=True,
    type=str,
    help="Input tar filename"
)

parser.add_argument(
    "--s3-bucket",
    dest='s3_bucket',
    required=True,
    type=str,
    help="S3 bucket name"
)

# DATA CLASSES

class FastqDatasets(BaseModel):
    name: str
    s3_bucket : str
    s3_source_key : str
    s3_source_bucket : str
    s3_read1_fastq_key : str
    s3_read2_fastq_key : str

# METHODS

def is_fastq(fh):
    fastq = SeqIO.parse(fh, "fastq")
    
    try : return any(fastq)
    
    except Exception as e:
        return False

# MAIN

def main(s3_input_tar_key: str, s3_bucket: str):
    
    aws_s3 = aws.AwsS3()
    init_wd = os.getcwd()
    
    # Prepare combinations for fastq endings
    read1_endings = [f'_{suf1}.{suf2}' for suf1 in VALID_READ1_SUFFIX for suf2 in VALID_FASTQ_EXTENSIONS]
    read2_endings = [f'_{suf1}.{suf2}' for suf1 in VALID_READ2_SUFFIX for suf2 in VALID_FASTQ_EXTENSIONS]
    
    # Check if output bucket exists
    aws_s3.check_bucket_exists(OUTPUT_BUCKET)
    
    # Check if backend credentials can be defined
    
    if SERVICE_USER_SECRET_KEY_NAME:
        aws_secrets_manager = aws.AwsSecretsManager()
        secret_key_json = aws_secrets_manager.get_secret_value_json(SERVICE_USER_SECRET_KEY_NAME)
        service_user_name = secret_key_json['username']
        service_user_pwd = secret_key_json['password']
        
    else:
        service_user_pwd = SERVICE_USER_PWD
        service_user_name = SERVICE_USER
    login = HTTPBasicAuth(service_user_name, service_user_pwd)

    # Test connection to backend
    print(f'Test connection to backend URL {BACKEND_URL}')
    
    res = requests.get(BACKEND_URL, auth=login)
    assert res.status_code == 200, f'Backend URL {BACKEND_URL} is not reachable. Exit.'
    
    # Check if single bucket key exists
    assert s3_input_tar_key.endswith('.tar'), f'{s3_input_tar_key} is not a .tar file. Exit.'
    
    if not aws_s3.check_object_key_exists(s3_bucket, s3_input_tar_key):
        raise ziexceptions.ZiHelperError(f'Key {s3_input_tar_key} does not exist in bucket {s3_bucket}.Exit.')
    
    tar_filesize_mb = aws_s3.get_key_size_mb(s3_bucket, s3_input_tar_key)
    
    if tar_filesize_mb > (MAX_INPUT_GB * 1024):
        raise ziexceptions.ZiHelperError(f'{s3_input_tar_key} is larger than {MAX_INPUT_GB}GB. Exit.')
    
    print(f'Download input tar file {s3_input_tar_key} from bucket {s3_bucket}')
    
    # Create a temporary folder
    temp_dir = tempfile.TemporaryDirectory()
    
    # Move to temp dir
    os.chdir(temp_dir.name)
    
    tar_base = os.path.basename(s3_input_tar_key)
    local_tar_path = os.path.join(temp_dir.name, tar_base)
        
    aws_s3.download_key_from_bucket(s3_bucket, s3_input_tar_key, local_tar_path)
    
    # Untar the tar file
    print(f'Untar {local_tar_path}')
    
    # CONTINUE HERE: Files are in tar dir and need to be extracted
    utils.untar_file(local_tar_path)
    untar_base = local_tar_path.replace('.tar', '')
    
    # Sort the fastq files by prefix
    sample_read_dict = defaultdict(dict)
    
    # fastq files can be in cwd, level1 or level2 below the tar file, depedning on the tar file structure
    # Prefilter fastq files from tar dir
    fq_files = glob.glob('**', recursive=True)
    fq_files = [os.path.abspath(f) for f in fq_files if f.endswith(tuple(VALID_FASTQ_EXTENSIONS))]
    
    for f in fq_files:
        
        # Check for file which is matching substring and read
        # Loop over read1 endings, if loop ends, check read2 endings, if loop completes continue
        # Break if file ending is round and define sample and read
        for read1_end in read1_endings:
            if f.endswith(read1_end):
                sample = os.path.basename(f).replace(read1_end, '')
                read = 'R1'
                break
        else:
            for read2_end in read2_endings:
                if f.endswith(read2_end):
                    sample = os.path.basename(f).replace(read2_end, '')
                    read = 'R2'
                    break
            else:
                print(f"WARNING {f} cannot be assigned to read1 or read2. Skip.")        
                continue
                
        # Check if the fastq file has minimum size of 1 MB
        if os.path.getsize(f) < 1024:
            print(f"WARNING {f} is smaller than 1MB. Skip.")
            continue
        
        # Check if files are valid fastq files, continue if not valid
        if f.endswith('.gz'):
            with gzip.open(f, 'rt') as fq_fh:
                if is_fastq(fq_fh):
                    f_path_gz = f
                else:
                    print(f"WARNING {f} is not a valid fastq file. Skip.")
                    continue
                    
        # Case for uncompressed fastq files, continue if not valid or gzip
        else:
            with open(f, 'r') as fq_fh:
                if is_fastq(fq_fh):
                    f_path_gz = f + '.gz'
                    utils.gzip_file(f, output_dir = os.path.dirname(f), remove_original=True)
                    
                else:
                    print(f"WARNING {f} is not a valid fastq file. Skip.")
                    continue
        
        # Add the sample and read to the dictionary
        sample_read_dict[sample][read] = f_path_gz
    
    # Check if the sample has both read1 and read2 and prepare for upload
    for sample, read_dict in sample_read_dict.items():
        
        if 'R1' not in read_dict:
            print(f"WARNING {sample} does not have read1. Skip.")
            continue
        if 'R2' not in read_dict:
            print(f"WARNING {sample} does not have read2. Skip.")
            continue
        
        uuid_short = utils.generate_short_uuid()
        dataset_name = f'fq_{sample}_{uuid_short}'
        date = datetime.datetime.now().strftime("%Y%m%d")
        
        # Upload the fastq files to S3 and 
        for read, f in read_dict.items():
                
            # Check if key exists
            s3_key = f'{OUTPUT_BUCKET_PREFIX}/{date}/{dataset_name}_S1_{read}_001.fastq.gz'
            print(f'Upload {f} to {s3_key}')
            aws_s3.upload_file_to_bucket(OUTPUT_BUCKET, s3_key, f)

            if read == 'R1':
                read1_key = s3_key
            else:
                read2_key = s3_key
        
        
        fastq_dataset = FastqDatasets(
            name = dataset_name,
            s3_bucket = OUTPUT_BUCKET,
            s3_source_key = s3_input_tar_key,
            s3_source_bucket = s3_bucket,
            s3_read1_fastq_key = read1_key,
            s3_read2_fastq_key = read2_key
        )
        
        print('POST dataset json.')
        res = requests.post(BACKEND_URL + '/', auth=login, data=fastq_dataset.model_dump())
        assert res.status_code == 201, f'POST request failed with status code {res.status_code}. Exit.'
            
    temp_dir.cleanup()
    
    os.chdir(init_wd)
    
if __name__ == '__main__':
    
    print('Start container fastq-registration script.')
    
    args = parser.parse_args()
    s3_input_tar_key = args.s3_input_tar_key
    s3_bucket = args.s3_bucket

    main(s3_input_tar_key, s3_bucket)
    
    print('fastq-registration completed. Exit.')