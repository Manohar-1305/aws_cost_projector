import boto3
import time
import json
from botocore.exceptions import ClientError
from price_api import get_total_cost  # Your custom module

# AWS clients
sns_client = boto3.client('sns', region_name='ap-south-1')
s3_client = boto3.client('s3', region_name='ap-south-1')

# Configurations
topic_name = 'Cost_Estimator_Bot'
email_endpoint = 'tradingcontentdrive@gmail.com'  # Change to your email
s3_bucket = 'invoicegeneratorbucket'  # Change to your bucket name
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
    <title>AWS Daily Cost Report</title>
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
        <h1>AWS Daily Cost Report</h1>

        <div class="section">
            <h2>EC2</h2>
            <div class="cost-item"><span class="label">Hourly:</span><span class="value">${costs['ec2_hourly']:.3f}</span></div>
            <div class="cost-item"><span class="label">Monthly:</span><span class="value">${costs['ec2_monthly']:.2f}</span></div>
        </div>

        <div class="section">
            <h2>S3</h2>
            <div class="cost-item"><span class="label">Size:</span><span class="value">{costs['s3_size']:.5f} GB</span></div>
            <div class="cost-item"><span class="label">Monthly:</span><span class="value">${costs['s3_monthly']:.2f}</span></div>
        </div>

        <div class="section">
            <h2>RDS</h2>
            <div class="cost-item"><span class="label">Hourly:</span><span class="value">${costs['rds_hourly']:.2f}</span></div>
            <div class="cost-item"><span class="label">Monthly:</span><span class="value">${costs['rds_monthly']:.2f}</span></div>
        </div>

        <div class="section total">
            <div class="cost-item"><span class="label">Total Hourly:</span><span class="value">${costs['total_hourly']:.2f}</span></div>
            <div class="cost-item"><span class="label">Total Monthly:</span><span class="value">${costs['total_monthly']:.2f}</span></div>
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
            ExtraArgs={'ACL': 'bucket-owner-full-control'}  # Might cause AccessControlListNotSupported error if bucket ACLs are disabled
        )
        print(f"HTML report uploaded to s3://{s3_bucket}/{s3_key}")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessControlListNotSupported':
            print(f"Failed to upload HTML to S3 with ACL. Trying without ACL...")
            try:
                s3_client.upload_file(
                    Filename=local_html_file,
                    Bucket=s3_bucket,
                    Key=s3_key
                )
                print(f"HTML report uploaded to s3://{s3_bucket}/{s3_key} (without ACL)")
                return True
            except Exception as ex:
                print(f"Failed to upload without ACL as well: {ex}")
                return False
        else:
            print(f"Failed to upload HTML to S3: {e}")
            return False
    except Exception as e:
        print(f"Unexpected error during S3 upload: {e}")
        return False


def publish_sns_html(topic_arn, download_link=None):
    # Option 2 message description with download link if available
    if download_link:
        message_body = f"""
AWS Cost Explorer Report Update:

Your daily AWS cost report has been generated and is available at the following link.
This report includes EC2, S3, RDS costs, and a total summary for your account.

Click below to view the full report:
{download_link}
"""
    else:
        message_body = """
AWS Cost Explorer Report Update:

Your daily AWS cost report has been generated.
However, the report upload failed and the download link is unavailable.
"""

    sns_client.publish(
        TopicArn=topic_arn,
        Message=message_body,
        Subject="AWS Daily Cost Report"
    )
    print("Email with report link sent via SNS.")


def main():
    topic_arn = create_sns_topic_and_subscribe()

    # Get costs from your custom module
    costs = get_total_cost()

    print("\n=== AWS Daily Cost Report Preview ===")
    print(f"EC2 Hourly Cost: ${costs['ec2_hourly']:.3f}")
    print(f"EC2 Monthly Cost: ${costs['ec2_monthly']:.2f}")
    print(f"S3 Total Size (GB): {costs['s3_size']:.5f}")
    print(f"S3 Monthly Cost: ${costs['s3_monthly']:.2f}")
    print(f"RDS Hourly Cost: ${costs['rds_hourly']:.2f}")
    print(f"RDS Monthly Cost: ${costs['rds_monthly']:.2f}")
    print(f"Total Hourly Cost: ${costs['total_hourly']:.2f}")
    print(f"Total Monthly Cost: ${costs['total_monthly']:.2f}")
    print("=== End of Report ===\n")

    # Generate HTML
    html_report = generate_html_report(costs)

    # Save locally
    with open(local_html_file, "w") as f:
        f.write(html_report)
    print(f"HTML report saved locally as '{local_html_file}'")

    # Upload to S3
    upload_success = upload_html_to_s3()

    download_link = None
    if upload_success:
        download_link = f"https://{s3_bucket}.s3.ap-south-1.amazonaws.com/{s3_key}"
    else:
        print("Skipping download link in email due to upload failure.")

    # Send SNS email with description and link (if any)
    publish_sns_html(topic_arn, download_link)


if __name__ == "__main__":
    main()
