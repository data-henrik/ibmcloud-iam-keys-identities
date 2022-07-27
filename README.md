# Information about inactive identities and API keys in your IBM Cloud account
Retrieve information about IBM Cloud IAM keys and identify inactive identities


### Preparation
All commands and scripts can be run in IBM Cloud Shell. The following steps are needed to get started.
1. Visit https://cloud.ibm.com, if not done log in, then open the [IBM Cloud Shell](https://cloud.ibm.com/shell).
2. In the new terminal, set an environment variable with the access token for you session:
   ```sh
   export IBMCLOUD_TOKEN=$(ibmcloud iam oauth-tokens --output json | jq -r '.iam_token')
   ```
3. Set an environment variable with the account ID:
   ```
   export IBMCLOUD_ACCOUNTID=$(ibmcloud account show --output json | jq -r '.account_id')
   ```


### Use curl to trigger and retrieve report on inactive identities
With the above preparations, you can use the command line investigate inactive identities in your IBM Cloud account.

1. Trigger a new report about inactive identities. The result is the reference to the new report.
   ```
   curl -X POST "https://iam.cloud.ibm.com/v1/activity/accounts/${IBMCLOUD_ACCOUNTID}/report" -H "Authorization: ${IBMCLOUD_TOKEN}" -H 'Content-Type: application/json' 
   ```
   By default, the duration is 720 hours which is 30 days. You can change the duration by passing in an additional parameter. Adapt it to your preferences (shown for 90 days):
   ```
   curl -X POST "https://iam.cloud.ibm.com/v1/activity/accounts/${IBMCLOUD_ACCOUNTID}/report?duration=2160" -H "Authorization: ${IBMCLOUD_TOKEN}" -H 'Content-Type: application/json' 
   ```
2. A some seconds to minute, you can retrieve the report. Using **latest** as reference, the latest available report is returned. Replace **latest** with the reference from the previous command to retrieve that specific report.
   ```
   curl -s -X GET "https://iam.cloud.ibm.com/v1/activity/accounts/${IBMCLOUD_ACCOUNTID}/report/latest" -H "Authorization: ${IBMCLOUD_TOKEN}" -H 'Content-Type: application/json' | jq
   ```

### Use Python to investigate your API keys and service IDs

1. Download and save the Python script:
   ```
   curl -s https://raw.githubusercontent.com/data-henrik/ibmcloud-iam-keys-identities/main/IAMkeys.py
   ```

2. Run the Python script:
   ```
   python3 IAMkeys.ps
   ```


## License
See the [LICENSE](LICENSE) file.