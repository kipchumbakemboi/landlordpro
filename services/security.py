from werkzeug.utils import secure_filename

ALLOWED_IMAGES = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_DOCS = ALLOWED_IMAGES | {"pdf", "doc", "docx"}

def allowed_file(filename, allowed=ALLOWED_DOCS):
    return bool(filename and "." in filename and filename.rsplit(".", 1)[1].lower() in allowed)

def safe_upload_name(prefix, user_id, filename, timestamp):
    return f"{prefix}_{user_id}_{timestamp}_{secure_filename(filename)}"
