import json
import boto3
import time
from botocore.exceptions import ClientError
from price_api import get_total_cost  # Your cost fetching function

# AWS clients
sns_client = boto3.client('sns', region_name='ap-south-1')
s3_client = boto3.client('s3', region_name='ap-south-1')

# Configuration
topic_name = 'Cost_Estimator_Bot'
email_endpoint = 'tradingcontentdrive@gmail.com'  # Replace with your email
s3_bucket = 'invoicegeneratorbucket'              # Replace with your bucket name
s3_key = 'reports/aws_daily_cost_report.html'
local_html_file = 'aws_daily_cost_report.html'


def create_sns_topic_and_subscribe():
    response = sns_client.create_topic(Name=topic_name)
    topic_arn = response['TopicArn']

    sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol='email',
        Endpoint=email_endpoint
    )
    print(f"\nSubscription request sent to {email_endpoint}. Please check your email to confirm.")

    # Wait for subscription confirmation
    while True:
        subs = sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
        subscription_arn = subs['Subscriptions'][0]['SubscriptionArn']
        if subscription_arn != 'PendingConfirmation':
            print("\nSubscription Confirmed")
            break
        else:
            print("\nWaiting for subscription confirmation...")
            time.sleep(5)

    return topic_arn

def generate_html_report(costs):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AWS Monthly Cost Estimation Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(120deg, #a1c4fd, #c2e9fb);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .report-container {{
            background: #fff;
            width: 90%;
            max-width: 700px;
            border-radius: 16px;
            padding: 30px 40px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            animation: fadeIn 1s ease;
        }}
        h1 {{
            font-size: 2.5rem;
            text-align: center;
            margin-bottom: 30px;
            background: linear-gradient(90deg, #ff7eb3, #ff758c, #ff7eb3);
            background-size: 200% auto;
            color: transparent;
            background-clip: text;
            -webkit-background-clip: text;
            animation: shimmer 4s linear infinite;
            white-space: nowrap;
        }}
        .section {{
            margin-bottom: 25px;
            background: linear-gradient(135deg, #fdfbfb, #ebedee);
            border-left: 6px solid #6366f1;
            padding: 20px;
            border-radius: 10px;
        }}
        .section h2 {{
            font-size: 1.4rem;
            color: #4f46e5;
            margin-bottom: 15px;
        }}
        .cost-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            font-size: 1.1rem;
            border-bottom: 1px dashed #ccc;
        }}
        .cost-item:last-child {{
            border-bottom: none;
        }}
        .label {{
            font-weight: 600;
            color: #1e293b;
        }}
        .value {{
            font-weight: 700;
            color: #dc2626;
        }}
        .total {{
            background: #fef08a;
            border: 2px dashed #facc15;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .total .label {{
            color: #92400e;
        }}
        .total .value {{
            color: #b45309;
        }}
        @keyframes shimmer {{
            0% {{ background-position: 0% center; }}
            100% {{ background-position: 200% center; }}
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @media (max-width: 620px) {{
            h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
    </head>
    <body>
    <div class="report-container">
        <h1>AWS Monthly Cost Estimator Report</h1>

        <div class="section">
            <h2>EC2</h2>
            <div class="cost-item"><span class="label">Hourly:</span><span class="value">${costs.get('ec2_hourly', 0.0):.3f}</span></div>
            <div class="cost-item"><span class="label">Monthly:</span><span class="value">${costs.get('ec2_monthly', 0.0):.2f}</span></div>
        </div>

        <div class="section">
            <h2>S3</h2>
            <div class="cost-item"><span class="label">Size:</span><span class="value">{costs.get('s3_size', 0.0):.5f} GB</span></div>
            <div class="cost-item"><span class="label">Monthly:</span><span class="value">${costs.get('s3_monthly', 0.0):.2f}</span></div>
        </div>

        <div class="section">
            <h2>RDS</h2>
            <div class="cost-item"><span class="label">Hourly:</span><span class="value">${costs.get('rds_hourly', 0.0):.2f}</span></div>
            <div class="cost-item"><span class="label">Monthly:</span><span class="value">${costs.get('rds_monthly', 0.0):.2f}</span></div>
        </div>

        <div class="section">
            <h2>EBS</h2>
            <div class="cost-item"><span class="label">Monthly:</span><span class="value">${costs.get('ebs_monthly', 0.0):.2f}</span></div>
        </div>

        <div class="section">
            <h2>Route 53</h2>
            <div class="cost-item"><span class="label">Monthly:</span><span class="value">${costs.get('route53_monthly', 0.0):.2f}</span></div>
        </div>

        <div class="section total">
            <div class="cost-item"><span class="label">Total Hourly:</span><span class="value">${costs.get('total_hourly', 0.0):.2f}</span></div>
            <div class="cost-item"><span class="label">Total Monthly:</span><span class="value">${costs.get('total_monthly', 0.0):.2f}</span></div>
        </div>
    </div>
    </body>
    </html>
    """
    return html_content


def upload_html_to_s3():
    try:
        s3_client.upload_file(
            Filename=local_html_file,
            Bucket=s3_bucket,
            Key=s3_key,
            ExtraArgs={'ACL': 'bucket-owner-full-control', 'ContentType': 'text/html'}
        )
        print(f"HTML report uploaded to s3://{s3_bucket}/{s3_key}")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessControlListNotSupported':
            print(f"Failed to upload HTML with ACL. Trying without ACL...")
            try:
                s3_client.upload_file(
                    Filename=local_html_file,
                    Bucket=s3_bucket,
                    Key=s3_key,
                    ExtraArgs={'ContentType': 'text/html'}
                )
                print(f"HTML report uploaded to s3://{s3_bucket}/{s3_key} (without ACL)")
                return True
            except Exception as ex:
                print(f"Failed without ACL as well: {ex}")
                return False
        else:
            print(f"Failed to upload HTML: {e}")
            return False
    except Exception as e:
        print(f"Unexpected error during S3 upload: {e}")
        return False


def generate_presigned_url(download=False):
    params = {'Bucket': s3_bucket, 'Key': s3_key}
    if download:
        # Force download by setting Content-Disposition header
        params['ResponseContentDisposition'] = 'attachment; filename="AWS_Daily_Cost_Report.html"'
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=3600  # 1 hour expiration
        )
        return url
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return None


def publish_sns_html(topic_arn, url_view, url_download):
    message = (
        f"Hello!\n\n"
        f"Your daily AWS cost report has been generated and is available at the following link"
        f"This report includes EC2, S3, RDS, EBS, and Route 53 costs, along with a total summary for your account."
        f"Your AWS Daily Cost/Monthly Report is ready.\n\n"
        f"View it in your browser:\n{url_view}\n\n"
        f"Download it as HTML file:\n{url_download}\n\n"
        f"Thanks for using AWS Cost Estimator Bot."
    )
    subject = "AWS Cost Report Notification"
    try:
        sns_client.publish(TopicArn=topic_arn, Message=message, Subject=subject)
        print("Notification email sent with report URLs.")
    except Exception as e:
        print(f"Failed to send SNS notification: {e}")


def main():
    topic_arn = create_sns_topic_and_subscribe()

    costs = get_total_cost()  # Your function to fetch cost data

    # Print costs for debug
    print(f"EC2 Hourly: ${costs.get('ec2_hourly', 0.0):.3f}")
    print(f"EC2 Monthly: ${costs.get('ec2_monthly', 0.0):.2f}")
    print(f"S3 Size: {costs.get('s3_size', 0.0):.5f} GB")
    print(f"S3 Monthly: ${costs.get('s3_monthly', 0.0):.2f}")
    print(f"RDS Hourly: ${costs.get('rds_hourly', 0.0):.2f}")
    print(f"RDS Monthly: ${costs.get('rds_monthly', 0.0):.2f}")
    print(f"EBS Monthly: ${costs.get('ebs_monthly', 0.0):.2f}")
    print(f"Route53 Monthly: ${costs.get('route53_monthly', 0.0):.2f}")
    print(f"Total Hourly: ${costs.get('total_hourly', 0.0):.2f}")
    print(f"Total Monthly: ${costs.get('total_monthly', 0.0):.2f}")

    html_report = generate_html_report(costs)

    # Save HTML locally
    with open(local_html_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
    print(f"HTML report saved locally as {local_html_file}")

    # Upload to S3
    if not upload_html_to_s3():
        print("Upload failed, aborting.")
        return

    # Generate presigned URLs
    url_view = generate_presigned_url(download=False)  # For browser viewing
    url_download = generate_presigned_url(download=True)  # For download

    if not url_view or not url_download:
        print("Failed to generate presigned URLs, aborting.")
        return

    # Send SNS notification with URLs
    publish_sns_html(topic_arn, url_view, url_download)

    # Print the view URL so you can open it directly in a browser
    print("\nOpen this link in your browser to view the report:")
    print(url_view)


if __name__ == '__main__':
    main()
