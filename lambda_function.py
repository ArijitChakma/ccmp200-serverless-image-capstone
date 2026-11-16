import os
from io import BytesIO

import boto3
from PIL import Image, ImageOps, UnidentifiedImageError

s3 = boto3.client("s3")

CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
}


def lambda_handler(event, context):
    bucket = event.get("bucket")
    key = event.get("key")

    if bucket != os.environ["INPUT_BUCKET"] or not isinstance(key, str) or not key:
        return {"success": False, "message": "Provide an image key from the originals bucket."}

    output_bucket = os.environ["OUTPUT_BUCKET"]
    output_key = f"thumbnails/{key}"

    try:
        response = s3.get_object(Bucket=bucket, Key=key)
    except s3.exceptions.NoSuchKey:
        return {"success": False, "message": f"Image not found: {key}"}

    with response["Body"] as body:
        original = BytesIO(body.read())

    with BytesIO() as resized:
        try:
            with Image.open(original) as image:
                image_format = image.format
                if image_format not in CONTENT_TYPES:
                    return {"success": False, "message": "Use a JPEG or PNG image."}

                ImageOps.exif_transpose(image, in_place=True)
                image.thumbnail((200, 200))
                image.save(resized, format=image_format)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            return {"success": False, "message": "The image could not be processed."}

        resized.seek(0)
        s3.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=resized,
            ContentType=CONTENT_TYPES[image_format],
        )

    return {
        "success": True,
        "outputBucket": output_bucket,
        "outputKey": output_key,
    }
