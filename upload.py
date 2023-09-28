from flask import Flask, request, jsonify, send_file
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
import time


upload_ns = Namespace('upload', description="A namespace for image upload and predictions")

# Define your image upload model
upload_model = upload_ns.model(
    'UploadImage',
    {
        "image": fields.Raw(required=False),
        "uploaded" : fields.String(required = False),
        "enhanced" : fields.String(required = False),
    }
)

def predict_image(image_np, name):
    os.system("source SRModel/bin/activate")
    os.system(f"python SRModel/Real-ESRGAN/inference_realesrgan.py -n RealESRGAN_x4plus -i {image_np} -o Images/{name}/")

    while not os.path.exists(image_np.split('.')[0] + '_out.jpg'):
        time.sleep(2)

#The uploaded image file is retrieved from the request form data.
#The uploaded image is saved to the user's specific folder within the 'Images' directory.
#The predict_image function is called to apply the Hough Transform on the uploaded image, and the resulting predicted image is saved in the same user folder.
#A response is returned indicating the successful upload and prediction.

@upload_ns.route('/submit')
class ImageSubmit(Resource):
    @jwt_required()
    @upload_ns.expect(upload_model)
    def post(self):
        image_file = request.files['image']  # 'image' should match the field name
        
        current_username = get_jwt_identity()

        print(type(image_file))
        
        if not image_file:
            return return_response("Image not provided", 400)

        image_pil = Image.open(image_file)
        # Convert RGBA to RGB
        if image_pil.mode == 'RGBA':
            image_pil = image_pil.convert('RGB')

        images_folder = os.path.join('Images', current_username)

        if not os.path.exists(images_folder):
            os.makedirs(images_folder)

        # Generate unique filenames using UUID
        random = uuid.uuid4()
        uploaded_image_filename = f"uploaded_image_{random}.jpg"
        if '-' in uploaded_image_filename:
        	fn = uploaded_image_filename.split('-')
        	
        	uploaded_image_filename = ('').join(fn)
        	
        uploaded_image_path = os.path.join(images_folder, uploaded_image_filename)
        image_pil.save(uploaded_image_path)
        print("SAVED IMAGE")
        # Apply Hough Transform to the uploaded image
        uploaded_image_np = np.array(image_pil)
        predict_image(uploaded_image_path, current_username)

        # Generate unique filenames for predicted images
        if os.path.exists(uploaded_image_path.split('.')[0] + '_out.jpg'):
            print("Hurrayyyyy")
            os.rename(uploaded_image_path.split('.')[0] + '_out.jpg', os.path.join(images_folder, f"predicted_image_{random}.jpg"))

        print("SAVED PREDICTED")

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
                print("FOUND IT SENDING NOWW!")
                predicted_image_base64 = base64.b64encode(f.read()).decode('utf-8')
                return send_file(latest_predicted_image_path, as_attachment=True)
                #return return_response("Latest predicted image retrieved", 200, {"predicted_image": predicted_image_base64}, current_username)
        else:
            return return_response("Predicted image not found", 404, username=current_username)
            
@upload_ns.route('/image')
class ImageCompare(Resource):

    @jwt_required()
    def get(self):
        current_username = get_jwt_identity()
        images_folder = os.path.join('Images', current_username)

        uploaded_images = []

        # Find all predicted image files in the user's folder
        for file_name in os.listdir(images_folder):
            if file_name.startswith('uploaded_image_') and file_name.endswith('.jpg'):
                uploaded_images.append(file_name)

        # Sort predicted image files by modification time (newest first)
        uploaded_images.sort(key=lambda x: os.path.getmtime(os.path.join(images_folder, x)), reverse=True)

        if uploaded_images:
            latest_uploaded_image = uploaded_images[0]
            latest_uploaded_image_path = os.path.join(images_folder, latest_uploaded_image)

            with open(latest_uploaded_image_path, 'rb') as f:
                print("FOUND IT SENDING NOWW!")
                uploaded_image_base64 = base64.b64encode(f.read()).decode('utf-8')
                return send_file(latest_uploaded_image_path, as_attachment=True)
                #return return_response("Latest predicted image retrieved", 200, {"predicted_image": predicted_image_base64}, current_username)
        else:
            return return_response("Uploaded image not found", 404, username=current_username)
