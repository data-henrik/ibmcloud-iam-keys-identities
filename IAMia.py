# Small script to retrieve information about API keys, users and trusted profiles
# in an IBM Cloud account. The information is based on the IAM inactive identities 
# report with a default duration of 0 hours and formats the results in comma-separated values.
# For API keys additional details are retrieved such as the created by and created date.
# For trusted profiles additional details are retreived such as the created date and created date.
# Written by Henrik Loeser, hloeser@de.ibm.com
#            Dimitri Prosper, dimitri_prosper@us.ibm.com

# only standard packages are used, no installation necessary
import requests, json, sys,os, base64
import argparse 
from urllib.parse import urlparse,parse_qs


json_apikeys=[]

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

# retrieve details about an API key
def getIAMDetails(api_key, iam_token):
    url     = "https://iam.cloud.ibm.com/v1/apikeys/details"
    headers = { "Authorization" : iam_token, "IAM-Apikey" : api_key, "Content-Type" : "application/json" }
    try:
        response  = requests.get( url, headers=headers )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return response.json()

# get the details for an API key, including history and activities
def getApiKeyDetails(iam_token, apikey_id):
    url = 'https://iam.cloud.ibm.com/v1/apikeys/{}'.format(apikey_id)
    headers = { "Authorization" : iam_token }
    # we want activity included
    payload={"include_activity":True}
    try:
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    return response.json()

# get the details for a trusted profile, including activities
def getTrustedProfileDetails(iam_token, profile_id):
    url = 'https://iam.cloud.ibm.com/v1/profiles/{}'.format(profile_id)
    headers = { "Authorization" : iam_token }
    # we want activity included
    payload={"include_activity":True}
    try:
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    return response.json()

# loop over the IAM Inactive Identities Report (apikeys / users / trusted profiles) ID and retrieve the details
def getAndPrintInactiveIdentitiesReport(iam_token, account_id, iam_id, report_id, level, out_format):
    url = 'https://iam.cloud.ibm.com/v1/activity/accounts/{}/report/{}'.format(account_id,report_id)
    headers = { "Authorization" : iam_token, "Content-Type" : "application/json" }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    result=response.json()

    if out_format=='JSON':
        print(json.dumps(result, indent=2))
        return


    print('iam_id,name,last_authn,type,id,name,username,email,created_by,created_at,locked,authn_count')
    for apikey in result['apikeys']:
         if apikey['type']=='serviceid':
            if level=='standard':
               print("{},{},{},{},{},{}".format(apikey['id'],apikey['name'], apikey.get('last_authn',None), 
                     apikey['type'], apikey['serviceid']['id'], apikey['serviceid']['name'] ))
            else:
               apikey_details=getApiKeyDetails(iam_token, apikey['id'])
               print("{},{},{},{},{},{},{},{},{},{},{},{}".format(apikey['id'], apikey['name'], apikey.get('last_authn',None), 
                     apikey['type'], apikey['serviceid']['id'], apikey['serviceid']['name'], 
                     '','',
                     apikey_details['created_by'], apikey_details['created_at'], apikey_details['locked'], apikey_details.get('activity',{}).get('authn_count', None) ))

         if apikey['type']=='user':
            if level=='standard':
               print("{},{},{},{},{},{},{},{}".format(apikey['id'],apikey['name'], apikey.get('last_authn',None), 
                     apikey['type'], apikey['user']['iam_id'], apikey['user']['name'], 
                     apikey['user']['username'], apikey['user']['email'] ))
            else:
               apikey_details=getApiKeyDetails(iam_token, apikey['id'])
               print("{},{},{},{},{},{},{},{},{},{},{},{}".format(apikey['id'],apikey['name'], apikey.get('last_authn',None), 
                     apikey['type'], apikey['user']['iam_id'], apikey['user']['name'], 
                     apikey['user']['username'], apikey['user']['email'],
                     apikey_details['created_by'], apikey_details['created_at'], apikey_details['locked'], apikey_details.get('activity',{}).get('authn_count', None) ))

    for profile in result['profiles']:
         if level=='standard':
            print("{},{},{}".format(profile['id'], profile['name'], profile.get('last_authn',None) ))
         else:
            trusted_profile_details=getTrustedProfileDetails(iam_token, profile['id'])
            print("{},{},{},{},{},{},{},{},{},{},{},{}".format(profile['id'], profile['name'], profile.get('last_authn',None), 
                  '','','',
                  '', '',
                  '', trusted_profile_details['created_at'], '', trusted_profile_details.get('activity',{}).get('authn_count', None) ))

    for user in result['users']:
         if level=='standard':
            print("{},{},{},{},{},{},{},{}".format(user['iam_id'], user['name'], user.get('last_authn',None),
                  '','','', 
                  user['username'], user['email'] ))
         else:
            print("{},{},{},{},{},{},{},{}".format(user['iam_id'], user['name'], user.get('last_authn',None),
                  '','','', 
                  user['username'], user['email'] ))

# trigger an activity report
def triggerReport(iam_token, account_id, duration):
    url = 'https://iam.cloud.ibm.com/v1/activity/accounts/{}/report?duration={}'.format(account_id,duration)
    headers = { "Authorization" : iam_token }
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    return response.json()

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
    report_id=None

    # define the command line arguments
    parser = argparse.ArgumentParser(description='Retrieve information from IAM Inactive Identities report in an IBM Cloud account')
    parser.add_argument('--action', choices=['trigger','get'], dest='action', default='get',
                        help='trigger or get a report')
    parser.add_argument('--output', choices=['CSV','JSON'], dest='out_format', default='CSV',
                        help='return output in CSV or JSON format')
    parser.add_argument('--credentials', type=str, action='store', dest='credfile', help='credential file to use')
    parser.add_argument('--duration', type=int, dest='duration', default=0, help='Optional duration of the report, supported unit of duration is hours')
    parser.add_argument('--level', choices=['standard','advanced'], dest='level', default='standard', 
                        help='Retrieve information from the report only (standard) or more detailed - takes longer to run - leveraging the APIs (advanced).')
    parser.add_argument('--reportid', type=str, action='store', dest='reportid', default='latest', help='the report to retrieve')
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
  
    # either trigger a new report or
    if args.action=='trigger':
        report=triggerReport(iam_token, account_id, args.duration)
        report_id=report['reference']
        print("The report ID is: {}".format(report_id))
    # retrieve an existing report
    elif args.action=='get':
        getAndPrintInactiveIdentitiesReport(iam_token, account_id, iam_id, args.reportid, args.level, args.out_format)
        
