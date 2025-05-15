from flask import request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import logging
from . import storage_bp
from models import File, Folder, AdminCredentials
from app import db

# Helper functions
def get_file_path(folder_path, filename):
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'storage')
    return os.path.join(storage_path, folder_path, filename)

def create_folder_structure(path):
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'storage')
    full_path = os.path.join(storage_path, path)
    os.makedirs(full_path, exist_ok=True)
    return full_path

@storage_bp.route('/folders', methods=['POST'])
def create_folder():
    data = request.json
    folder_name = data.get('name')
    parent_path = data.get('parent_path', '')
    
    if not folder_name:
        return jsonify({'error': 'Folder name is required'}), 400
    
    try:
        # Create folder in filesystem
        new_folder_path = os.path.join(parent_path, folder_name)
        full_path = create_folder_structure(new_folder_path)
        
        # Check if folder already exists in database
        existing_folder = Folder.query.filter_by(path=new_folder_path).first()
        if existing_folder:
            return jsonify({
                'id': existing_folder.id,
                'name': existing_folder.name,
                'path': existing_folder.path
            }), 200
        
        # Find parent folder if parent_path is provided
        parent_folder = None
        if parent_path:
            parent_folder = Folder.query.filter_by(path=parent_path).first()
        
        # Create folder in database
        folder = Folder(
            name=folder_name,
            path=new_folder_path,
            parent_id=parent_folder.id if parent_folder else None
        )
        db.session.add(folder)
        db.session.commit()
        
        return jsonify({
            'id': folder.id,
            'name': folder.name,
            'path': folder.path
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@storage_bp.route('/files', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    folder_path = request.form.get('folder_path', '')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Create secure filename and get file path
        filename = secure_filename(file.filename)
        file_path = get_file_path(folder_path, filename)
        
        # Ensure folder exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save file
        file.save(file_path)
        
        # Create file record in database
        file_record = File(
            filename=filename,
            original_filename=file.filename,
            file_path=os.path.join(folder_path, filename),
            file_type=file.content_type,
            size=os.path.getsize(file_path)
        )
        
        # Associate with folder if provided
        if folder_path:
            folder = Folder.query.filter_by(path=folder_path).first()
            if folder:
                file_record.folder_id = folder.id
        
        db.session.add(file_record)
        db.session.commit()
        
        return jsonify({
            'id': file_record.id,
            'filename': file_record.filename,
            'path': file_record.file_path
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@storage_bp.route('/files/<path:file_path>', methods=['GET'])
def get_file(file_path):
    try:
        file_record = File.query.filter_by(file_path=file_path).first()
        if not file_record:
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            get_file_path(os.path.dirname(file_path), file_record.filename),
            as_attachment=True,
            download_name=file_record.original_filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@storage_bp.route('/folders/<path:folder_path>', methods=['GET'])
def list_folder_contents(folder_path):
    try:
        folder = Folder.query.filter_by(path=folder_path).first()
        if not folder:
            return jsonify({'error': 'Folder not found'}), 404
        
        # Get subfolders
        subfolders = Folder.query.filter_by(parent_id=folder.id).all()
        subfolders_data = [{
            'id': f.id,
            'name': f.name,
            'path': f.path
        } for f in subfolders]
        
        # Get files
        files = File.query.filter_by(folder_id=folder.id).all()
        files_data = [{
            'id': f.id,
            'filename': f.filename,
            'original_filename': f.original_filename,
            'file_type': f.file_type,
            'size': f.size,
            'created_at': f.created_at.isoformat()
        } for f in files]
        
        return jsonify({
            'folder': {
                'id': folder.id,
                'name': folder.name,
                'path': folder.path
            },
            'subfolders': subfolders_data,
            'files': files_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@storage_bp.route('/files/<path:file_path>', methods=['DELETE'])
def delete_file(file_path):
    try:
        file_record = File.query.filter_by(file_path=file_path).first()
        if not file_record:
            return jsonify({'error': 'File not found'}), 404
        
        # Delete file from filesystem
        os.remove(get_file_path(os.path.dirname(file_path), file_record.filename))
        
        # Delete from database
        db.session.delete(file_record)
        db.session.commit()
        
        return jsonify({'message': 'File deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@storage_bp.route('/folders/<path:folder_path>', methods=['DELETE'])
def delete_folder(folder_path):
    try:
        folder = Folder.query.filter_by(path=folder_path).first()
        if not folder:
            return jsonify({'error': 'Folder not found'}), 404
        
        # Delete all files in the folder
        files = File.query.filter_by(folder_id=folder.id).all()
        for file in files:
            os.remove(get_file_path(os.path.dirname(file.file_path), file.filename))
            db.session.delete(file)
        
        # Delete folder from filesystem
        os.rmdir(get_file_path(folder_path, ''))
        
        # Delete from database
        db.session.delete(folder)
        db.session.commit()
        
        return jsonify({'message': 'Folder deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500 