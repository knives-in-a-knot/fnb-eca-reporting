import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import time
import json
from lxml import etree
import csv

start_time = time.time()

txn_url = 'https://admin.fnb.avoka-transact.com/manager/secure/rest/fluentapi/txnquery/listValues'
job_url = 'https://admin.fnb.avoka-transact.com/manager/secure/rest/fluentapi/jobquery/listValues'
decline_url = 'https://admin.fnb.avoka-transact.com/manager/secure/rest/fluentapi/txnquery/firstValue'

with open('credentials.json') as config_file:
    config = json.load(config_file)
    username = config['username']
    password = config['password']

# the numbers that follow the month represent hours, minutes, and seconds
startDate = datetime(2024, 5, 17, 0, 0, 0)
endDate = datetime(2024, 5, 23, 23, 59, 59)

# "setId": "926710",

data = {
    "setFormCode": "fnb-personal-dev",
    "hasDataExtract": "PrimaryName",
    "addOrderByAsc": "id",
    "setFetchLimit": "3000",
    "setStartDate": startDate.isoformat() + " MDT",
    "setEndDate": endDate.isoformat() + " MDT",
    "withFormXml": "true",
    "withFormDataMap": "true"
}

#print(data)

depositList = ["savings", "checking", "certificate of deposit", "special certificate of deposit"]

response = requests.post(txn_url, json=data, auth=HTTPBasicAuth(username, password))

with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(["eCA ID", "eCA Tracking Code", "App Start Date", "App Submit Date", "App Update Date", "App Status", "Manual Review Decision", "Decline Reason", "Primary Name", "Primary SSN", "New/Existing", "Number of Co-Applicants", "Product 1", "Product List", "Number of Products", "Number of Deposit Products", "Number of Lending Products", "Funding Type", "Total Funding Amount", "Product Funding Amount", "Promo Codes", "Cross Sell Product", "Opt In"])

#print("eCA ID, eCA Tracking Code, App Start Date, App Submit Date,App Update Date, App Status, Decline Reason, Primary Name, Primary SSN, New/Existing, Number of Co-Applicants, Product 1, Product List, Number of Products, Number of Deposit Products, Number of Lending Products, Funding Type, Total Funding Amount")

if response.status_code == 200:
    json_obj = response.json()
    txn_count = 0
    app_count = 0
    for obj in json_obj:
        productList = []
        promoCodeList = []
        #crossSellIdList = []
        amountToFund = []
        jobSteps = []
        depositCount = 0
        lendingCount = 0
        txn_count += 1
        txn_id = obj['id']
        trackingCode = obj['trackingCode']
        jobRefNumber = obj['jobRefNumber']
        formXML = obj.get('formXml', {})
        formXML = formXML[formXML.index('?>') + 2:]
        root = etree.fromstring(formXML)
        formDataMap = obj.get('formDataMap', {})
        if obj['timeCreated']:
            timeCreated = obj['timeCreated']
        else:
            timeCreated = ""
        if obj['timeCompleted']:
            timeCompleted = obj['timeCompleted']
        else:
            timeCompleted = ""
        if obj['timeUserLastModified']:
            timeUserLastModified = obj['timeUserLastModified']
        else:
            timeUserLastModified = ""
        formStatus = obj['formStatus']
        primaryName = formDataMap.get("PrimaryName", "")
        primarySSN = formDataMap.get("PrimarySSN", "")
        paymentMethod = formDataMap.get("PaymentMethod", "")
        totalAmountToFund = root.find("./AvokaSmartForm/ShoppingCart/TotalAmountToFund")
        if totalAmountToFund.text:
            paymentTotal = totalAmountToFund.text
        else:
            paymentTotal = ''
        amountToFundNodes = root.findall("./AvokaSmartForm/ShoppingCart/Products/Product/AccountDetails/AmountToFund")
        for i in range(len(amountToFundNodes)):
            if amountToFundNodes[i] is not None and amountToFundNodes[i].text:
                amountToFund.append(amountToFundNodes[i].text)
            else:
                amountToFund.append('0')
        isCurrentCustomer = root.find("./AvokaSmartForm/Customers/Primary/IsCurrentCustomer")
        isCurrentCustomerShoppingCart = root.find("./AvokaSmartForm/Customers/Primary/IsCurrentCustomerShoppingCart")
        customerType = ''
        if isCurrentCustomer is not None and (isCurrentCustomer.text == "true" or isCurrentCustomerShoppingCart.text == "true"):
            customerType = "Existing"
        elif isCurrentCustomer is not None and (isCurrentCustomer.text == "false" or isCurrentCustomerShoppingCart.text == "false"):
            customerType = "New"
        full_name_nodes = root.findall("./AvokaSmartForm/Customers/AdditionalCustomers/Customer/FullName")
        additionalCustomers = sum(1 for node in full_name_nodes if node.text and node.text.strip())
        product_id_nodes = root.findall("./AvokaSmartForm/ShoppingCart/Products/Product/Id")
        product_type_nodes = root.findall("./AvokaSmartForm/ShoppingCart/Products/Product/Type")
        if len(product_id_nodes) > 0:
            firstProduct = product_id_nodes[0].text
        else:
            firstProduct = ''
        for i in range(len(product_id_nodes)):
            productList.append(product_id_nodes[i].text)
            #print("id:",product_id_nodes[i].text,"type:",product_type_nodes[i].text)
            if product_type_nodes[i].text and product_type_nodes[i].text.lower() in depositList:
                depositCount += 1
            elif product_type_nodes[i].text and product_id_nodes[i].text != "000":
                lendingCount += 1
        promoCodeNodes = root.findall("./AvokaSmartForm/ShoppingCart/Products/Product/Promotions/Promotion/Code")
        promoNameNodes = root.findall("./AvokaSmartForm/ShoppingCart/Products/Product/Promotions/Promotion/Name")
        for i in range(len(promoCodeNodes)):
            promoCodeList.append(promoCodeNodes[i].text + ": " + promoNameNodes[i].text)
        #if promoCodeNode.text:
        #    promoCode = promoCodeNode.text
        #else:
        #    promoCode = ''
        crossSellIdNode = root.find("./AvokaSmartForm/ShoppingCart/CrossSellProducts/CrossSellProduct/Id")
        crossSellNameNode = root.find("./AvokaSmartForm/ShoppingCart/CrossSellProducts/CrossSellProduct/Name")
        #for i in range(len(crossSellNodes)):
        #    crossSellIdList.append(crossSellNodes[i].text)
        if crossSellIdNode is not None and crossSellIdNode.text and crossSellNameNode.text:
            crossSellProductId = crossSellIdNode.text
            crossSellProductName = crossSellNameNode.text
            crossSellProductText = crossSellProductId + ": " + crossSellProductName
        else:
            crossSellProductId = ''
            crossSellProductName = ''
            crossSellProductText = ''
        #addCrossSellNode = root.find("./AvokaSmartForm/ShoppingCart/CounterOfferProduct/AddCrossSellProduct")
        #if crossSellNode.text:
        #    addCrossSell = addCrossSellNode.text
        #else:
        #    addCrossSell = ''

        #print("ID:", txn_id)
        #print("  trackingCode:", trackingCode)
        #print("  jobRefNumber:", jobRefNumber)
        #print("  formStatus:", formStatus)
        #print("  timeCreated:", timeCreated)
        #print("  timeCompleted:", timeCompleted)
        #print("  timeUserLastModified:", timeUserLastModified)
        #print("  primaryName:", primaryName)
        #print("  primarySSN:", primarySSN)
        #print("  paymentMethod:", paymentMethod)
        #print("  formXML:", formXML)
        #print("  totalAmountToFund:", totalAmountToFund.text)
        #print("  paymentTotal:", paymentTotal)
        #print("  isCurrentCustomer:", isCurrentCustomer.text, "isCurrentCustomerShoppingCart:", isCurrentCustomerShoppingCart.text)
        #print("  customerType:", customerType)
        #print("  additionalCustomers:", additionalCustomers)
        #print("  firstProduct:", firstProduct)
        #print("  productList:", "|".join(productList))
        #print("  depositCount:", depositCount)
        #print("  lendingCount:", lendingCount)

        if obj['jobRefNumber'] and jobRefNumber == trackingCode:
            app_count += 1
            job_data = {
                "addOrderByAsc": "timeLastProcessed",
                "setReferenceNumber": trackingCode,
                "setFetchLimit": "1",
            }
            job_response = requests.post(job_url, json=job_data, auth=HTTPBasicAuth(username, password))
            lastStep = ''
            decline_summary = ''
            if job_response.status_code == 200:
                job_json_obj = job_response.json()
                #print(response.json())
                for job in job_json_obj:
                    #jobSteps = job_json_obj['jobSteps']
                    #print("job id:", job['id'])
                    for step in job['jobSteps']:
                        jobSteps.append(step['name'])
                        #print("step name:", step['name'])
                        lastStep = step['name']
                        if step['name'] == 'Decline Application':
                            #print('*** IS DECLINED ***')
                            decline_data = {
                                "setId": f"{txn_id}",
                                "withPropertyMap": True
                            }
                            decline_response = requests.post(decline_url, json=decline_data, auth=HTTPBasicAuth(username, password))
                            if decline_response.status_code == 200:
                                decline_json_obj = decline_response.json()
                                propertyMap = decline_json_obj.get('propertyMap', {})
                                number_of_keys = len(propertyMap)
                                if number_of_keys == 0:
                                    print(f"***    No keys in propertyMap for txn_id: {txn_id}, skipping to next. ***")
                                    continue  # Skip to the next iteration if no keys in propertyMap
                                alloyResponseStr = propertyMap.get('alloy.entitiesComplete.Response', {})
                                alloyResponse = json.loads(alloyResponseStr)
                                embedded = alloyResponse.get('_embedded', {})
                                events = embedded.get('events', [])
                                if events:
                                    for event in embedded["events"]:
                                        evaluation_result = event.get('evaluation_result', {})
                                        summary = evaluation_result.get('summary', {})
                                        outcome = summary.get('outcome', {})
                                        if (outcome == 'Denied'):
                                            decline_summary = json.dumps(summary, indent=4)
                                            decline_summary = '"' + decline_summary + '"'
            #print("jobSteps: ",jobSteps)
            manualReviewDecision = ''
            try:
                index = jobSteps.index('Review Application')
                # Check if there is a next step
                if index + 1 < len(jobSteps):
                    print(jobSteps[index + 1])
                    manualReviewDecision = jobSteps[index + 1]
                else:
                    print("There is no next step after 'Review Application'.")
            except ValueError:
                pass

            with open('output.csv', 'a', newline='', encoding='utf-8') as csvfile:
                csvwriter = csv.writer(csvfile)
                if crossSellProductId in productList:
                    csvwriter.writerow([txn_id, trackingCode, timeCreated, timeCompleted, timeUserLastModified, lastStep, manualReviewDecision, decline_summary, primaryName, primarySSN, customerType, additionalCustomers, firstProduct, "|".join(productList), len(product_id_nodes), depositCount, lendingCount, paymentMethod, paymentTotal, "|".join(amountToFund),"|".join(promoCodeList), crossSellProductText, "Y"])
                else:
                    csvwriter.writerow([txn_id, trackingCode, timeCreated, timeCompleted, timeUserLastModified, lastStep, manualReviewDecision, decline_summary, primaryName, primarySSN, customerType, additionalCustomers, firstProduct, "|".join(productList), len(product_id_nodes), depositCount, lendingCount, paymentMethod, paymentTotal, "|".join(amountToFund), "|".join(promoCodeList), crossSellProductText, ''])

            print(txn_id, trackingCode, timeCreated, timeCompleted, timeUserLastModified, lastStep, decline_summary, primaryName, primarySSN, customerType, additionalCustomers, firstProduct, "|".join(productList), len(product_id_nodes), depositCount, lendingCount, paymentMethod, paymentTotal, sep=', ')
            print("promoCodeList: ", "|".join(promoCodeList), "crossSellProductId: ", crossSellProductId, "productList: ", "|".join(productList))
            if crossSellProductId in productList:
                print(f"{crossSellProductId} is in productList." + " " + crossSellProductName)

            #print("  lastStep:", lastStep)
        else:
            with open('output.csv', 'a', newline='', encoding='utf-8') as csvfile:
                csvwriter = csv.writer(csvfile)
                if crossSellProductId in productList:
                    csvwriter.writerow([txn_id, trackingCode, timeCreated, timeCompleted, timeUserLastModified, formStatus, '', '', primaryName, primarySSN, customerType, additionalCustomers, firstProduct, "|".join(productList), len(product_id_nodes), depositCount, lendingCount, paymentMethod, paymentTotal, "|".join(amountToFund), "|".join(promoCodeList), crossSellProductText, "Y"])
                else:
                    csvwriter.writerow([txn_id, trackingCode, timeCreated, timeCompleted, timeUserLastModified, formStatus, '', '', primaryName, primarySSN, customerType, additionalCustomers, firstProduct, "|".join(productList), len(product_id_nodes), depositCount, lendingCount, paymentMethod, paymentTotal, "|".join(amountToFund), "|".join(promoCodeList), crossSellProductText, ''])

            #print(txn_id, trackingCode, timeCreated, timeCompleted, timeUserLastModified, formStatus, '', primaryName, primarySSN, customerType, additionalCustomers, firstProduct, "|".join(productList), len(product_id_nodes), depositCount, lendingCount, paymentMethod, paymentTotal, sep=', ')
            print("promoCodeList: ", "|".join(promoCodeList), "crossSellProductId: ", crossSellProductId, "productList: ", "|".join(productList))
            if crossSellProductId in productList:
                print(f"{crossSellProductId} is in productList." + " " + crossSellProductName)


print("")
print("Number of txns:", txn_count)
print("Number of apps:", app_count)
end_time = time.time()
elapsed_time = end_time - start_time
print("Elapsed time:", elapsed_time, "seconds")