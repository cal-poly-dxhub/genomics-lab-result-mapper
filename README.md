# genomics-lab-result-mapper

Front end Web Site: https://genomics-dev.calpoly.io/
API Endpoint : https://genomics-api-dev.calpoly.io/


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
