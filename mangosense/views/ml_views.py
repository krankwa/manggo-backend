from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from PIL import Image
import numpy as np
import os
import gc
import json
import time
from ..models import MangoImage, MLModel, PredictionLog, Notification
from .utils import (
    get_client_ip, validate_image_file, get_disease_type,
    calculate_confidence_level, get_prediction_summary,
    log_prediction_activity, 
    create_api_response
)

import tensorflow as tf

# ML Configuration
IMG_SIZE = (224, 224)

# Separate class names for each model type (IMPROVED ORGANIZATION)
LEAF_CLASS_NAMES = [
    'Anthracnose','Die Back', 'Healthy','Powdery Mildew','Sooty Mold',
]

FRUIT_CLASS_NAMES = [
    'Anthracnose', 'Black Mold Rot', 'Healthy', 'Stem End Rot'
]

# Keep backward compatibility with old class_names (for any legacy code)
# class_names = LEAF_CLASS_NAMES + ['Black Mold Rot', 'Stem End Rot']

# Treatment suggestions (complete list)
treatment_suggestions = {
    'Anthracnose': 'The diseased twigs should be pruned and burnt along with fallen leaves. Spraying twice with Carbendazim (Bavistin 0.1%) at 15 days interval during flowering controls blossom infection.',
    'Bacterial Canker': 'Three sprays of Streptocycline (0.01%) or Agrimycin-100 (0.01%) after first visual symptom at 10 day intervals are effective in controlling the disease.',
    'Cutting Weevil': 'Use recommended insecticides and remove infested plant material.',
    'Die Back': 'Pruning of the diseased twigs 2-3 inches below the affected portion and spraying Copper Oxychloride (0.3%) on infected trees controls the disease.',
    'Gall Midge': 'Remove and destroy infested fruits; use appropriate insecticides.',
    'Healthy': 'No treatment needed. Maintain good agricultural practices.',
    'Powdery Mildew': 'Alternate spraying of Wettable sulphur 0.2 per cent at 15 days interval are recommended for effective control of the disease.',
    'Sooty Mold': 'Pruning of affected branches and their prompt destruction followed by spraying of Wettasulf (0.2%) helps to control the disease.',
    'Black Mold Rot': 'Improve air circulation and apply fungicides as needed.',
    'Stem End Rot': 'Proper post-harvest handling and storage conditions are essential.'
}

def get_treatment_for_disease(disease_name):
    """
    Get treatment suggestion for a disease with better error handling and debugging
    """
    if not disease_name:
        return "No treatment information available - disease name is empty."
    
    # Direct lookup first
    treatment = treatment_suggestions.get(disease_name)
    if treatment:
        return treatment
    
    # Try case-insensitive lookup
    disease_lower = disease_name.lower()
    for key, value in treatment_suggestions.items():
        if key.lower() == disease_lower:
            return value
    
    # Try partial match (for cases like 'Die Back' vs 'Die_Back')
    disease_normalized = disease_name.replace('_', ' ').replace('-', ' ').strip()
    for key, value in treatment_suggestions.items():
        key_normalized = key.replace('_', ' ').replace('-', ' ').strip()
        if disease_normalized.lower() == key_normalized.lower():
            return value
    
    # Log available keys for debugging
    available_keys = list(treatment_suggestions.keys())
    
    return f"No treatment information available for '{disease_name}'. Please consult with an agricultural expert."

# Model paths
LEAF_MODEL_PATH = os.path.join(settings.BASE_DIR, 'models', 'leaf-resnet101.keras')
FRUIT_MODEL_PATH = os.path.join(settings.BASE_DIR, 'models', 'fruit-resnet101.keras')


def preprocess_image(image_file):
    """Preprocess image for ML model prediction"""
    try:
        img = Image.open(image_file).convert('RGB')
        original_size = img.size
        img = img.resize(IMG_SIZE)
        img_array = np.array(img)
        
        # CRITICAL FIX: Apply EfficientNet preprocessing then add batch dimension
        img_array = tf.keras.applications.efficientnet.preprocess_input(img_array)
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array, original_size
    except Exception as e:
        raise e


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def predict_image(request):
    """Handle image prediction from mobile Ionic app"""
    import time
    start_time = time.time()
    
    # Add debug logging
    
    if 'image' not in request.FILES:
        return JsonResponse(
            create_api_response(
                success=False,
                message='No image uploaded',
                errors=['Image file is required']
            ),
            status=400
        )

    try:
        image_file = request.FILES['image']
        client_ip = get_client_ip(request)
        
        # Extract location data from request
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        location_accuracy_confirmed = request.data.get('location_accuracy_confirmed', 'false').lower() == 'true'
        location_source = request.data.get('location_source', '')
        location_address = request.data.get('location_address', '')
        
        # Check if this is a preview-only request (no database save)
        preview_only = request.data.get('preview_only', 'false').lower() == 'true'
        
        # Extract user verification data
        is_detection_correct = request.data.get('is_detection_correct', '').lower() == 'true'
        user_feedback = request.data.get('user_feedback', '')
        
        # Extract symptoms data from verification
        try:
            selected_symptoms = json.loads(request.data.get('selected_symptoms', '[]')) if request.data.get('selected_symptoms') else []
        except (json.JSONDecodeError, TypeError):
            selected_symptoms = []
            
        try:
            primary_symptoms = json.loads(request.data.get('primary_symptoms', '[]')) if request.data.get('primary_symptoms') else []
        except (json.JSONDecodeError, TypeError):
            primary_symptoms = []
            
        try:
            alternative_symptoms = json.loads(request.data.get('alternative_symptoms', '[]')) if request.data.get('alternative_symptoms') else []
        except (json.JSONDecodeError, TypeError):
            alternative_symptoms = []
            
        detected_disease = request.data.get('detected_disease', '')
        
        try:
            top_diseases = json.loads(request.data.get('top_diseases', '[]')) if request.data.get('top_diseases') else []
        except (json.JSONDecodeError, TypeError):
            top_diseases = []
            
        try:
            symptoms_data = json.loads(request.data.get('symptoms_data', '{}')) if request.data.get('symptoms_data') else {}
        except (json.JSONDecodeError, TypeError):
            symptoms_data = {}
        
        # Validate image file using utils
        validation_errors = validate_image_file(image_file)
        if validation_errors:
            return JsonResponse(
                create_api_response(
                    success=False,
                    message='Invalid image file',
                    errors=validation_errors
                ),
                status=400
            )

        # Process image for prediction with error handling
        try:
            img_array, original_size = preprocess_image(image_file)
        except Exception as preprocessing_error:
            return JsonResponse(
                create_api_response(
                    success=False,
                    message='Image preprocessing failed',
                    errors=[str(preprocessing_error)]
                ),
                status=500
            )

        # Get prediction type and location data
        detection_type = request.data.get('detection_type', 'leaf')
        
        # Extract location data from request
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        location_accuracy_confirmed = request.data.get('location_accuracy_confirmed', 'false').lower() == 'true'
        location_source = request.data.get('location_source', '')
        location_address = request.data.get('location_address', '')
        
        # Choose model path and class names (IMPROVED LOGIC)
        if detection_type == 'fruit':
            model_path = FRUIT_MODEL_PATH
            model_used = 'fruit'
            model_class_names = FRUIT_CLASS_NAMES
        else:
            model_path = LEAF_MODEL_PATH
            model_used = 'leaf'
            model_class_names = LEAF_CLASS_NAMES


        # Check if model file exists
        if not os.path.exists(model_path):
            return JsonResponse(
                create_api_response(
                    success=False,
                    message=f'Model file not found: {model_used}',
                    errors=[f'Model file {model_path} does not exist']
                ),
                status=500
            )

        # Load the model dynamically with error handling
        try:
            model = tf.keras.models.load_model(model_path)
        except Exception as model_error:
            return JsonResponse(
                create_api_response(
                    success=False,
                    message='Failed to load ML model',
                    errors=[str(model_error)]
                ),
                status=500
            )

        # Real ML prediction with error handling
        try:
            prediction = model.predict(img_array)
            prediction = np.array(prediction).flatten()
        except Exception as prediction_error:
            return JsonResponse(
                create_api_response(
                    success=False,
                    message='ML prediction failed',
                    errors=[str(prediction_error)]
                ),
                status=500
            )

        # Get prediction summary using utils
        prediction_summary = get_prediction_summary(prediction, model_class_names)

        # Set confidence threshold
        CONFIDENCE_THRESHOLD = 20.0

        # Check if top prediction is below threshold
        if prediction_summary['primary_prediction']['confidence'] < CONFIDENCE_THRESHOLD:
            unknown_response = {
                'disease': 'Unknown',
                'confidence': f"{prediction_summary['primary_prediction']['confidence']:.2f}%",
                'confidence_score': prediction_summary['primary_prediction']['confidence'],
                'confidence_level': 'Low',
                'treatment': "The uploaded image could not be confidently classified. Please ensure the image is of a mango leaf or fruit and try again.",
                'detection_type': model_used
            }
            response_data = {
                'primary_prediction': unknown_response,
                'top_3_predictions': [],
                'prediction_summary': {
                    'most_likely': 'Unknown',
                    'confidence_level': 'Low',
                    'total_diseases_checked': len(model_class_names)
                },
                'alternative_symptoms': {
                    'primary_disease': 'Unknown',
                    'primary_disease_symptoms': [],
                    'alternative_diseases': []
                },
                'user_verification': {
                    'selected_symptoms': [],
                    'primary_symptoms': [],
                    'alternative_symptoms': [],
                    'detected_disease': 'Unknown',
                    'is_detection_correct': False,
                    'user_feedback': ''
                },
                'saved_image_id': None,
                'model_used': model_used,
                'model_path': model_path,
                'debug_info': {
                    'model_loaded': True,
                    'image_size': original_size,
                    'processed_size': IMG_SIZE
                }
            }
            return JsonResponse(
                create_api_response(
                    success=True,
                    data=response_data,
                    message='Could not confidently classify the image. Please upload a clear image of a mango leaf or fruit.'
                )
            )

        # Add treatment suggestions
        for pred in prediction_summary['top_3']:
            pred['treatment'] = get_treatment_for_disease(pred['disease'])
            pred['detection_type'] = model_used

        # Alternative symptoms data will be generated by frontend service
        # Frontend has getDiseaseSymptoms() method that handles this
        primary_disease = prediction_summary['primary_prediction']['disease']
        alternative_diseases = [pred['disease'] for pred in prediction_summary['top_3'][1:3]]  # Get top 2-3 alternative diseases

        # Save to database only if not preview mode
        saved_image_id = None
        if not preview_only:
            try:
                image_file.seek(0)
                
                # Prepare location data for storage - always save if available
                location_data = {}
                if latitude and longitude:
                    try:
                        location_data.update({
                            'latitude': float(latitude),
                            'longitude': float(longitude),
                            'location_consent_given': True,  # Consent was given during registration
                            'location_accuracy_confirmed': location_accuracy_confirmed,
                            'location_source': location_source,
                            'location_address': location_address,
                        })
                    except (ValueError, TypeError) as e:
                        location_data.update({
                            'location_consent_given': False,
                            'location_accuracy_confirmed': False,
                        })
                else:
                    location_data.update({
                        'location_consent_given': False,
                        'location_accuracy_confirmed': False,
                    })
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                mango_image = MangoImage.objects.create(
                    image=image_file,
                    original_filename=image_file.name,
                    predicted_class=prediction_summary['primary_prediction']['disease'],
                    disease_classification=prediction_summary['primary_prediction']['disease'],
                    disease_type=model_used,  # Use the actual model that was used for detection
                    model_used=model_used,  # Store which model was actually used
                    model_filename=os.path.basename(model_path),  # Store the actual model filename
                    confidence_score=prediction_summary['primary_prediction']['confidence'] / 100,
                    user=request.user if request.user.is_authenticated else None,
                    image_size=f"{original_size[0]}x{original_size[1]}",
                    processing_time=processing_time,
                    client_ip=get_client_ip(request),
                    notes=f"Predicted via mobile app with {prediction_summary['primary_prediction']['confidence']:.2f}% confidence",
                    is_verified=False,  # Always default to unverified - admin must manually verify
                    user_feedback=user_feedback if user_feedback else None,  # User feedback can be NULL
                    user_confirmed_correct=is_detection_correct if user_feedback else None,  # Save user confirmation decision
                    # Add symptoms data
                    selected_symptoms=selected_symptoms if selected_symptoms else None,
                    primary_symptoms=primary_symptoms if primary_symptoms else None,
                    alternative_symptoms=alternative_symptoms if alternative_symptoms else None,
                    detected_disease=detected_disease if detected_disease else prediction_summary['primary_prediction']['disease'],
                    top_diseases=top_diseases if top_diseases else None,
                    symptoms_data=symptoms_data if symptoms_data else None,
                    **location_data  # Add all location data
                )
                log_prediction_activity(request.user, mango_image.id, prediction_summary)
                saved_image_id = mango_image.id
                
                # Create notification for admin dashboard
                try:
                    # Get the user who uploaded the image or use a default system user
                    notification_user = mango_image.user if mango_image.user else None
                    
                    # If no user is authenticated, try to get an admin user for the notification
                    if not notification_user:
                        from django.contrib.auth.models import User
                        notification_user = User.objects.filter(is_staff=True).first()
                    
                    if notification_user:
                        # Create a notification about the new image upload
                        Notification.objects.create(
                            notification_type='image_upload',
                            title=f'New {model_used.title()} Image Upload',
                            message=f'A new {model_used} image "{mango_image.original_filename}" was uploaded and classified as {prediction_summary["primary_prediction"]["disease"]} with {prediction_summary["primary_prediction"]["confidence"]:.1f}% confidence.',
                            related_image=mango_image,
                            user=notification_user
                        )
                    else:
                        print(f"No user available for notification creation")
                except Exception as notification_error:
                    print(f"Error creating notification: {notification_error}")
                    # Don't fail the entire request if notification creation fails
            except Exception as e:
                print(f"Error saving image to database: {e}")
                saved_image_id = None

        # Memory cleanup
        gc.collect()

        response_data = {
            'primary_prediction': {
                'disease': prediction_summary['primary_prediction']['disease'],
                'confidence': f"{prediction_summary['primary_prediction']['confidence']:.2f}%",
                'confidence_score': prediction_summary['primary_prediction']['confidence'],
                'confidence_level': prediction_summary['confidence_level'],
                'treatment': get_treatment_for_disease(prediction_summary['primary_prediction']['disease']),
                'detection_type': model_used
            },
            'top_3_predictions': prediction_summary['top_3'],
            'prediction_summary': {
                'most_likely': prediction_summary['primary_prediction']['disease'],
                'confidence_level': prediction_summary['confidence_level'],
                'total_diseases_checked': len(model_class_names)
            },
            'alternative_symptoms': {
                'primary_disease': primary_disease,
                'primary_disease_symptoms': [],  # Frontend will generate using getDiseaseSymptoms()
                'alternative_diseases': alternative_diseases  # Just disease names, frontend will get symptoms
            },
            'user_verification': {
                'selected_symptoms': selected_symptoms,
                'primary_symptoms': primary_symptoms,
                'alternative_symptoms': alternative_symptoms,
                'detected_disease': detected_disease,
                'is_detection_correct': is_detection_correct,
                'user_feedback': user_feedback
            },
            'model_used': model_used,
            'model_path': model_path,
            'debug_info': {
                'model_loaded': True,
                'image_size': original_size,
                'processed_size': IMG_SIZE
            }
        }
        
        # Include saved_image_id only if not preview mode and image was saved
        if not preview_only and saved_image_id:
            response_data['saved_image_id'] = saved_image_id
        try:
            probs_list = prediction.tolist() if hasattr(prediction, 'tolist') else list(map(float, prediction))
            labels_list = model_class_names
            response_time = time.time() - start_time
            PredictionLog.objects.create(
                image=mango_image if 'mango_image' in locals() else None,
                client_ip=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                response_time=response_time,
                probabilities=probs_list,
                labels=labels_list,
                prediction_summary=prediction_summary,
                raw_response=response_data
            )
        except Exception as e:
            print(f"Failed to log prediction activity: {str(e)}")

        return JsonResponse(
            create_api_response(
                success=True,
                data=response_data,
                message='Image processed successfully'
            )
        )

    except Exception as e:
        return JsonResponse(
            create_api_response(
                success=False,
                message='Prediction failed',
                errors=[str(e)]
            ),
            status=500
        )


@api_view(['GET'])
def test_model_status(request):
    """Test endpoint to check if model and class names are loaded properly"""
    try:
        # Get active model info from database
        active_model = MLModel.objects.filter(is_active=True).first()
        
        model_status = {
            'model_loaded': active_model is not None,
            'model_path': str(settings.MODEL_PATH) if hasattr(settings, 'MODEL_PATH') else 'Not set',
            'leaf_model_path': LEAF_MODEL_PATH,
            'fruit_model_path': FRUIT_MODEL_PATH,
            'leaf_model_exists': os.path.exists(LEAF_MODEL_PATH),
            'fruit_model_exists': os.path.exists(FRUIT_MODEL_PATH),
            'leaf_class_names': LEAF_CLASS_NAMES,
            'fruit_class_names': FRUIT_CLASS_NAMES,
            'class_names': class_names,  # For backward compatibility
            'leaf_classes_count': len(LEAF_CLASS_NAMES),
            'fruit_classes_count': len(FRUIT_CLASS_NAMES),
            'treatment_suggestions_count': len(treatment_suggestions),
            'active_model': {
                'name': active_model.name if active_model else None,
                'version': active_model.version if active_model else None,
                'accuracy': active_model.accuracy if active_model else None,
                'training_date': active_model.training_date if active_model else None
            } if active_model else None,
            'img_size': IMG_SIZE
        }
        
        database_stats = {
            'total_images': MangoImage.objects.count(),
            'healthy_images': MangoImage.objects.filter(disease_classification='Healthy').count(),
            'diseased_images': MangoImage.objects.exclude(disease_classification='Healthy').count(),
            'verified_images': MangoImage.objects.filter(is_verified=True).count()
        }
        
        return JsonResponse(
            create_api_response(
                success=True,
                data={
                    'model_status': model_status,
                    'available_leaf_diseases': LEAF_CLASS_NAMES,
                    'available_fruit_diseases': FRUIT_CLASS_NAMES,
                    'available_diseases': class_names,  # For backward compatibility
                    'database_stats': database_stats
                },
                message='Model status retrieved successfully'
            )
        )
        
    except Exception as e:
        return JsonResponse(
            create_api_response(
                success=False,
                message='Failed to get model status',
                errors=[str(e)]
            ),
            status=500
        )