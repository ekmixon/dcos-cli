#!/usr/bin/env python3

import os
import pathlib
import sys

import boto3
import requests


if os.environ.get("TAG_NAME"):
    version =  os.environ.get("TAG_NAME")

    artifacts = [
        ("linux/dcos", "cli/releases/binaries/dcos/linux/x86-64/latest/dcos"),
        (
            "darwin/dcos",
            "cli/releases/binaries/dcos/darwin/x86-64/latest/dcos",
        ),
        (
            "darwin/dcos.zip",
            "cli/releases/binaries/dcos/darwin/x86-64/latest/dcos.zip",
        ),
        (
            "windows/dcos.exe",
            "cli/releases/binaries/dcos/windows/x86-64/latest/dcos.exe",
        ),
        (
            "linux/dcos",
            f"cli/releases/binaries/dcos/linux/x86-64/{version}/dcos",
        ),
        (
            "darwin/dcos",
            f"cli/releases/binaries/dcos/darwin/x86-64/{version}/dcos",
        ),
        (
            "darwin/dcos.zip",
            f"cli/releases/binaries/dcos/darwin/x86-64/{version}/dcos.zip",
        ),
        (
            "windows/dcos.exe",
            f"cli/releases/binaries/dcos/windows/x86-64/{version}/dcos.exe",
        ),
        ("linux/dcos", "binaries/cli/linux/x86-64/latest/dcos"),
        ("darwin/dcos", "binaries/cli/darwin/x86-64/latest/dcos"),
        ("darwin/dcos.zip", "binaries/cli/darwin/x86-64/latest/dcos.zip"),
        ("windows/dcos.exe", "binaries/cli/windows/x86-64/latest/dcos.exe"),
        ("linux/dcos", f"binaries/cli/linux/x86-64/{version}/dcos"),
        ("darwin/dcos", f"binaries/cli/darwin/x86-64/{version}/dcos"),
        ("darwin/dcos.zip", f"binaries/cli/darwin/x86-64/{version}/dcos.zip"),
        (
            "windows/dcos.exe",
            f"binaries/cli/windows/x86-64/{version}/dcos.exe",
        ),
    ]

else:
    version = os.environ.get("BRANCH_NAME")

    artifacts = [
        (
            "linux/dcos",
            f"cli/testing/binaries/dcos/linux/x86-64/{version}/dcos",
        ),
        (
            "darwin/dcos",
            f"cli/testing/binaries/dcos/darwin/x86-64/{version}/dcos",
        ),
        (
            "darwin/dcos.zip",
            f"cli/testing/binaries/dcos/darwin/x86-64/{version}/dcos.zip",
        ),
        (
            "windows/dcos.exe",
            f"cli/testing/binaries/dcos/windows/x86-64/{version}/dcos.exe",
        ),
    ]


s3_client = boto3.resource('s3', region_name='us-west-2').meta.client
bucket = "downloads.dcos.io"

# TODO: this should probably passed as argument.
build_path = f"{os.path.dirname(os.path.realpath(__file__))}/../build"

for f, bucket_key in artifacts:
    s3_client.upload_file(f"{build_path}/{f}", bucket, bucket_key)

slack_token = os.environ.get("SLACK_API_TOKEN")
if not slack_token or not os.environ.get("TAG_NAME"):
    sys.exit(0)

attachment_text = f"The DC/OS CLI {version} has been released!"
s3_urls = [f"https://{bucket}/{a[1]}" for a in artifacts]

try:
    resp = requests.post(
        f"https://mesosphere.slack.com/services/hooks/jenkins-ci?token={slack_token}",
        json={
            "channel": "#dcos-cli-ci",
            "color": "good",
            "attachments": [
                {
                    "color": "good",
                    "title": "dcos-cli",
                    "text": "\n".join(
                        [f"{attachment_text} :rocket:"] + s3_urls
                    ),
                    "fallback": f"[dcos-cli] {attachment_text}",
                }
            ],
        },
        timeout=30,
    )


    if resp.status_code != 200:
        raise Exception(f"received {resp.status_code} status response: {resp.text}")
except Exception as e:
    print(f"Couldn't post Slack notification:\n  {e}")
