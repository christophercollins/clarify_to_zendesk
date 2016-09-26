#!/usr/bin/python
# Script:		ClarifyToZendesk.py
# Author:		Christopher Collins (christophercollins@livenation.com)
# Last Change:	2015-11-03
#
# Description: Converts a Clarify generated Markdown file to a JSON file which can be submitted to the Zendesk API
# All articles are uploaded marked as drafts

from __future__ import print_function
import requests
import markdown
import os
import sys
import json
import argparse

# CHANGE THESE GLOBAL VARIABLES
ZENDESK_URL = ''  # 'https://example.zendesk.com'
API_USER = ''  # 'user@domain.com/token'
API_PASS = ''  # '<token string from admin interface>'
ARTICLE_SECTION = ''  # Article section in Zendesk to upload to


def check_file_exists(file):
    if os.path.exists(file):
        return
    else:
        print("File {} does not exist! Exiting!".format(os.path.basename(file)))
        sys.exit(1)


def get_images(dir):
    image_dict = {}  # Get dict of images responses from the server after posting to get id, url, etc.
    for f in os.listdir(dir):
        if os.path.splitext(f)[1] in ['.png', '.jpg', '.jpeg', '.tif', '.gif']:
            print("Uploading image attachment: {}".format(f))
            image_dict[f] = upload_images(os.path.join(dir, f))
    return image_dict


def upload_images(file):
    url = ZENDESK_URL + '/api/v2/help_center/articles/attachments.json'
    r = requests.post(url=url, auth=(API_USER, API_PASS), data={'inline':'true'}, files={'file': open(file, 'rb')})
    if r.status_code == 201:
        return json.loads(r.text)
    else:
        print('There was some kind of an error uploading images to Zendesk.\nExiting.')
        sys.exit(1)


def replace_markdown_urls(image_dict, markdown_file, image_path):
    print("Opening markdown file: {}".format(markdown_file))
    md = open(markdown_file).read()
    print("Replacing image links in markdown file to prep for upload")
    for image in image_dict:
        image_name = image_dict[image]['article_attachment']['file_name']
        image_url = image_dict[image]['article_attachment']['content_url']
        md = md.replace('images/' + image_path + '/' + image_name, image_url)
    return md


def generate_html_payload(markdown_data):
    print("Converting markdown to HTML for JSON payload")
    html = markdown.markdown(markdown_data)
    return html


def generate_article_dictionary(html, title):
    print("Generating rest of article JSON payload")
    payload = {"article": {"draft": True, "locale": "en-us", "title": title, "body": html}}
    return payload


def post_article(post_payload):
    url = ZENDESK_URL + '/api/v2/help_center/sections/' + ARTICLE_SECTION + '/articles.json'
    r = requests.post(url=url, auth=(API_USER, API_PASS), json=post_payload)
    print("Posting article to Zendesk")
    if r.status_code == 201:
        return json.loads(r.text)
    else:
        print('There was some kind of an error posting article to Zendesk.\nExiting.')
        sys.exit(1)


def associate_attachments(article_id, image_dict):
    url = ZENDESK_URL + '/api/v2/help_center/articles/' + str(article_id) + '/bulk_attachments.json'
    image_id_list = []
    for image in image_dict:
        image_id_list.append(image_dict[image]['article_attachment']['id'])
    print("Associating image attachments with article")

    if len(image_id_list) > 20:
        start_count = 0
        end_count = 20
        temp_list = image_id_list[start_count:end_count]
        while temp_list:
            payload = {'attachment_ids': temp_list}
            r = requests.post(url=url, auth=(API_USER, API_PASS), json=payload)
            start_count += 20
            end_count += 20
            temp_list = image_id_list[start_count:end_count]
    else:
        payload = {'attachment_ids': image_id_list}
        r = requests.post(url=url, auth=(API_USER, API_PASS), json=payload)


def main():

    parser = argparse.ArgumentParser(description='This script takes the output of Clarify and posts to Zendesk.')

    parser.add_argument('--mdfile', help='Supply markdown input file.', required=False)
    parser.add_argument('--title', help='The title of the article as you want it to appear in Zendesk', required=True)

    args = parser.parse_args()

    md_path = os.path.realpath(args.mdfile)
    check_file_exists(md_path)
    start_file = os.path.basename(args.mdfile)
    start_dir = os.path.dirname(args.mdfile)
    images_dir = start_dir + '/images/' + os.path.splitext(start_file)[0]
    article_title = args.title
    image_dict = get_images(images_dir)
    md = replace_markdown_urls(image_dict, args.mdfile, os.path.splitext(start_file)[0])
    html = generate_html_payload(md)
    post_payload = generate_article_dictionary(html, article_title)
    article_post_response = post_article(post_payload)
    article_id = article_post_response['article']['id']
    associate_attachments(article_id, image_dict)
    print("The article URL is: {}".format(ZENDESK_URL + "/hc/en-us/articles/" + str(article_id)))
    print("Upload of article to Zendesk is completed, dude")


if __name__ == '__main__':
    main()
