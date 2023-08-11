from flask import Flask, request, jsonify
from flask_restx import Resource, fields, Namespace
from PIL import Image
import numpy as np
import io
import os
import base64
from auth import return_response
from flask_jwt_extended import jwt_required, get_jwt_identity
import cv2  # Import OpenCV for Hough Transform
import uuid
from datetime import datetime


upload_ns = Namespace('upload', description="A namespace for image upload and predictions")

# Define your image upload model
upload_model = upload_ns.model(
    'UploadImage',
    {
        "image": fields.String(required=True)
    }
)

def predict_image(image_np):
    # Apply Hough Transform
    edges = cv2.Canny(image_np, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)

    # Draw lines on the image
    for line in lines:
        rho, theta = line[0]
        a = np.cos(theta)
        b = np.sin(theta)
        x0 = a * rho
        y0 = b * rho
        x1 = int(x0 + 1000 * (-b))
        y1 = int(y0 + 1000 * (a))
        x2 = int(x0 - 1000 * (-b))
        y2 = int(y0 - 1000 * (a))
        cv2.line(image_np, (x1, y1), (x2, y2), (0, 0, 255), 2)

    return image_np

#The uploaded image file is retrieved from the request form data.
#The uploaded image is saved to the user's specific folder within the 'Images' directory.
#The predict_image function is called to apply the Hough Transform on the uploaded image, and the resulting predicted image is saved in the same user folder.
#A response is returned indicating the successful upload and prediction.

@upload_ns.route('/submit')
class ImageSubmit(Resource):

    @jwt_required()
    @upload_ns.expect(upload_model)
    def post(self):
        data = request.form

        image_file = request.files.get('image')  # 'image' should match the field name
        
        if not image_file:
            return return_response("Image not provided", 400)

        image_pil = Image.open(image_file)
        # Convert RGBA to RGB
        if image_pil.mode == 'RGBA':
            image_pil = image_pil.convert('RGB')
            
        current_username = get_jwt_identity()

        images_folder = os.path.join('Images', current_username)

        if not os.path.exists(images_folder):
            os.makedirs(images_folder)

        # Generate unique filenames using UUID
        uploaded_image_filename = f"uploaded_image_{uuid.uuid4()}.jpg"
        uploaded_image_path = os.path.join(images_folder, uploaded_image_filename)
        image_pil.save(uploaded_image_path)

        # Apply Hough Transform to the uploaded image
        uploaded_image_np = np.array(image_pil)
        predicted_image_np = predict_image(uploaded_image_np)

        # Generate unique filenames for predicted images
        predicted_image_filename = f"predicted_image_{uuid.uuid4()}.jpg"
        predicted_image_path = os.path.join(images_folder, predicted_image_filename)
        predicted_image_pil = Image.fromarray(predicted_image_np)
        predicted_image_pil.save(predicted_image_path)
        
        # the below code save the prediceted and uploaded images with the same name so that the previous images are over written
        #by the new images.
        #predicted_image_path = os.path.join(images_folder, 'predicted_image.jpg')
        #predicted_image_pil = Image.fromarray(predicted_image_np)
        #predicted_image_pil.save(predicted_image_path)

        return return_response("Image uploaded and predicted successfully", 200, {}, current_username)

#The get method within the ImagePredict class is decorated with @jwt_required() to ensure the user is authenticated.
#It searches for all predicted image files in the user's folder, sorts them by modification time to get the latest one, and retrieves its content.
#If a predicted image is found, it is encoded in base64 and returned in the response.
#If no predicted image is found, an appropriate response is returned.


@upload_ns.route('/predict')
class ImagePredict(Resource):

    @jwt_required()
    def get(self):
        current_username = get_jwt_identity()
        images_folder = os.path.join('Images', current_username)

        predicted_images = []

        # Find all predicted image files in the user's folder
        for file_name in os.listdir(images_folder):
            if file_name.startswith('predicted_image_') and file_name.endswith('.jpg'):
                predicted_images.append(file_name)

        # Sort predicted image files by modification time (newest first)
        predicted_images.sort(key=lambda x: os.path.getmtime(os.path.join(images_folder, x)), reverse=True)

        if predicted_images:
            latest_predicted_image = predicted_images[0]
            latest_predicted_image_path = os.path.join(images_folder, latest_predicted_image)

            with open(latest_predicted_image_path, 'rb') as f:
                predicted_image_base64 = base64.b64encode(f.read()).decode('utf-8')
                return return_response("Latest predicted image retrieved", 200, {"predicted_image": predicted_image_base64}, current_username)
        else:
            return return_response("Predicted image not found", 404, username=current_username)
