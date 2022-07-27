# Small script to retrieve information about API keys in an IBM Cloud account.
# The API keys either belong to the user or the service IDs in the account.
# For each API key details including the activity are retrieved. The activity
# details may include the timestamp of the latest authentication and the number
# of recorded authentications with that API key.
#
# Written by Henrik Loeser, hloeser@de.ibm.com

# only standard packages are used, no installation necessary
import requests, json, sys,os, base64
from urllib.parse import urlparse,parse_qs

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
    response  = requests.post( url, headers=headers, data=data )
    return response.json()

# retrieve details about an API key
def getIAMDetails(api_key, iam_token):
    url     = "https://iam.cloud.ibm.com/v1/apikeys/details"
    headers = { "Authorization" : iam_token, "IAM-Apikey" : api_key, "Content-Type" : "application/json" }
    response  = requests.get( url, headers=headers )
    return response.json()

# retrieve the list of accounts accessible using the token
def getAccounts(iam_token):
    url     = "https://accounts.cloud.ibm.com/v1/accounts"
    headers = { "Authorization" : iam_token }
    response  = requests.get( url, headers=headers )
    return response.json()

# retrieve all API keys for the given IAM ID (user or service)
def getApiKeys(iam_token, account_id, iam_id):
    pagesize=100
    url = 'https://iam.cloud.ibm.com/v1/apikeys'
    headers = { "Authorization" : iam_token }
    payload = {"account_id": account_id, "iam_id": iam_id, "pagesize":pagesize}
    response = requests.get(url, headers=headers, params=payload)
    result=response.json()
    temp=result
    while 'next' in temp:
        payload = {"account_id": account_id, "iam_id": iam_id, "pagesize":pagesize, "pagetoken":extractNextPageToken(temp['next'])}
        response=requests.get(url, headers=headers, params=payload)
        temp=response.json()
        result['apikeys'].extend(temp['apikeys'])
    return result

# get the details for an API key, including history and activities
def getApiKeyDetails(iam_token, apikey_id):
    url = 'https://iam.cloud.ibm.com/v1/apikeys/{}'.format(apikey_id)
    headers = { "Authorization" : iam_token }
    # we want EVERYTHING
    payload={"include_history":True, "include_activity":True}
    response = requests.get(url, headers=headers, params=payload)
    return response.json()

# retrieve the list of service IDs
def getServiceIDs(iam_token, account_id):
    pagesize=5
    url = 'https://iam.cloud.ibm.com/v1/serviceids'
    headers = { "Authorization" : iam_token }
    payload = {"account_id": account_id, "pagesize": pagesize}
    response = requests.get(url, headers=headers, params=payload)
    result=response.json()
    temp=result
    while 'next' in temp:
        payload = {"account_id": account_id, "pagesize":pagesize, "pagetoken":extractNextPageToken(temp['next'])}
        response=requests.get(url, headers=headers, params=payload)
        temp=response.json()
        result['serviceids'].extend(temp['serviceids'])
    return result

# loop over all the API keys for the (user / service) ID and retrieve the details
def getAndPrintAPIKeys(iam_token, account_id, iam_id):
    api_key_list=getApiKeys(iam_token, account_id, iam_id)
    for apikey in api_key_list['apikeys']:
        print(apikey)
        apikey_details=getApiKeyDetails(iam_token, apikey['id'])
        # some tricky printing because "activity" and last_authn might not be present
        print("{},{},{},{},{},{},{}".format(apikey_details['iam_id'],apikey_details['created_by'],
                                            apikey_details['created_at'],apikey_details['name'],apikey_details['id'],
                                            apikey_details.get('activity',{}).get('last_authn',None),
                                            apikey_details.get('activity',{}).get('authn_count', None)))

# retrieve details on API keys for the current user and the related service IDs
def getEverything(iam_token,account_id, iam_id):
    print('iam_id, created_by, created_at, name, id, last_authn, authn_count')
    print('=================================================================')
    getAndPrintAPIKeys(iam_token, account_id, iam_id)
    serviceids=getServiceIDs(iam_token, account_id)
    for serviceid in serviceids['serviceids']:
        print()
        getAndPrintAPIKeys(iam_token, account_id, serviceid['iam_id'])

# use split and base64 to get to the content of the IAM token
def extractAccount(iam_token):
    data = iam_token.split('.')
    padded = data[1] + "="*divmod(len(data[1]),4)[1]
    jsondata = json.loads(base64.urlsafe_b64decode(padded))
    return jsondata


# some help
def printHelp(progname):
    print ("Usage: "+progname+" [credential-file]")

if __name__== "__main__":
    credfile=None
    iam_token=None
    iam_id=None
    account_id=None

    # do we have any parameters like the credential file?
    # if not, let's try to obtain the token from environment
    if (len(sys.argv)<2):
        if 'IBMCLOUD_TOKEN' in os.environ:
            iam_token=os.getenv('IBMCLOUD_TOKEN')
            token_data=extractAccount(iam_token)
            account_id=token_data["account"]["bss"]
            iam_id=token_data['iam_id']
        else:
            printHelp(sys.argv[0])
            exit()
    elif (len(sys.argv)==2):
        credfile=sys.argv[1]
    else:
        print ("unknown options")
        printHelp(sys.argv[0])
        exit()

    # we don't have a token yet
    if iam_token is None:
        print ("Reading credentials")
        apiKey=readApiKey(credfile)
        print ("generating auth tokens")
        authTokens=getAuthTokens(api_key=apiKey)
        #print ("authTokens:")
        print (json.dumps(authTokens, indent=2))
        iam_token='Bearer '+authTokens["access_token"]   


        print ("Getting account details")
        accDetails=getIAMDetails(api_key=apiKey, iam_token=iam_token)
        account_id=accDetails['account_id']
        iam_id=accDetails['iam_id']
  
    
    # do the work
    getEverything(iam_token, account_id, iam_id)
