import requests
import json
from utils.Sigma2MetadataObjects import classdict as c

metadata = c['InitialMetadata'](title="My second test", \
                                description="Some description", \
                                state="RAW", \
                                created="2021-05-11")


metadata.category = [c['Category'](name="OBSERVATION")]
metadata.language = [c['Language'](name="English")]
metadata.subject = [c['Subject'](domain="Professional and Applied sciences",
                                 field="Engineering",
                                 subfield="Environmental engineering")]

metadata.article = [c['Publication']()]
metadata.article[0].publication = c['NoPublication'](no_publication=True,
                                                     motivation="Some text")
metadata.contributor = [c['Contributor'](uploader=True)]
metadata.contributor[0].member = c['Person'](firstname="Odd",
                                             lastname="Andersen",
                                             email="odd.andersen@sintef.no",
                                             federatedid="oddan@rnd.feide.no")
metadata.data_manager = [c['DataManager']()]
metadata.data_manager[0].manager = c['Person'](firstname="Adil",
                                               lastname="Hasan",
                                               email="adilhasan2@gmail.com",
                                               federatedid="ahasan@rnd.feide.no")
metadata.rights_holder = c['RightsHolder'](holder=c['Person'](firstname="Adil",
                                                              lastname="Hasan",
                                                              email="adilhasan2@gmail.com",
                                                              federatedid="ahasan@rnd.feide.no"))
metadata.creator = [c['Creator']()]
metadata.creator[0].creator = c['CreatorPerson'](firstname="Odd",
                                                 lastname="Andersen",
                                                 email="odd.andersen@sintef.no")


def submit_metadata(username, password):

    token_url = 'https://staging.web.archive-api.sigma2.no/token'
    
    headers = {'content-type': 'application/x-www-form-urlencoded',
               'accept': 'application/json'}
    data = {'grant_type': [], 'username': username,
            'password': password,
            'scope': [], 'client_id': [], 'client_secret': []}
    res = requests.post(token_url, headers=headers, data=data)
    
    token = json.loads(res.content)

    upload_url = 'https://staging.web.archive-api.sigma2.no/api/dataset/'
    headers = {'accept': 'application/json',
               'Authorization': 'Bearer ' + token['access_token'],
               'content-type': 'application/json'}  
    data = metadata.toJSON()

    #@@@ The following call returns a 405.  Investigate
    # pdb.set_trace()
    res = requests.post(upload_url, headers=headers, data=data)



