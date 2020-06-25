# Dicom image processing pipeline example

This is not out of box running version. This project is for a presentation 
purposes and how to structure microservice oriented event-driven architecture 
with several supporting packages. There are missing bits and piece :-)

Original structure is using git submodules, but for convenience and showcase 
everything is linked into project. Supporting packages, services and apis all should be submodules.

Infrastructure folders should live in their own DevOps projects.

## General architecture and folder structure

This project shows how to process CT scans (dicom files) store them, 
process them and return prediction result 

#### Ingestion API

Endpoints:

    /api/v1/files
    /api/v1/files/<filepath>
    /api/v1/predict/<ID>

Logic:

    API accepts dicom format images and uploads them to the GCS. We have a pubsub notification created when object is created in GCS which is pulled by our microservices
    
    API works on pulling method, where /predict returns the current status of prediction and filepath where to download the result
    
Folders:

    ./flaskapp  - core flaskapp boilertemplate
    ./apis      - implementation of files and predict endpoints
    
### Services

Each service has it's pubsub topic and subscription
Service pulls messages, processes file describe in the 
message and uploads results to GCS if necessary

Folders:

    ./services
    
##### Throttler

Reads and monitors the main ingestion queue and throttles amount of 
messages processed in the same time so there is no congestion in the system 

##### Observer

Monitors the status of image processed and triggers next processing step 
when the previous is finished

##### Prediction

Runs prediction for image

##### Boneseg

Combines predicted to images to one bundle (3D image)

### Supporting packages

    apimessages
    gcloudlogging
    gclodredis
    gcloudstorage
    pubsubutils
    
### Infrastructure and deployment

Infrastructure is setup using terraform on GCP. See the terraform folder.
The manifest for deployment of the application can be found in k8s folder.

Unfortunately at the moment all dependent images are in private eu.gcr.io registry - this is the main reason why this project is just showcase.

Folders:

    ./terraform
    ./k8s



