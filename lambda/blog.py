"""
# blog.py
# Author: Adam Campbell
# Date: 23/06/2016
# Edited: N/D        | Miguel Saavedra
#         29/07/2016 | Christopher Treadgold
#         07/08/2016 | Christopher Treadgold
"""

import datetime
import json
import uuid

import boto3
import botocore
from boto3.dynamodb.conditions import Attr, Key

from response import Response
from validator import Validator

class Blog(object):

    def __init__(self, event, context):
        self.event = event
        self.context = context
        self.index_file= "BlogIndex.html"
        with open("constants.json", "r") as constants_file:
            self.constants = json.loads(constants_file.read())
    
    
    def get_blog_data(self):
        """ Gets blog data from dynamoDB """
        try:
            dynamodb = boto3.client("dynamodb")
            blog_data = dynamodb.query(
                TableName=self.constants["BLOG_TABLE"],
                KeyConditionExpression="BlogID = :v1",
                ExpressionAttributeValues={
                    ":v1": {
                        "S": blog_id
                    }
                }
            )
            response = Response("Success", blog_data)
        except botocore.exceptions.ClientError as e:
            print e.response["Error"]["Code"]
            response = Response("Error", None)
            response.errorMessage = "Unable to get blog data: %s" % e.response["Error"]["Code"]
            return response.to_JSON()

        response = Response("Success", blogData)
        # response.setData = blogData
        return response.to_JSON()


    def get_all_blogs(self):
        # Attempt to get all data from table
        try:
            dynamodb = boto3.client("dynamodb")
            data = dynamodb.scan(TableName=self.constants["BLOG_TABLE"],
                                 ConsistentRead=True)
        except botocore.exceptions.ClientError as e:
            print e.response["Error"]["Code"]
            response = Response("Error", None)
            response.errorMessage = "Unable to get blog data: %s" % e.response["Error"]["Code"]
            return response.to_JSON()
        
        response = Response("Success", data)
        # response.setData = data
        return response.format("All Blogs")


    def save_new_blog(self):
        # Get new blog params
        blogID = str(uuid.uuid4())
        author = self.event["blog"]["author"]
        title = self.event["blog"]["title"]
        content = self.event["blog"]["content"]
        metaDescription = self.event["blog"]["metaDescription"]
        metaKeywords = self.event["blog"]["metaKeywords"]
        saveDate = str(datetime.datetime.now())

        if not Validator.validateBlog(content):
            response = Response("Error", None)
            response.errorMessage = "Invalid blog content"
            
            return response.to_JSON()

        blog_params = {
            "BlogID": {"S": blogID},
            "Author": {"S": author},
            "Title": {"S": title},
            "Content": {"S": content},
            "SavedDate": {"S": saveDate},
            "MetaDescription": {"S": metaDescription},
            "MetaKeywords": {"S": metaKeywords},
        }

        try:
            dynamodb = boto3.client("dynamodb")
            dynamodb.put_item(TableName=self.constants["BLOG_TABLE"],
                              Item=blog_params, ReturnConsumedCapacity="TOTAL")
            self.put_blog_object(blog_id, author, title, content, saved_date,
                         meta_description, meta_keywords)
        except botocore.exceptions.ClientError as e:
            print e.response["Error"]["Code"]
            
            response = Response("Error", None)
            response.errorMessage = "Unable to save new blog: %s" % e.response["Error"]["Code"]

            if e.response["Error"]["Code"] == "NoSuchKey":
                self.update_index(blogID, title)
                self.save_new_blog()
            else:
                return response.to_JSON()

        self.put_blog_object(blogID, author, title, content, saveDate,
                metaDescription, metaKeywords)
        return Response("Success", None).to_JSON()


    def edit_blog(self):
        blogID = self.event["blog"]["blogID"]
        author = self.event["blog"]["author"]
        content = self.event["blog"]["content"]
        title = self.event["blog"]["title"]
        meta_description = self.event["blog"]["metaDescription"]
        meta_keywords = self.event["blog"]["metaKeywords"]

        if not Validator.validateBlog(content):
            response = Response("Error", None)
            response.errorMessage = "Invalid blog content"
            return response.to_JSON()

        try:
            dynamodb  = boto3.client("dynamodb")
            blog_post = dynamodb.query(
                TableName=self.constants["BLOG_TABLE"],
                KeyConditionExpression="BlogID = :v1",
                ExpressionAttributeValues={
                    ":v1": {
                        "S": blog_id
                    }
                }
            )
            saved_date = blog_post["Items"][0]["SavedDate"]
            
            dynamodb.update_item(
                TableName=self.constants["BLOG_TABLE"],
                Key={"BlogID": blog_id, "Author": author},
                UpdateExpression=(
                    "set Title=:t Content=:c SavedDate=:s "
                    "MetaDescription=:d MetaKeywords=:k"
                ),
                ExpressionAttributeValues={
                    ":t": title, ":c": content, ":s": saved_date,
                    ":d": meta_description, ":k": meta_keywords
                }
            )
        except botocore.exceptions.ClientError as e:
            print e.response["Error"]["Code"]
            if e.response["Error"]["Code"] == "NoSuchKey":
                self.create_new_index()
                self.save_new_blog()
            else:
                response = Response("Error", None)
                response.errorMessage = "Unable to save edited blog: %s" % (
                    e.response["Error"]["Code"])
                return response.to_JSON()

    self.put_blog_object(blogID, author, title, content, saved_date,
                         meta_description, meta_keywords)
                         
    return Response("Success", None).to_JSON()


    def delete_blog(self):
        blogID = self.event["blog"]["blogID"]
        author = self.event["blog"]["author"]
        
        try:
            dynamodb = boto3.client("dynamodb")
            dynamodb.delete_item(
                TableName=self.constants["BLOG_TABLE"],
                Key={"BlogID": blog_id, "Author" : author}
            )
        except botocore.exceptions.ClientError as e:
            print e.response["Error"]["Code"]
            response = Response("Error", None)
        response.errorMessage = "Unable to delete blog: %s" % e.response["Error"]["Code"]
        return response.to_JSON()

        return Response("Success", None).to_JSON()


    def update_index(self, blog_id, title):
        """ Updates the index of blogs in the s3 bucket """
        try:
            dynamodb = boto3.client("dynamodb")
            s3 = boto3.client("s3")
            
            data = dynamodb.scan(TableName=self.constants["BLOG_TABLE"],
                                 ConsistentRead=True)
            blog_prefix = "https://s3.amazonaws.com/%s/blog" % (
                self.constants["BUCKET"])
            index_links = (
                "<html>"
                    "<head><title>Blog Index</title></head>"
                        "<body>"
                            "<h1>Index</h1>"
            )
            for item in data["Items"]:
                blog_id = item["BlogID"]["S"]
                blog_title = item["Title"]["S"]
                index_links += (
                    "<br><a href=\"%s%s\">%s</a>" % (
                        blog_prefix, blog_id, blog_title)
                )
            index_links = "%s</body></html>" % (index_links)
            
            put_index_item_kwargs = {
                "Bucket": self.constants["BUCKET"], "ACL": "public-read",
                "Body": indexContent, "Key": self.index_file,
                "ContentType": "text/html"
            }
            print index_links
            
            s3.put_object(**put_index_item_kwargs)
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            print error_code
            
            response = Response("Error", None)
            response.errorMessage = "Unable to update index: %s" % (
                error_code)
            return response.to_JSON()
        
        return Response("Success", None).to_JSON()


    def put_blog_object(self, blogID, author, title, content, saveDate,
                        mDescription, mKeywords):
        blog_key = "blog" + blogID
        blog_body = (
            "<head>"
                "<title>%s</title>"
                "<meta name=description content=%s>"
                "<meta name=keywords content=%s>"
                "<meta http-equiv=content-type content=text/html;charset=UTF-8>"
            "</head>"
            "<p>"
                "%s<br>"
                "%s<br>"
                "%s<br>"
                "%s"
            "</p>"
        ) % (title, meta_description, meta_keywords, author, title, content,
             saved_date)
        blog_key = "blog%s" % (blog_id)
        self.update_index(blogID, title)
        
        put_blog_item_kwargs = {
            "Bucket": self.constants["BUCKET"],
            "ACL": "public-read",
            "Body": "<head> <title>" + title + "</title>" +
            " <meta name="description" content="" + mDescription+ "">"
            + "<meta name="keywords" content="" + mKeywords + "">" +
            "<meta http-equiv="content-type" content="text/html;charset=UTF-8">" +
            "</head><p>" + author + "<br>" + title + "<br>" +
            content + "<br>" + saveDate + "</p>",
            "Key": blog_key
        }

        put_blog_item_kwargs["ContentType"] = "text/html"
        self.s3.put_object(**put_blog_item_kwargs)


    def create_new_index(self):
        print "no index found ... creating Index"
        try:
            put_index_item_kwargs = {
                "Bucket": self.constants["BUCKET"], "ACL": "public-read",
                "Body":"<h1>Index</h1> <br>", "Key": self.index_file
            }
            put_index_item_kwargs["ContentType"] = "text/html"
            self.s3.put_object(**put_index_item_kwargs)
        except botocore.exceptions.ClientError as e:
            print e.response["Error"]["Code"]
            response = Response("Error", None)
            response.errorMessage = "Unable to save new blog: %s" % e.response["Error"]["Code"]
