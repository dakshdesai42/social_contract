"""
Cloudinary Integration Helper
Handles image uploads for profile photos and check-in verification photos
"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import logging

logger = logging.getLogger('accountability_arena.cloudinary')

# Initialize Cloudinary from environment variables
# Required env vars: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
# Or use CLOUDINARY_URL which contains all three


def init_cloudinary():
    """Initialize Cloudinary configuration from environment variables."""
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    cloudinary_url = os.environ.get('CLOUDINARY_URL')

    if cloudinary_url:
        # CLOUDINARY_URL format: cloudinary://API_KEY:API_SECRET@CLOUD_NAME
        cloudinary.config(cloudinary_url=cloudinary_url)
        logger.info('Cloudinary configured from CLOUDINARY_URL')
        return True
    elif cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        logger.info('Cloudinary configured from individual env vars')
        return True
    else:
        logger.warning('Cloudinary not configured - image uploads will fail')
        return False


def upload_image(file_storage, folder='social-contract', public_id=None, transformation=None):
    """
    Upload an image to Cloudinary.

    Args:
        file_storage: Flask FileStorage object from request.files
        folder: Cloudinary folder to store the image
        public_id: Optional custom public ID (auto-generated if not provided)
        transformation: Optional transformation dict (e.g., {'width': 500, 'height': 500, 'crop': 'fill'})

    Returns:
        dict with 'url' and 'public_id' on success, or None on failure
    """
    if not file_storage or not file_storage.filename:
        return None

    try:
        # Default transformations for optimization
        upload_options = {
            'folder': folder,
            'resource_type': 'image',
            'overwrite': True,
            'invalidate': True,
        }

        if public_id:
            upload_options['public_id'] = public_id

        # Apply automatic format and quality optimization
        upload_options['eager'] = [
            {'quality': 'auto', 'fetch_format': 'auto'}
        ]

        if transformation:
            upload_options['transformation'] = transformation

        result = cloudinary.uploader.upload(file_storage, **upload_options)

        return {
            'url': result.get('secure_url'),
            'public_id': result.get('public_id'),
        }

    except cloudinary.exceptions.Error as e:
        logger.error(f'Cloudinary upload failed: {e}')
        return None
    except Exception as e:
        logger.error(f'Unexpected error uploading to Cloudinary: {e}')
        return None


def upload_profile_photo(file_storage, user_id):
    """
    Upload a profile photo with automatic cropping and optimization.

    Args:
        file_storage: Flask FileStorage object
        user_id: User ID for generating consistent public_id

    Returns:
        URL string on success, None on failure
    """
    result = upload_image(
        file_storage,
        folder='social-contract/profiles',
        public_id=f'user_{user_id}',
        transformation={
            'width': 400,
            'height': 400,
            'crop': 'fill',
            'gravity': 'face',
            'quality': 'auto',
            'fetch_format': 'auto'
        }
    )
    return result.get('url') if result else None


def upload_checkin_photo(file_storage, challenge_id, user_id, checkin_date):
    """
    Upload a check-in verification photo.

    Args:
        file_storage: Flask FileStorage object
        challenge_id: Challenge ID
        user_id: User ID
        checkin_date: Date string (YYYY-MM-DD)

    Returns:
        URL string on success, None on failure
    """
    result = upload_image(
        file_storage,
        folder='social-contract/checkins',
        public_id=f'checkin_{challenge_id}_{user_id}_{checkin_date}',
        transformation={
            'width': 1200,
            'height': 1200,
            'crop': 'limit',  # Don't upscale, just limit max dimensions
            'quality': 'auto:good',
            'fetch_format': 'auto'
        }
    )
    return result.get('url') if result else None


def delete_image(public_id):
    """
    Delete an image from Cloudinary.

    Args:
        public_id: The public_id of the image to delete

    Returns:
        True on success, False on failure
    """
    if not public_id:
        return False

    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        logger.error(f'Failed to delete image {public_id}: {e}')
        return False


def get_optimized_url(url, width=None, height=None, crop='fill'):
    """
    Get an optimized URL for an existing Cloudinary image.

    Args:
        url: Original Cloudinary URL
        width: Target width
        height: Target height
        crop: Crop mode (fill, fit, limit, etc.)

    Returns:
        Optimized URL string
    """
    if not url or 'cloudinary.com' not in url:
        return url

    try:
        # Extract public_id from URL
        # URL format: https://res.cloudinary.com/cloud_name/image/upload/v123/folder/public_id.ext
        parts = url.split('/upload/')
        if len(parts) != 2:
            return url

        base = parts[0] + '/upload'
        path = parts[1]

        # Build transformation string
        transforms = ['f_auto', 'q_auto']
        if width:
            transforms.append(f'w_{width}')
        if height:
            transforms.append(f'h_{height}')
        if crop and (width or height):
            transforms.append(f'c_{crop}')

        transform_str = ','.join(transforms)
        return f'{base}/{transform_str}/{path}'

    except Exception:
        return url
