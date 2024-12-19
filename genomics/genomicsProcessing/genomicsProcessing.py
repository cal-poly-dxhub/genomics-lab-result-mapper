import json
import boto3
import pandas as pd
from botocore.exceptions import ClientError
import io
import re
import os

def handler(event, context):
    # Extract the S3 bucket name from the event and verify it contains "genomicsuploaddownload"
    record = event['Records'][0]
    bucket_name = record['s3']['bucket']['name']
    
    if "genomicsuploaddownload" not in bucket_name:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Bucket name does not contain 'genomicsuploaddownload'."})
        }

    # Extract file details
    file_key = record['s3']['object']['key']
    file_uuid = file_key.split('/')[1].split('_')[0]
    file_name_with_extension = file_key.split('/')[1]
    file_name_without_extension = os.path.splitext(file_name_with_extension)[0]

    s3Client = boto3.client('s3')

    # Retrieve the file content from S3
    try:
        response = s3Client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = response['Body'].read()
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to get object from bucket '{bucket_name}': {str(e)}"})
        }

    # Determine file extension and read the file accordingly
    file_extension = file_key.split('.')[-1].lower() 

    if file_extension == 'csv':
        df = pd.read_csv(io.BytesIO(file_content))
    elif file_extension in ['xlsx', 'xls']:
        df = pd.read_excel(io.BytesIO(file_content))
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Unsupported file type"})
        }
    
    # Process the DataFrame
    processDF(df, bucket_name, file_name_without_extension, file_uuid, s3Client)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def processDF(df, bucket_name, file_name_without_extension, file_uuid, s3Client):
    required_sra_columns = [
        "sample_name", "library_ID", "title", "library_strategy", "library_source",
        "library_selection", "library_layout", "platform", "instrument_model",
        "design_description", "filetype", "filename", "filename2", "filename3",
        "filename4", "assembly", "fasta_file"
    ]
    required_biosample_columns = [
        "sample_name", "sample_title", "bioproject_accession", "organism", "strain",
        "isolate", "collected_by", "collection_date", "geo_loc_name", "host",
        "host_disease", "isolation_source", "lat_lon"
    ]

    # Extract the first row's data for prompt generation
    column_data = {col: df[col].iloc[0] if not df[col].isnull().all() else "" for col in df.columns}
    sraDf = pd.DataFrame()
    biosampleDf = pd.DataFrame()
    
    # Define mandatory and optional columns (these variables are currently unused but can be utilized for further validations)
    mandatorySRA = ['sample_name','organism','collected_by','collection_date','geo_loc_name','host','host_disease','isolation_source','lat_lon']
    oneMandatorySRA = ['strain','isolate']
    optionalSRA = [
        'sample_title','bioproject_accession','purpose_of_sequencing','genotype',
        'host_age','host_description','host_disease_outcome','host_disease_stage',
        'host_health_state','host_sex','host_subject_id','host_tissue_sampled',
        'passage_history','pathotype','serotype','serovar','specimen_voucher',
        'subgroup','subtype','description'
    ]
    
    # Load manual rules from S3
    rules_key = f"rules/{file_uuid}.json"
    rules = None
    try:
        s3Client.head_object(Bucket=bucket_name, Key=rules_key)
        rules_obj = s3Client.get_object(Bucket=bucket_name, Key=rules_key)
        rules_content = rules_obj['Body'].read().decode('utf-8')
        rules = json.loads(rules_content)
    except Exception as e:
        print(f"Rules file not found or invalid: {e}")
        # Proceed without rules

    # Load static rules from S3
    static_rules_key = f"rules/static_{file_uuid}.json"
    static_rules = None
    try:
        s3Client.head_object(Bucket=bucket_name, Key=static_rules_key)
        static_obj = s3Client.get_object(Bucket=bucket_name, Key=static_rules_key)
        static_rules_content = static_obj['Body'].read().decode('utf-8')
        static_rules = json.loads(static_rules_content)
    except Exception as e:
        print(f"Static rules file not found or invalid: {e}")
        # Proceed without static rules

    # Determine which columns are already mapped via manual rules
    already_mapped_columns_sra = set()
    already_mapped_columns_biosample = set()

    if rules is not None:
        # Identify SRA manual mappings
        if 'sra_manual_mappings' in rules and isinstance(rules['sra_manual_mappings'], dict):
            for input_col, ncbi_col in rules['sra_manual_mappings'].items():
                if input_col in df.columns and ncbi_col != "":
                    already_mapped_columns_sra.add(input_col)

        # Identify Biosample manual mappings
        if 'biosample_manual_mappings' in rules and isinstance(rules['biosample_manual_mappings'], dict):
            for input_col, ncbi_col in rules['biosample_manual_mappings'].items():
                if input_col in df.columns and ncbi_col != "":
                    already_mapped_columns_biosample.add(input_col)

    # Exclude already mapped columns from LLM prompts
    filtered_sra_column_data = {col: val for col, val in column_data.items() if col not in already_mapped_columns_sra}
    filtered_biosample_column_data = {col: val for col, val in column_data.items() if col not in already_mapped_columns_biosample}

    # Generate prompts using filtered column data
    sra_prompt = generate_prompt(filtered_sra_column_data, required_sra_columns, "SRA")
    sra_json_text = invokeModel(sra_prompt)
    sra_json_obj = parse_json_response(sra_json_text)
    sraDf = map_columns(df, sra_json_obj)

    # Ensure all required SRA columns are present
    for col in required_sra_columns:
        if col not in sraDf.columns:
            sraDf[col] = ""

    biosample_prompt = generate_prompt(filtered_biosample_column_data, required_biosample_columns, "Biosample")
    biosample_json_text = invokeModel(biosample_prompt)
    biosample_json_obj = parse_json_response(biosample_json_text)
    biosampleDf = map_columns(df, biosample_json_obj)

    # Ensure all required Biosample columns are present
    for col in required_biosample_columns:
        if col not in biosampleDf.columns:
            biosampleDf[col] = ""

    # Apply manual mappings from rules to SRA and Biosample DataFrames and update mapping JSON objects
    if rules is not None:
        # Apply SRA manual mappings if present
        if 'sra_manual_mappings' in rules and isinstance(rules['sra_manual_mappings'], dict):
            for input_col, ncbi_col in rules['sra_manual_mappings'].items():
                if input_col in df.columns and ncbi_col != "":
                    sraDf[ncbi_col] = df[input_col]
                    sra_json_obj[input_col] = ncbi_col  # Ensure manual mappings are included in the JSON

        # Apply Biosample manual mappings if present
        if 'biosample_manual_mappings' in rules and isinstance(rules['biosample_manual_mappings'], dict):
            for input_col, ncbi_col in rules['biosample_manual_mappings'].items():
                if input_col in df.columns and ncbi_col != "":
                    biosampleDf[ncbi_col] = df[input_col]
                    biosample_json_obj[input_col] = ncbi_col  # Ensure manual mappings are included in the JSON

    # Apply static rules if present
    if static_rules is not None:
        # Apply SRA static rules
        if 'sra_static' in static_rules and isinstance(static_rules['sra_static'], dict):
            for ncbi_col, static_val in static_rules['sra_static'].items():
                sraDf[ncbi_col] = static_val  # Fill entire column with static_val

        # Apply Biosample static rules
        if 'biosample_static' in static_rules and isinstance(static_rules['biosample_static'], dict):
            for ncbi_col, static_val in static_rules['biosample_static'].items():
                biosampleDf[ncbi_col] = static_val  # Fill entire column with static_val

    # Debugging: Print final mappings
    print("Final SRA Mappings (including rules):", json.dumps(sra_json_obj, indent=2))
    print("Final Biosample Mappings (including rules):", json.dumps(biosample_json_obj, indent=2))

    # Write final mappings to JSON files in /mappings
    sra_json_key = f"mappings/{file_uuid}_sra.json"
    biosample_json_key = f"mappings/{file_uuid}_biosample.json"

    try:
        s3Client.put_object(
            Bucket=bucket_name,
            Key=sra_json_key,
            Body=json.dumps(sra_json_obj, indent=2).encode("utf-8"),
            ContentType='application/json'
        )
    except Exception as e:
        print(f"Failed to upload SRA JSON mapping: {str(e)}")

    try:
        s3Client.put_object(
            Bucket=bucket_name,
            Key=biosample_json_key,
            Body=json.dumps(biosample_json_obj, indent=2).encode("utf-8"),
            ContentType='application/json'
        )
    except Exception as e:
        print(f"Failed to upload Biosample JSON mapping: {str(e)}")
 
    # Convert DataFrames to CSV and upload to S3
    sra_csv = sraDf.to_csv(index=False).encode("utf-8")
    biosample_csv = biosampleDf.to_csv(index=False).encode("utf-8")

    sra_key = f"download/{file_name_without_extension}_sra.csv"
    biosample_key = f"download/{file_name_without_extension}_biosample.csv"
    try:
        s3Client.put_object(Bucket=bucket_name, Key=sra_key, Body=sra_csv, ContentType='text/csv')
    except Exception as e:
        print(f"Failed to upload SRA CSV: {str(e)}")
    try:
        s3Client.put_object(Bucket=bucket_name, Key=biosample_key, Body=biosample_csv, ContentType='text/csv')
    except Exception as e:
        print(f"Failed to upload Biosample CSV: {str(e)}")

def generate_prompt(column_data, required_columns, file_type):
    formatted_columns = "\n".join([f"{col}: {value}" for col, value in column_data.items()])
    prompt = f"""
    You are a medical expert who is skilled at converting proprietary
    lab data to the NCBI {file_type} format. A crucial step in this process is
    mapping the columns of the lab's data to the columns of the NCBI {file_type}
    format. Here are the lab's data columns and their first values:
    {formatted_columns}

    Map each of these columns to the NCBI {file_type} columns based on
    your inference of what columns best match to each other:
    {', '.join(required_columns)}
    Return a JSON string object with the format of:
    {{
        "lab column1":"ncbi column1",
        "lab column2":"ncbi column2"
    }}
    For any column that doesn't have a good match or is missing, leave it as an empty string "".
    It is absolutely crucial that you return NOTHING but the JSON.
    """

    if file_type == "SRA":
        prompt += """Here are some sample definitions of the column headers: 
        Header: *sample_name, Comment: Sample Name is a name that you choose for the sample. It can have any format, but we suggest that you make it concise, unique and consistent within your lab, and as informative as possible. Every Sample Name from a single Submitter must be unique.
        Header: sample_title, Comment: Title of the sample.
        Header: bioproject_accession, Comment: The accession number of the BioProject(s) to which the BioSample belongs. If the BioSample belongs to more than one BioProject, enter multiple bioproject_accession columns. A valid BioProject accession has prefix PRJN, PRJE or PRJD, e.g., PRJNA12345.
        Header: *organism, Comment: The most descriptive organism name for this sample (to the species, if possible). It is OK to submit an organism name that is not in our database. In the case of a new species, provide the desired organism name, and our taxonomists may assign a provisional taxID. In the case of unidentified species, choose the appropriate Genus and include 'sp.', e.g., "Escherichia sp.". When sequencing a genome from a non-metagenomic source, include a strain or isolate name too, e.g., "Pseudomonas sp. UK4".
        Header: strain, Comment: Organism group microbial or eukaryotic strain name 
        Header: isolate, Comment: Organism group identification or description of the specific individual from which this sample was obtained
        Header: *collected_by, Comment: Name of persons or institute who collected the sample
        Header: *collection_date, Comment: the date on which the sample was collected; date/time ranges are supported by providing two dates from among the supported value formats, delimited by a forward-slash character; collection times are supported by adding "T", then the hour and minute after the date, and must be in Coordinated Universal Time (UTC), otherwise known as "Zulu Time" (Z); supported formats include "DD-Mmm-YYYY", "Mmm-YYYY", "YYYY" or ISO 8601 standard "YYYY-mm-dd", "YYYY-mm", "YYYY-mm-ddThh:mm:ss"; e.g., 30-Oct-1990, Oct-1990, 1990, 1990-10-30, 2015-10-11T17:53:03Z
        Header: *geo_loc_name, Comment: Geographical origin of the sample; use the appropriate name from this list http://wria, fungi or virus) usually based on its antigenic properties. Same as serovar and serotype. Sometimes used as species identifier in bacteria with shaky taxonomy, e.g. Leptospira, serovar saopaolo S76607 (65357 in Entrez).       
        Header: specimen_voucher, Comment: Identifier for the physical specimen. Use format: "[<institution-code>:[<collection-code>:]]<specimen_id>", eg, "UAM:Mamm:52179". Intended as a reference to the physical specimen that remains after it was analyzed. If the specimen was destroyed in the process of analysis, electronic images (e-vouchers) are an adequate substitute for a physical voucher specimen. Ideally the specimens will be deposited in a curated museum, herbarium, or frozen tissue collection, but often they will remain in a personal or laboratory collection for some time before they are deposited in a curated collection. There are three forms of specimen_voucher qualifiers. If the text of the qualifier includes one or more colons it is a 'structured voucher'. Structured vouchers include institution-codes (and optional collection-codes) taken from a controlled vocabulary maintained by the INSDC that denotes the museum or herbarium collection where the specimen resides, please visit: http://www.insdc.org/controlled-vocabulary-specimenvoucher-qualifier.
        Header: subgroup, Comment: Taxonomy below subspecies; sometimes used in viruses to denote subgroups taken from a single isolate.
        Header: subtype, Comment: Used as classifier in viruses (e.g. HIV type 1, Group M, Subtype A)."""

    return prompt

def parse_json_response(json_text):
    # Extract JSON object from the response text
    json_pattern = re.compile(r'\{.*\}', re.DOTALL)
    match = json_pattern.search(json_text)
    if match:
        json_str = match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}
    else:
        return {}

def map_columns(df, json_mapping):
    # Map columns based on the JSON mapping
    mapped_df = pd.DataFrame()
    for column in df.columns:
        mapping = json_mapping.get(column, "")
        if mapping != "":
            mapped_df[mapping] = df[column]
    return mapped_df

def invokeModel(prompt=""):
    # Invoke the Bedrock model with the given prompt
    client = boto3.client("bedrock-runtime", region_name="us-west-2")
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    }
    request = json.dumps(native_request)
    try:
        response = client.invoke_model(modelId=model_id, body=request)
    except (ClientError, Exception) as e:
        return json.dumps({"ERROR": f"Can't invoke '{model_id}'. Reason: {str(e)}"})
    model_response = json.loads(response["body"].read())
    response_text = model_response["content"][0]["text"]
    return response_text
