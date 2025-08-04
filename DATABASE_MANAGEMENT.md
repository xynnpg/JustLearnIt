# Database Management Guide for JustLearnIt

This guide explains how to manage the JustLearnIt database, including initialization, backup, restoration, and data export/import operations.

## Overview

The JustLearnIt application uses SQLite as its database, stored in `storage/storage.db`. The database contains the following tables:

- `user` - User accounts and profiles
- `admin_credentials` - Admin login credentials
- `admin_whitelist` - IP addresses allowed for admin access
- `lesson` - Educational lessons
- `test` - Tests and quizzes
- `grade` - Student grades and test results
- `folder` - File storage folders
- `file` - Stored files metadata

## Database Initialization

### Basic Initialization

To initialize the database for the first time:

```bash
python init_db.py
```

This will:
1. Create all database tables
2. Generate initial admin credentials
3. Add localhost to admin whitelist
4. Verify database integrity

### Advanced Initialization Options

```bash
# Recreate database from scratch (with backup)
python init_db.py recreate

# Seed initial data only
python init_db.py seed

# Verify database integrity
python init_db.py verify

# Show database information
python init_db.py info

# Create a backup
python init_db.py backup
```

## Database Backup and Restoration

### Using the Backup Utility

The `db_backup.py` script provides comprehensive backup and restoration capabilities:

```bash
# Create a timestamped backup
python db_backup.py backup

# List available backups
python db_backup.py list-backups

# Restore from a specific backup
python db_backup.py restore storage/storage.db.backup.20241201_120000
```

### Data Export and Import

You can export database data to JSON files for backup or migration:

```bash
# Export all data to JSON files
python db_backup.py export

# List available exports
python db_backup.py list-exports

# Import data from JSON export
python db_backup.py import storage/exports/data_export_20241201_120000
```

## Database Recreation Workflow

If you need to completely recreate the database:

### 1. Backup Current Data (Optional)
```bash
python db_backup.py backup
```

### 2. Export Data (Recommended)
```bash
python db_backup.py export
```

### 3. Recreate Database
```bash
python init_db.py recreate
```

### 4. Restore Data (If Needed)
```bash
python db_backup.py import storage/exports/data_export_20241201_120000
```

## Security Considerations

### Admin Credentials

- Admin credentials are automatically generated and rotated every 7 days
- Credentials are sent to the admin email address configured in `.env`
- You can force credential regeneration using the admin panel

### Database Security

- The database file should have appropriate file permissions
- Regular backups are recommended
- Consider encrypting the database file for production use

## Troubleshooting

### Common Issues

1. **Database locked**: Ensure no other processes are using the database
2. **Permission denied**: Check file permissions on the storage directory
3. **Import errors**: Verify JSON export files are complete and valid
4. **Missing tables**: Run `python init_db.py recreate` to recreate the database structure

### Verification Commands

```bash
# Check database integrity
python init_db.py verify

# Show database statistics
python init_db.py info

# List all backups
python db_backup.py list-backups
```

## File Structure

```
storage/
├── storage.db                    # Main database file
├── storage.db.backup.*          # Database backups
├── exports/                     # Data export directories
│   └── data_export_*/          # Timestamped exports
│       ├── user.json           # User data
│       ├── lesson.json         # Lesson data
│       ├── test.json           # Test data
│       └── export_info.json    # Export metadata
└── admin_credentials.txt       # Legacy admin credentials (deprecated)
```

## Best Practices

1. **Regular Backups**: Create backups before major changes
2. **Test Restorations**: Periodically test backup restoration
3. **Version Control**: Keep database schema changes in migrations
4. **Environment Separation**: Use different databases for development and production
5. **Monitoring**: Monitor database size and performance

## Migration Notes

When upgrading the application:

1. Backup the current database
2. Export data if needed
3. Update the application code
4. Run database migrations: `flask db upgrade`
5. Verify database integrity
6. Test the application functionality

## Emergency Recovery

In case of database corruption or loss:

1. Check for recent backups: `python db_backup.py list-backups`
2. Restore from the most recent backup: `python db_backup.py restore <backup_file>`
3. If no backup exists, recreate the database: `python init_db.py recreate`
4. Restore data from JSON export if available: `python db_backup.py import <export_dir>`

## Support

For database-related issues:

1. Check the application logs for error messages
2. Verify database file permissions
3. Ensure sufficient disk space
4. Check for conflicting processes
5. Review this documentation for common solutions 