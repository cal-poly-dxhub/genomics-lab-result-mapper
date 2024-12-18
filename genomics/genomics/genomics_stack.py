from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigateway,
    aws_apigatewayv2_integrations as integrations,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_s3_deployment as s3deploy,
    aws_iam as iam,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
import aws_cdk as cdk
from constructs import Construct


class GenomicsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # -------------------- IAM Role--------------------
        lambda_s3_role = iam.Role(
            self, "LambdaS3FullAccessRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="IAM role with full access to S3 for Lambda functions",
        )

        
        # Restrict Lambda to access S3 buckets in the same account
        lambda_s3_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:*"],  # Allow all S3 actions
                resources=[
                    f"arn:aws:s3:::*",
                    f"arn:aws:s3:::*/*"
                ],
                conditions={
                    "StringEquals": {
                        "s3:ResourceAccount": cdk.Aws.ACCOUNT_ID  # Restrict to same account
                    }
                }
            )
        )


        # AmazonBedrockFullAccess
        lambda_s3_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
        )

        # -------------------- genomics-upload-download S3 Bucket --------------------
        primary_bucket = s3.Bucket(
            self, "GenomicsUploadDownloadBucket",
            versioned=True,
            public_read_access=True, 
            block_public_access=s3.BlockPublicAccess.BLOCK_ACLS,
            cors=[
                s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.DELETE,
                        s3.HttpMethods.HEAD
                    ],
                    allowed_origins=["*"],
                    exposed_headers=["ETag"],
                )
            ]
        )

        # Bucket Policy for public read and write
        primary_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AnyPrincipal()],  # public access
                actions=["s3:GetObject", "s3:PutObject"],
                resources=[f"{primary_bucket.bucket_arn}/*"]
            )
        )

        # -------------------- static website S3 Bucket --------------------
        static_site_bucket = s3.Bucket(
            self, "GenomicsStaticWebsiteBucket",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            cors=[
                s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.DELETE,
                        s3.HttpMethods.HEAD
                    ],
                    allowed_origins=["*"],
                    exposed_headers=["ETag"],
                )
            ]
        )

        # static website assets
        s3deploy.BucketDeployment(
            self, "StaticSiteDeployment",
            destination_bucket=static_site_bucket,
            sources=[
                s3deploy.Source.asset("./static-website")  
            ]
        )

        # -------------------- genomics-generate-presigned-url Lambda --------------------
        presignedUrlLambda = _lambda.Function(
            self, "GenomicsApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="lambda_function.handler",
            code=_lambda.Code.from_asset("presignedUrlLambda"),
            role=lambda_s3_role,
            timeout=Duration.seconds(10), 
        )

        # HTTP API Gateway with CORS
        http_api = apigateway.HttpApi(
            self, "GenomicsHttpApi",
            description="HTTP API Gateway to trigger presigned URL Lambda",
            cors_preflight=apigateway.CorsPreflightOptions(
                allow_headers=["*"],
                allow_methods=[
                    apigateway.CorsHttpMethod.GET,
                    apigateway.CorsHttpMethod.PUT,
                    apigateway.CorsHttpMethod.POST,
                    apigateway.CorsHttpMethod.DELETE,
                    apigateway.CorsHttpMethod.HEAD,
                    apigateway.CorsHttpMethod.OPTIONS
                ],
                allow_origins=["*"],
                expose_headers=["ETag"]
            )
        )

        # Integrate Lambda with HTTP API
        lambda_integration = integrations.HttpLambdaIntegration(
            "LambdaIntegration", presignedUrlLambda
        )

        # Add API route
        http_api.add_routes(
            path="/",  # Root path
            methods=[apigateway.HttpMethod.GET],
            integration=lambda_integration
        )

        # -------------------- Second Lambda (S3 Event Triggered) --------------------
        # Create Lambda Layer
        lambda_layer = _lambda.LayerVersion(
            self, "GenomicsLambdaLayer",
            code=_lambda.Code.from_asset("lambda-layer"),  # Folder with layer contents
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13],  # Ensure this runtime is supported
            description="A layer for additional libraries or utilities"
        )

        # Lambda function triggered by S3 event
        genomicsProcessing = _lambda.Function(
            self, "GenomicsS3EventLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,  # Ensure this runtime is supported
            handler="genomicsProcessing.handler",
            code=_lambda.Code.from_asset("genomicsProcessing"),  # Folder for Lambda function
            layers=[lambda_layer],
            environment={
                "BUCKET_NAME": primary_bucket.bucket_name
            },
            role=lambda_s3_role,
            timeout=Duration.seconds(20),  # Set timeout to 20 seconds
        )

        # Add S3 Event Notification for PUT Object
        primary_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(genomicsProcessing)
        )

        # -------------------- Outputs --------------------
        self.add_output("ApiUrl", value=http_api.url)
        self.add_output("PrimaryBucketName", value=primary_bucket.bucket_name)
        self.add_output("PrimaryBucketURL", value=f"https://{primary_bucket.bucket_name}.s3.amazonaws.com/")
        self.add_output("StaticWebsiteURL", value=static_site_bucket.bucket_website_url)

    def add_output(self, name: str, value: str) -> None:
        CfnOutput(self, name, value=value)
