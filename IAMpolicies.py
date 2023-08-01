# Small script to retrieve information about access policies in an IBM Cloud account.
#
# Written by Henrik Loeser, hloeser@de.ibm.com

# only standard packages are used, no installation necessary
import requests, json, sys,os, base64
import argparse 
from urllib.parse import urlparse,parse_qs


# read an API key from a JSON file
def readApiKey(filename):
    with open(filename) as data_file:
        credentials = json.load(data_file)
    api_key = credentials.get('apikey')
    return api_key

# obtain an access token from an IAM API key
def getAuthTokens(api_key):
    url     = "https://iam.cloud.ibm.com/identity/token"
    headers = { "Content-Type" : "application/x-www-form-urlencoded" }
    data    = "apikey=" + api_key + "&grant_type=urn:ibm:params:oauth:grant-type:apikey"
    try:
        response  = requests.post( url, headers=headers, data=data )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return response.json()

# retrieve all API keys for the given IAM ID (user or service)
# https://cloud.ibm.com/apidocs/iam-policy-management#list-policies
# NOTE: This function is not used, but shown for easy fallback to or
#       additional activation of the version 1 API
def getPoliciesV1(iam_token, account_id, iam_id, id_type):
    pagesize=100
    url = 'https://iam.cloud.ibm.com/v1/policies'
    headers = { "Authorization" : iam_token }
    payload = {"account_id": account_id, "pagesize":pagesize, "format":"include_last_permit", "sort": "last_permit_at"}
    try:
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    result=response.json()
    return result


# retrieve all API keys for the given IAM ID (user or service)
# https://cloud.ibm.com/apidocs/iam-policy-management#list-v2-policies
def getPoliciesV2(iam_token, account_id, iam_id, id_type):
    pagesize=100
    url = 'https://iam.cloud.ibm.com/v2/policies'
    headers = { "Authorization" : iam_token }
    payload = {"account_id": account_id, "pagesize":pagesize, "format":"include_last_permit", "sort": "last_permit_at"}
    try:
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    result=response.json()
    return result

# NOTE: This function is not used, but shown for easy fallback to or
#       additional activation of the version 1 API
def getEverythingV1(iam_token,account_id, out_format):
    policy_list=getPoliciesV1(iam_token, account_id, None, None)
    if out_format=='JSON':
        print(json.dumps(policy_list))
    elif out_format=='CSV':
        # assume CSV output
        print('id, created_by_id, created_at, last_permit_at, last_permit_frequency, state, subject_key1, subject_val1, num_subjects, resource_key1, resource_val1, num_resources, role_id1, description')
        for policy in policy_list['policies']:
            print("{},{},{},{},{},{},{},{},{},{},{},{},'{}','{}'".format(policy['id'], policy.get('created_by_id',None), policy.get('created_at',''),
                                            policy['last_permit_at'],policy['last_permit_frequency'],policy['state'],
                                            policy['subjects'][0]['attributes'][0]['name'],
                                            policy['subjects'][0]['attributes'][0]['value'],
                                            len(policy['subjects'][0]['attributes']),
                                            policy['resources'][0]['attributes'][0]['name'],
                                            policy['resources'][0]['attributes'][0]['value'],
                                            len(policy['resources'][0]['attributes']),
                                            policy['roles'][0]['role_id'],
                                            policy.get('description','')
                                            ))
    else:
        raise("unsupported format")


# retrieve the IAM policies and process them
def getEverythingV2(iam_token,account_id, out_format, subject_types, iam_types):
    policy_list=getPoliciesV2(iam_token, account_id, None, None)
    res_list=[]
    for policy in policy_list['policies']:
        # access
        if policy['type'] in subject_types and policy['type']=='access':
            for subject in policy['subject']['attributes']:
                if subject['key']=='iam_id' and 'id' in iam_types:
                    res_list.append(policy)
                elif subject['key']=='access_group_id' and 'ag' in iam_types:
                    res_list.append(policy)
        # authorization
        elif policy['type'] in subject_types and policy['type']=='authorization':
            res_list.append(policy)

    pol_list={'policies': res_list}
    if out_format=='JSON':
        print(json.dumps(pol_list))
    elif out_format=='CSV':
        # assume CSV output
        print('id, created_by_id, created_at, last_permit_at, last_permit_frequency, state, subject_key1, subject_val1, num_subjects, resource_key1, resource_val1, num_resources, role_id1, description')
        for policy in pol_list['policies']:
            print("{},{},{},{},{},{},{},{},{},{},{},{},'{}','{}'".format(policy['id'], policy.get('created_by_id',None), policy.get('created_at',''),
                                            policy['last_permit_at'],policy['last_permit_frequency'],policy['state'],
                                            policy['subject']['attributes'][0]['key'],
                                            policy['subject']['attributes'][0]['value'],
                                            len(policy['subject']['attributes']),
                                            policy['resource']['attributes'][0]['key'],
                                            policy['resource']['attributes'][0]['value'],
                                            len(policy['resource']['attributes']),
                                            policy['control']['grant']['roles'][0]['role_id'],
                                            policy.get('description','')
                                            ))
    else:
        raise("unsupported format")

# use split and base64 to get to the content of the IAM token
def extractAccount(iam_token):
    data = iam_token.split('.')
    padded = data[1] + "="*divmod(len(data[1]),4)[1]
    jsondata = json.loads(base64.urlsafe_b64decode(padded))
    return jsondata

# main function
if __name__== "__main__":
    credfile=None
    iam_token=None
    iam_id=None
    account_id=None

    # define the command line arguments
    parser = argparse.ArgumentParser(description='Retrieve information about API keys in an IBM Cloud account')
    parser.add_argument('--output', choices=['CSV','JSON'], dest='out_format', default='CSV',
                        help='return output in CSV or JSON format')
    parser.add_argument('--credentials', type=str, action='store', dest='credfile', help='credential file to use')
    parser.add_argument('--type', choices=['access','authorization'], type=str, dest='subject_types', default=['access','authorization'], nargs='*', help='filter by subject type')
    parser.add_argument('--iamtype', choices=['ag','id'], type=str, dest='iam_types', default=['ag','id'], nargs='*', help='filter by IAM type')
    # parse the parameters
    args = parser.parse_args()

    # do we have any parameters like the credential file?
    # if not, let's try to obtain the token from environment
    if args.credfile is None:
        if 'IBMCLOUD_TOKEN' in os.environ:
            iam_token=os.getenv('IBMCLOUD_TOKEN')
        else:
            parser.print_help()
            exit()
    # we should have a credentials file to read from
    else:
        # read credentials from file 
        apiKey=readApiKey(args.credfile)
        # create the IAM access token
        authTokens=getAuthTokens(api_key=apiKey)
        # and make it a bearer token
        iam_token='Bearer '+authTokens["access_token"]   

    # get account details
    token_data=extractAccount(iam_token)
    account_id=token_data["account"]["bss"]
    iam_id=token_data['iam_id']

    # call into the V2-related processing
    getEverythingV2(iam_token, account_id, args.out_format, args.subject_types, args.iam_types)
  