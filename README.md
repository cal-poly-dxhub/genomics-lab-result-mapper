# genomics-lab-result-mapper

Front end Web Site: https://genomics-dev.calpoly.io/
API Endpoint : https://genomics-api-dev.calpoly.io/


# Helpdesk Chatbot Solution

# Collaboration
Thanks for your interest in our solution.  Having specific examples of replication and cloning allows us to continue to grow and scale our work. If you clone or download this repository, kindly shoot us a quick email to let us know you are interested in this work!

[wwps-cic@amazon.com] 

# Disclaimers

**Customers are responsible for making their own independent assessment of the information in this document.**

**This document:**

(a) is for informational purposes only, 

(b) represents current AWS product offerings and practices, which are subject to change without notice, and 

(c) does not create any commitments or assurances from AWS and its affiliates, suppliers or licensors. AWS products or services are provided “as is” without warranties, representations, or conditions of any kind, whether express or implied. The responsibilities and liabilities of AWS to its customers are controlled by AWS agreements, and this document is not part of, nor does it modify, any agreement between AWS and its customers. 

(d) is not to be considered a recommendation or viewpoint of AWS

**Additionally, all prototype code and associated assets should be considered:**

(a) as-is and without warranties

(b) not suitable for production environments

(d) to include shortcuts in order to support rapid prototyping such as, but not limited to, relaxed authentication and authorization and a lack of strict adherence to security best practices

**All work produced is open source. More information can be found in the GitHub repo.**

## Authors
- Noor Dhaliwal - rdhali07@calpoly.edu

## Table of Contents
- [Overview](#genomics-overview)
- [Backend Services](#backend-services)
- [Additional Resource Links](#additional-resource-links)

## Genomics Mapper Overview
- The [DxHub](https://dxhub.calpoly.edu/challenges/) developed a data mapping solution that takes an input .csv or .xlsx file containing the masterdata for a lab's genomics data and maps it to the SRA and Biosample formats for NCBI submission.

## Steps to Deploy and Configure the System

### Before We Get Started

- Request and ensure model access within AWS Bedrock, specifically:
    - Claude 3

The corresponding model ID is:
```
anthropic.claude-3-sonnet-20240229-v1:0
```

### 1. Deploy an EC2 Instance
- Deploy an EC2 instance in your desired region and configure it as required (i.e grant a role with required managed polices).

- CDK will require Administrator Permissions 

### 2. Pull the Git Repository
- Install git using this command 
    ```
    sudo yum install git
    ```

- Clone the necessary repository to the EC2 instance:
    ```bash
    git clone https://github.com/cal-poly-dxhub/helpdesk-chatbot.git
    ```

### 3. Run OpenSearch CDK

- Install Node.js for cdk
    ```
    sudo yum install -y nodejs
    ```

- Install cdk
    ```
    sudo npm install -g aws-cdk
    ```

- Install python 3.11
    ```
    sudo yum install python3.11
    ```
    
- Install pip3.11
    ```
    curl -O https://bootstrap.pypa.io/get-pip.py

    python3.11 get-pip.py --user
    ```

- Create and activate venv and install requirements
    ```
    python3.11 -m venv env

    source env/bin/activate

    cd genomics-lab-result-mapper

    pip3.11 install -r requirements.txt
    ```

- CDK deploy 
    ```
    cd cdk

    cdk synth

    cdk bootstrap

    cdk deploy --all

    ```

### 4. URLs
- Locate the API URL in API Gateway.
- Locate the frontend interface URL in the S3 Bucket containing the static website contents.
- HTTPS and domain configuration will need to be done as needed.
  
By following these steps, you will have a properly deployed and configured system with the desired settings.


## Known Bugs/Concerns
- Quick PoC with no intent verification or error checking

## Support
For any queries or issues, please contact:
- Darren Kraker, Sr Solutions Architect - dkraker@amazon.com
- Noor Dhaliwal, Software Developer Intern - rdhali07@calpoly.edu


### Query Parameters:

1. **`file_name`** (required)  
   - **Description**: The name of the file to upload or download.  
   - **Example**: `example.csv` or `example.xlsx`

2. **`json_rules`** (optional)  
   - **Description**: JSON content to save as rules in the S3 bucket.  
   - **Example**: `{"lab_column": "sra_column"}`

3. **`json_static_rules`** (optional)  
   - **Description**: JSON content to save as static rules in the S3 bucket.  
   - **Example**: `{"column_name": "static_value"}`

4. **`upload`** (required)  
   - **Description**: Indicates if the operation is for uploading or downloading a file.  
   - **Allowed Values**: `true`, `false`

5. **`uuid`** (required for all downloads)  
   - **Description**: A unique identifier for the file used during download operations.  
   - **Example**: `123e4567-e89b-12d3-a456-426614174000`  
   - **Behavior**:
     - Always required when `upload=false`.
     - Used to construct file names and retrieve associated mappings.

6. **`sra`** (optional)  
   - **Description**: Indicates whether the file is related to the Sequence Read Archive (SRA).  
   - **Allowed Values**: `true`, `false`  
   - **Behavior**:
     - If `true`, the file name includes `_sra`, and mappings use `_sra.json`.
     - If `false` or omitted, the file name includes `_biosample`, and mappings use `_biosample.json`.



### Response Variables:

1. **`url`**  
   - **Description**: A presigned URL for uploading or downloading the file. Can do a PUT request with file to upload to it.
  
2. **`file_name`**  
   - **Description**: The name of the file in the S3 bucket, including the `uuid` and any suffix (`_sra` or `_biosample`).  
   - **Example**: `123e4567-e89b-12d3-a456-426614174000_example_sra.csv`

3. **`uuid`**  
   - **Description**: The unique identifier associated with the file.  
   - **Example**: `123e4567-e89b-12d3-a456-426614174000`

4. **`mappings`** (only for downloads)  
   - **Description**: The content of the mappings file associated with the `uuid`, if available.  



### Behavior Summary:

- **Upload (`upload=true`)**:
  - Requires `file_name`.
  - Generates a unique `uuid` automatically.
  - Saves optional JSON rules (`json_rules`, `json_static_rules`) in S3.
  - **Response**: Returns the presigned upload URL, the file name, and the generated `uuid`.

- **Download (`upload=false`)**:
  - Requires `file_name` and **`uuid`**.
  - Constructs file names and retrieves mappings based on `uuid` and optionally on `sra`.
  - **Response**: Returns the presigned download URL, the file name, the `uuid`, and the associated mappings (if available).  
