# Small script to retrieve information about API keys in an IBM Cloud account.
# The API keys either belong to the user or the service IDs in the account.
# For each API key details including the activity are retrieved. The activity
# details may include the timestamp of the latest authentication and the number
# of recorded authentications with that API key.
#
# Written by Henrik Loeser, hloeser@de.ibm.com

# only standard packages are used, no installation necessary
import requests, json, sys,os, base64
import argparse 
from urllib.parse import urlparse,parse_qs


json_apikeys=[]

# to use pagination, the next page token is required
def extractNextPageToken(next_url):
    o=urlparse(next_url)
    q=parse_qs(o.query)
    return q['pagetoken'][0]

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
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        raise SystemExit(e)
    return response.json()

# retrieve details about an API key
def getIAMDetails(api_key, iam_token):
    url     = "https://iam.cloud.ibm.com/v1/apikeys/details"
    headers = { "Authorization" : iam_token, "IAM-Apikey" : api_key, "Content-Type" : "application/json" }
    try:
        response  = requests.get( url, headers=headers )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        raise SystemExit(e)
    return response.json()

# retrieve the list of accounts accessible using the token
def getAccounts(iam_token):
    url     = "https://accounts.cloud.ibm.com/v1/accounts"
    headers = { "Authorization" : iam_token }
    try:
        response  = requests.get( url, headers=headers )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        raise SystemExit(e)

    return response.json()

# retrieve all API keys for the given IAM ID (user or service)
def getApiKeys(iam_token, account_id, iam_id, id_type):
    pagesize=100
    url = 'https://iam.cloud.ibm.com/v1/apikeys'
    headers = { "Authorization" : iam_token }
    if iam_id is None:
        payload = {"account_id": account_id, "pagesize":pagesize, "scope":"account", "type": id_type}
    else:
        payload = {"account_id": account_id, "iam_id": iam_id, "pagesize":pagesize, "type": id_type}
    try:
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        raise SystemExit(e)

    result=response.json()
    temp=result
    while 'next' in temp:
        payload = {"account_id": account_id, "iam_id": iam_id, "pagesize":pagesize, "pagetoken":extractNextPageToken(temp['next'])}
        try:
            response=requests.get(url, headers=headers, params=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            raise SystemExit(e)
        temp=response.json()
        result['apikeys'].extend(temp['apikeys'])
    return result

# get the details for an API key, including history and activities
def getApiKeyDetails(iam_token, apikey_id):
    url = 'https://iam.cloud.ibm.com/v1/apikeys/{}'.format(apikey_id)
    headers = { "Authorization" : iam_token }
    # we want EVERYTHING
    payload={"include_history":True, "include_activity":True}
    try:
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        raise SystemExit(e)

    return response.json()

# retrieve the list of service IDs
def getServiceIDs(iam_token, account_id):
    pagesize=25
    url = 'https://iam.cloud.ibm.com/v1/serviceids'
    headers = { "Authorization" : iam_token }
    payload = {"account_id": account_id, "pagesize": pagesize}
    try:
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        raise SystemExit(e)

    result=response.json()
    temp=result
    while 'next' in temp:
        payload = {"account_id": account_id, "pagesize":pagesize, "pagetoken":extractNextPageToken(temp['next'])}
        try:
            response=requests.get(url, headers=headers, params=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            raise SystemExit(e)

        temp=response.json()
        result['serviceids'].extend(temp['serviceids'])
    return result

# loop over all the API keys for the (user / service) ID and retrieve the details
def getAndPrintAPIKeys(iam_token, account_id, iam_id, id_type, out_format):
    api_key_list=getApiKeys(iam_token, account_id, iam_id, id_type)
    for apikey in api_key_list['apikeys']:
        #print(apikey)
        apikey_details=getApiKeyDetails(iam_token, apikey['id'])
        # some tricky printing because "activity" and last_authn might not be present
        if out_format=='CSV':
            print("{},{},{},{},{},{},{},{}".format(apikey_details['iam_id'],apikey_details['created_by'],apikey_details['created_at'],
                                            apikey_details['name'],apikey_details['id'],apikey_details['locked'],
                                            apikey_details.get('activity',{}).get('last_authn',None),
                                            apikey_details.get('activity',{}).get('authn_count', None)))
        else:
            json_apikeys.append(apikey_details)

# as account admin, retrieve details on API keys for users and service IDs
# in the entire account. This requires a broad set of privileges and might fail.
def getEverything(iam_token,account_id, iam_id, out_format):
    if out_format=='CSV':
        print('iam_id, created_by, created_at, name, id, locked, last_authn, authn_count')
        
    getAndPrintAPIKeys(iam_token, account_id, None, 'user',out_format)
    getAndPrintAPIKeys(iam_token, account_id, None, 'serviceid',out_format)
    if out_format=='JSON':
       print(json.dumps(json_apikeys))

# as regular user, retrieve details on API keys for the current user and the related service IDs
def getEverythingUser(iam_token,account_id, iam_id, out_format):
    if out_format=='CSV':
        print('iam_id, created_by, created_at, name, id, locked, last_authn, authn_count')
        
    getAndPrintAPIKeys(iam_token, account_id, iam_id, 'user',out_format)
    serviceids=getServiceIDs(iam_token, account_id)
    
    for serviceid in serviceids['serviceids']:
       getAndPrintAPIKeys(iam_token, account_id, serviceid['iam_id'], 'serviceid', out_format)
    if out_format=='JSON':
       print(json.dumps(json_apikeys))


# use split and base64 to get to the content of the IAM token
def extractAccount(iam_token):
    data = iam_token.split('.')
    padded = data[1] + "="*divmod(len(data[1]),4)[1]
    jsondata = json.loads(base64.urlsafe_b64decode(padded))
    return jsondata

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
    parser.add_argument('--type', choices=['admin','user'], type=str, dest='usertype', default='admin', help='existing privilege scope')
    # parse the parameters
    args = parser.parse_args()

    # do we have any parameters like the credential file?
    # if not, let's try to obtain the token from environment
    if args.credfile is None:
        if 'IBMCLOUD_TOKEN' in os.environ:
            iam_token=os.getenv('IBMCLOUD_TOKEN')
            token_data=extractAccount(iam_token)
            account_id=token_data["account"]["bss"]
            iam_id=token_data['iam_id']
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
        accDetails=getIAMDetails(api_key=apiKey, iam_token=iam_token)
        account_id=accDetails['account_id']
        iam_id=accDetails['iam_id']
  
    if args.usertype=='admin':
        getEverything(iam_token, account_id, iam_id, args.out_format)
    else:
        getEverythingUser(iam_token, account_id, iam_id, args.out_format)